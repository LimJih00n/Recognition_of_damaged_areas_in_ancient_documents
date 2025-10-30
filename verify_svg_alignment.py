"""
SVG 벡터가 원본 이미지와 정확히 매칭되는지 시각적으로 검증

사용법:
    python verify_svg_alignment.py \
        --image datasets/test_small.jpg \
        --svg results/test_small_svg/all_holes_vector.svg \
        --output verification.png
"""

import cv2
import numpy as np
import xml.etree.ElementTree as ET
import argparse
import re


def parse_svg_path(path_d):
    """SVG path 문자열을 좌표 리스트로 파싱"""
    points = []

    # "M 271,1080 L 277,1080 L 275,1077 Z" 형식 파싱
    commands = re.findall(r'[ML]\s*([\d.]+),([\d.]+)', path_d)

    for cmd in commands:
        x, y = float(cmd[0]), float(cmd[1])
        points.append([int(x), int(y)])

    return np.array(points, dtype=np.int32)


def load_svg_paths(svg_path):
    """SVG 파일에서 모든 path 읽기"""
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # SVG namespace 처리
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    paths = []

    # 모든 path 요소 찾기
    for path in root.findall('.//svg:path', ns):
        path_d = path.get('d')
        if path_d:
            try:
                points = parse_svg_path(path_d)
                if len(points) > 0:
                    paths.append(points)
            except Exception as e:
                print(f"Warning: Failed to parse path: {e}")

    # namespace 없이도 시도
    if len(paths) == 0:
        for path in root.findall('.//path'):
            path_d = path.get('d')
            if path_d:
                try:
                    points = parse_svg_path(path_d)
                    if len(points) > 0:
                        paths.append(points)
                except Exception as e:
                    print(f"Warning: Failed to parse path: {e}")

    print(f"Loaded {len(paths)} paths from SVG")
    return paths


def verify_svg_alignment(image_path, svg_path, output_path):
    """SVG 경로를 원본 이미지에 오버레이하여 검증"""

    # 1. 이미지 로드 (한글 경로 지원)
    try:
        # numpy를 통한 한글 경로 지원
        with open(image_path, 'rb') as f:
            image_data = np.frombuffer(f.read(), np.uint8)
            image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

        if image is None:
            print(f"Error: Cannot decode image: {image_path}")
            return
    except Exception as e:
        print(f"Error: Cannot load image: {image_path}")
        print(f"  {e}")
        return

    h, w = image.shape[:2]
    print(f"\nImage size: {w}x{h}")

    # 2. SVG 경로 로드
    svg_paths = load_svg_paths(svg_path)

    if len(svg_paths) == 0:
        print("Error: No paths found in SVG")
        return

    # 3. 시각화 이미지 3개 생성
    overlay = image.copy()
    svg_only = np.ones_like(image) * 255  # 흰 배경
    numbered = image.copy()

    # 4. 폰트 크기 자동 계산 (이미지 크기에 비례)
    font_scale = max(0.3, min(w, h) / 2000)
    thickness = max(1, int(font_scale * 2))
    line_thickness = max(1, int(font_scale * 3))

    # 5. SVG 경로를 이미지에 그리기
    for i, points in enumerate(svg_paths):
        if len(points) < 3:
            continue

        # Overlay: 원본 이미지 + 빨간 윤곽선
        cv2.polylines(overlay, [points], True, (0, 0, 255), line_thickness)

        # SVG only: 검은 채우기
        cv2.fillPoly(svg_only, [points], (0, 0, 0))

        # Numbered: 녹색 윤곽선 + 번호 표시
        cv2.polylines(numbered, [points], True, (0, 255, 0), 1)

        # 중심점 계산 (번호 표시 위치)
        M = cv2.moments(points)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            # 번호 표시 (1부터 시작)
            text = str(i + 1)
            # 텍스트 크기 계산
            (text_w, text_h), baseline = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
            )

            # 배경 사각형 (가독성 향상)
            cv2.rectangle(numbered,
                         (cx - text_w//2 - 2, cy - text_h//2 - 2),
                         (cx + text_w//2 + 2, cy + text_h//2 + baseline),
                         (255, 255, 255), -1)

            # 번호 텍스트
            cv2.putText(numbered, text,
                       (cx - text_w//2, cy + text_h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 0, 0), thickness)

    # 6. 결과 합성
    # 상단: 원본 | 오버레이
    # 하단: SVG만 | 번호 표시
    top = np.hstack([image, overlay])
    bottom = np.hstack([svg_only, numbered])
    result = np.vstack([top, bottom])

    # 텍스트 추가
    font = cv2.FONT_HERSHEY_SIMPLEX
    title_scale = max(0.5, min(w, h) / 1500)
    title_thickness = max(1, int(title_scale * 2))
    cv2.putText(result, "Original", (10, 30), font, title_scale, (255, 255, 255), title_thickness)
    cv2.putText(result, "SVG Overlay (Red)", (w + 10, 30), font, title_scale, (255, 255, 255), title_thickness)
    cv2.putText(result, "SVG Only (Black)", (10, h + 30), font, title_scale, (0, 0, 0), title_thickness)
    cv2.putText(result, "Numbered (ID)", (w + 10, h + 30), font, title_scale, (255, 255, 255), title_thickness)

    # 7. 저장
    cv2.imwrite(output_path, result)
    print(f"\nVerification saved: {output_path}")
    print(f"Total SVG paths drawn: {len(svg_paths)}")
    print(f"\nVisual check:")
    print(f"  - Top-left: Original image")
    print(f"  - Top-right: SVG paths in RED overlay")
    print(f"  - Bottom-left: SVG paths only (black fill)")
    print(f"  - Bottom-right: Numbered holes with IDs (1-{len(svg_paths)})")
    print(f"\nIf RED lines match holes exactly → SVG is accurate!")
    print(f"Blue numbers show hole IDs for tracking")


def main():
    parser = argparse.ArgumentParser(
        description='Verify SVG path alignment with original image'
    )
    parser.add_argument('--image', required=True,
                       help='Original image file')
    parser.add_argument('--svg', required=True,
                       help='SVG vector file')
    parser.add_argument('--output', default='svg_verification.png',
                       help='Output verification image')

    args = parser.parse_args()

    verify_svg_alignment(args.image, args.svg, args.output)


if __name__ == '__main__':
    main()
