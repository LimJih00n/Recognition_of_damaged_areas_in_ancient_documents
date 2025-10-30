#!/usr/bin/env python3
"""
Restoration Guide Generator
조선시대 문서 복원 가이드 자동 생성

기능:
- 원본 이미지에 구멍 위치와 번호 오버레이
- 레이저 커팅된 조각을 어디에 붙여야 하는지 표시
- 인쇄 가능한 가이드 이미지 생성
- CSV 좌표 데이터 출력
"""

import os
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import json
import csv
import numpy as np
import cv2
from typing import List, Dict, Tuple
import re


def load_image(image_path: str) -> np.ndarray:
    """이미지 로드 (한글 경로 지원)"""
    try:
        # numpy를 통한 한글 경로 지원
        with open(image_path, 'rb') as f:
            image_data = np.frombuffer(f.read(), np.uint8)
            image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
        return image
    except Exception as e:
        print(f"Error: Cannot load image: {image_path}")
        print(f"  {e}")
        return None


def parse_combined_svg(svg_path: str) -> List[Dict]:
    """통합 SVG 파일에서 구멍 정보 추출"""
    print(f"Parsing SVG: {svg_path}")

    tree = ET.parse(svg_path)
    root = tree.getroot()

    # 네임스페이스 처리
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    holes = []

    # 모든 path 요소 찾기
    paths = root.findall('.//svg:path', ns) or root.findall('.//path') or root.findall('.//{http://www.w3.org/2000/svg}path')

    for path in paths:
        path_id = path.get('id', '')

        # hole_id 추출 (예: "hole_10" -> 10)
        hole_id = 0
        if path_id.startswith('hole_'):
            try:
                hole_id = int(path_id.split('_')[1])
            except (IndexError, ValueError):
                pass

        # path 데이터에서 좌표 추출하여 bounding box 계산
        d = path.get('d', '')
        if not d:
            continue

        # path 좌표 파싱
        coords = []
        parts = d.replace(',', ' ').split()
        i = 0
        while i < len(parts):
            if parts[i] in ['M', 'L', 'Z']:
                i += 1
            else:
                try:
                    x = float(parts[i])
                    y = float(parts[i + 1])
                    coords.append((x, y))
                    i += 2
                except (ValueError, IndexError):
                    i += 1

        if not coords:
            continue

        # Bounding box 계산
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]

        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        # 중심점 계산
        cx = (x_min + x_max) / 2
        cy = (y_min + y_max) / 2

        holes.append({
            'hole_id': hole_id,
            'bbox': (int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)),
            'center': (int(cx), int(cy)),
            'area': (x_max - x_min) * (y_max - y_min)
        })

    print(f"  Found {len(holes)} holes")

    return holes


def parse_individual_svgs(svg_dir: str) -> List[Dict]:
    """개별 SVG 파일들에서 구멍 정보 추출 (path 데이터 포함)"""
    print(f"Loading individual SVG files from: {svg_dir}")

    holes = []
    svg_files = sorted(Path(svg_dir).glob('*.svg'))

    for svg_file in svg_files:
        try:
            tree = ET.parse(str(svg_file))
            root = tree.getroot()

            # 네임스페이스 처리
            ns = {'svg': 'http://www.w3.org/2000/svg'}

            # 메타데이터 추출
            metadata_elem = root.find('svg:metadata', ns) or root.find('metadata') or root.find('{http://www.w3.org/2000/svg}metadata')

            if metadata_elem is None:
                continue

            metadata = {}
            for child in metadata_elem:
                tag = child.tag.replace('{http://www.w3.org/2000/svg}', '')
                metadata[tag] = child.text

            # hole_id 추출
            hole_id = int(metadata.get('hole_id', 0))

            # bbox 파싱 (예: "x=1221, y=1019, w=92, h=63")
            bbox_str = metadata.get('bbox', '')
            bbox_parts = {}
            for part in bbox_str.split(','):
                part = part.strip()
                if '=' in part:
                    key, val = part.split('=')
                    bbox_parts[key.strip()] = int(val.strip())

            if 'x' in bbox_parts and 'y' in bbox_parts and 'w' in bbox_parts and 'h' in bbox_parts:
                x = bbox_parts['x']
                y = bbox_parts['y']
                w = bbox_parts['w']
                h = bbox_parts['h']

                cx = x + w // 2
                cy = y + h // 2

                # SVG path 데이터 추출
                path_elem = (root.find('.//svg:path', ns) or
                            root.find('.//path') or
                            root.find('.//{http://www.w3.org/2000/svg}path'))

                path_data = path_elem.get('d', '') if path_elem is not None else ''

                holes.append({
                    'hole_id': hole_id,
                    'bbox': (x, y, w, h),
                    'center': (cx, cy),
                    'area': w * h,
                    'path_data': path_data,  # SVG path 데이터 추가
                    'svg_file': str(svg_file)
                })

        except Exception as e:
            print(f"Warning: Failed to parse {svg_file.name}: {e}")

    print(f"  Loaded {len(holes)} holes")

    return holes


def parse_svg_path(path_data: str) -> List[Tuple[float, float]]:
    """SVG path 데이터를 좌표 리스트로 변환"""
    coords = []

    # 간단한 path 파싱 (M, L 명령어만)
    commands = re.findall(r'([MLZ])\s*([\d\.,\s-]+)', path_data)

    for cmd, params in commands:
        if cmd in ['M', 'L']:
            # 좌표 추출
            nums = re.findall(r'[-\d.]+', params)
            for i in range(0, len(nums), 2):
                if i + 1 < len(nums):
                    x = float(nums[i])
                    y = float(nums[i + 1])
                    coords.append((x, y))

    return coords


def render_svg_piece(image: np.ndarray, hole: Dict, color: Tuple[int, int, int],
                     thickness: int = -1, scale: float = 1.0) -> np.ndarray:
    """SVG 조각을 이미지에 렌더링"""
    result = image.copy()

    if 'path_data' not in hole or not hole['path_data']:
        # path 데이터가 없으면 bbox만 그리기
        x, y, w, h = hole['bbox']
        cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
        return result

    # SVG path 파싱
    coords = parse_svg_path(hole['path_data'])

    if not coords:
        return result

    # 스케일 적용
    if scale != 1.0:
        x, y, w, h = hole['bbox']
        cx, cy = x + w / 2, y + h / 2

        scaled_coords = []
        for px, py in coords:
            # 중심점 기준으로 스케일
            dx = px - cx
            dy = py - cy
            scaled_coords.append((cx + dx * scale, cy + dy * scale))
        coords = scaled_coords

    # numpy 배열로 변환
    points = np.array(coords, dtype=np.int32)

    if thickness == -1:
        # 채우기
        cv2.fillPoly(result, [points], color)
    else:
        # 윤곽선만
        cv2.polylines(result, [points], True, color, thickness)

    return result


def create_restoration_guide(image: np.ndarray, holes: List[Dict], output_path: str):
    """복원 가이드 이미지 생성 (번호 오버레이)"""

    print(f"\nCreating restoration guide with {len(holes)} pieces...")

    # 이미지 복사
    guide = image.copy()

    # 투명도를 위한 오버레이 레이어
    overlay = guide.copy()

    # 각 구멍에 번호 표시
    for hole in holes:
        hole_id = hole['hole_id']
        cx, cy = hole['center']
        x, y, w, h = hole['bbox']

        # 구멍 영역 강조 (반투명 사각형)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), -1)

        # 구멍 테두리 (진한 녹색)
        cv2.rectangle(guide, (x, y), (x + w, y + h), (0, 200, 0), 2)

        # 번호 텍스트 크기 계산 (구멍 크기에 비례)
        font_scale = min(2.0, max(0.4, w / 40.0))
        thickness = max(1, int(font_scale * 2))
        font = cv2.FONT_HERSHEY_SIMPLEX

        # 번호 텍스트
        text = str(hole_id)
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

        # 텍스트 배경 (가독성 향상)
        bg_x1 = cx - text_w // 2 - 5
        bg_y1 = cy - text_h // 2 - 5
        bg_x2 = cx + text_w // 2 + 5
        bg_y2 = cy + text_h // 2 + baseline + 5

        cv2.rectangle(guide, (bg_x1, bg_y1), (bg_x2, bg_y2), (255, 255, 255), -1)
        cv2.rectangle(guide, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 255), 2)

        # 번호 텍스트
        cv2.putText(guide, text,
                   (cx - text_w // 2, cy + text_h // 2),
                   font, font_scale, (0, 0, 255), thickness)

    # 오버레이 합성 (30% 투명도)
    cv2.addWeighted(overlay, 0.3, guide, 0.7, 0, guide)

    # 가이드 정보 텍스트
    info_text = f"Restoration Guide - {len(holes)} pieces to restore"
    cv2.putText(guide, info_text,
               (20, 40),
               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    # 저장 (한글 경로 지원)
    try:
        _, encoded = cv2.imencode('.png', guide)
        with open(output_path, 'wb') as f:
            f.write(encoded)
        print(f"  Saved: {output_path}")
    except Exception as e:
        print(f"Error: Failed to save guide image: {e}")


def create_simple_overlay(image: np.ndarray, holes: List[Dict], output_path: str):
    """간단한 번호 오버레이 (레퍼런스용)"""

    print(f"Creating simple overlay...")

    overlay = image.copy()

    for hole in holes:
        hole_id = hole['hole_id']
        cx, cy = hole['center']
        x, y, w, h = hole['bbox']

        # 작은 사각형과 번호만 표시
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 1)

        # 번호
        font_scale = 0.5
        thickness = 1
        text = str(hole_id)

        (text_w, text_h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

        # 배경
        cv2.rectangle(overlay,
                     (cx - text_w // 2 - 2, cy - text_h // 2 - 2),
                     (cx + text_w // 2 + 2, cy + text_h // 2 + baseline + 2),
                     (255, 255, 255), -1)

        # 텍스트
        cv2.putText(overlay, text,
                   (cx - text_w // 2, cy + text_h // 2),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 0, 0), thickness)

    # 저장
    try:
        _, encoded = cv2.imencode('.png', overlay)
        with open(output_path, 'wb') as f:
            f.write(encoded)
        print(f"  Saved: {output_path}")
    except Exception as e:
        print(f"Error: Failed to save overlay image: {e}")


def create_restoration_preview(image: np.ndarray, holes: List[Dict], output_path: str,
                              scale_config: Dict[str, float] = None, global_scale: float = 1.0):
    """복원 미리보기: SVG 조각들을 원본 위치에 렌더링"""

    print(f"\nCreating restoration preview with {len(holes)} pieces...")

    # 이미지 복사
    preview = image.copy()

    # 각 구멍에 SVG 조각 렌더링
    for hole in holes:
        hole_id = hole['hole_id']

        # 스케일 계산
        if scale_config and str(hole_id) in scale_config:
            scale = float(scale_config[str(hole_id)])
        else:
            scale = global_scale

        # 반투명 녹색으로 채우기
        color = (150, 255, 150)  # 연한 녹색
        preview = render_svg_piece(preview, hole, color, thickness=-1, scale=scale)

        # 테두리는 진한 녹색
        edge_color = (0, 200, 0)
        preview = render_svg_piece(preview, hole, edge_color, thickness=2, scale=scale)

    # 저장
    try:
        _, encoded = cv2.imencode('.png', preview)
        with open(output_path, 'wb') as f:
            f.write(encoded)
        print(f"  Saved: {output_path}")
    except Exception as e:
        print(f"Error: Failed to save preview image: {e}")


def create_coverage_visualization(image: np.ndarray, holes: List[Dict], output_path: str,
                                  scale_config: Dict[str, float] = None, global_scale: float = 1.0):
    """커버리지 시각화: 스케일된 조각이 원본 구멍을 얼마나 덮는지 표시"""

    print(f"\nCreating coverage visualization...")

    # 이미지 복사
    coverage = image.copy()

    # 통계
    coverage_stats = {
        'perfect': 0,      # 1.0x (정확히 일치)
        'oversized': 0,    # > 1.0x (여유 있음)
        'undersized': 0    # < 1.0x (부족함)
    }

    for hole in holes:
        hole_id = hole['hole_id']
        x, y, w, h = hole['bbox']
        cx, cy = hole['center']

        # 스케일 계산
        if scale_config and str(hole_id) in scale_config:
            scale = float(scale_config[str(hole_id)])
        else:
            scale = global_scale

        # 스케일에 따라 색상 결정
        if scale == 1.0:
            color = (0, 255, 0)  # 녹색: 완벽
            label = "1.0x"
            coverage_stats['perfect'] += 1
        elif scale > 1.0:
            color = (0, 200, 255)  # 주황색: 여유
            label = f"{scale:.1f}x"
            coverage_stats['oversized'] += 1
        else:
            color = (0, 0, 255)  # 빨강: 부족
            label = f"{scale:.1f}x"
            coverage_stats['undersized'] += 1

        # 원본 구멍 (회색 윤곽)
        cv2.rectangle(coverage, (x, y), (x + w, y + h), (128, 128, 128), 1)

        # 스케일된 조각 렌더링
        coverage = render_svg_piece(coverage, hole, color, thickness=2, scale=scale)

        # 스케일 라벨
        font_scale = 0.4
        thickness = 1
        (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)

        # 라벨 배경
        label_x = cx - text_w // 2
        label_y = cy - text_h // 2

        cv2.rectangle(coverage,
                     (label_x - 2, label_y - text_h - 2),
                     (label_x + text_w + 2, label_y + 2),
                     (255, 255, 255), -1)

        # 라벨 텍스트
        cv2.putText(coverage, label,
                   (label_x, label_y),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)

    # 범례 추가
    legend_y = 30
    legend_x = 10
    font_scale = 0.6
    thickness = 2

    cv2.rectangle(coverage, (5, 5), (250, 110), (255, 255, 255), -1)
    cv2.rectangle(coverage, (5, 5), (250, 110), (0, 0, 0), 2)

    cv2.putText(coverage, "Coverage Legend:", (legend_x, legend_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)

    legend_y += 25
    cv2.rectangle(coverage, (legend_x, legend_y - 10), (legend_x + 20, legend_y), (0, 255, 0), -1)
    cv2.putText(coverage, f"1.0x: Perfect ({coverage_stats['perfect']})", (legend_x + 30, legend_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1)

    legend_y += 25
    cv2.rectangle(coverage, (legend_x, legend_y - 10), (legend_x + 20, legend_y), (0, 200, 255), -1)
    cv2.putText(coverage, f">1.0x: Oversized ({coverage_stats['oversized']})", (legend_x + 30, legend_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1)

    legend_y += 25
    cv2.rectangle(coverage, (legend_x, legend_y - 10), (legend_x + 20, legend_y), (0, 0, 255), -1)
    cv2.putText(coverage, f"<1.0x: Undersized ({coverage_stats['undersized']})", (legend_x + 30, legend_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1)

    # 저장
    try:
        _, encoded = cv2.imencode('.png', coverage)
        with open(output_path, 'wb') as f:
            f.write(encoded)
        print(f"  Saved: {output_path}")
        print(f"  Coverage stats: {coverage_stats['perfect']} perfect, {coverage_stats['oversized']} oversized, {coverage_stats['undersized']} undersized")
    except Exception as e:
        print(f"Error: Failed to save coverage image: {e}")


def export_csv(holes: List[Dict], csv_path: str):
    """구멍 위치 정보를 CSV로 출력"""

    print(f"Exporting CSV: {csv_path}")

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # 헤더
        writer.writerow(['piece_id', 'center_x', 'center_y', 'bbox_x', 'bbox_y', 'bbox_w', 'bbox_h', 'area_pixels'])

        # 데이터
        for hole in sorted(holes, key=lambda h: h['hole_id']):
            cx, cy = hole['center']
            x, y, w, h = hole['bbox']
            area = hole['area']

            writer.writerow([hole['hole_id'], cx, cy, x, y, w, h, area])

    print(f"  Exported {len(holes)} pieces")


def main():
    parser = argparse.ArgumentParser(description='Generate restoration guide from hole detection results')
    parser.add_argument('--image', required=True, help='Input image file')
    parser.add_argument('--svg', help='Combined SVG file with all holes')
    parser.add_argument('--svg-dir', help='Directory containing individual SVG files')
    parser.add_argument('--output-dir', default='restoration_guide', help='Output directory')

    # 스케일 옵션
    parser.add_argument('--scale', type=float, default=1.0, help='Global scale factor for preview (default: 1.0)')
    parser.add_argument('--scale-config', type=str, help='JSON file with individual piece scales')

    args = parser.parse_args()

    print("=" * 60)
    print("Restoration Guide Generator")
    print("문화재 복원 가이드 자동 생성")
    print("=" * 60)

    # 1. 이미지 로드
    print(f"\nLoading image: {args.image}")
    image = load_image(args.image)

    if image is None:
        print("Error: Failed to load image")
        return

    print(f"  Image size: {image.shape[1]}x{image.shape[0]}")

    # 2. 구멍 정보 로드
    holes = []

    if args.svg:
        # 통합 SVG에서 로드
        holes = parse_combined_svg(args.svg)
    elif args.svg_dir:
        # 개별 SVG 파일들에서 로드
        holes = parse_individual_svgs(args.svg_dir)
    else:
        print("Error: Either --svg or --svg-dir must be specified")
        return

    if len(holes) == 0:
        print("Error: No holes found")
        return

    # hole_id 순으로 정렬
    holes.sort(key=lambda h: h['hole_id'])

    # 3. 스케일 설정 로드
    scale_config = None
    if args.scale_config:
        try:
            with open(args.scale_config, 'r', encoding='utf-8') as f:
                scale_config = json.load(f)
            print(f"\nLoaded scale config from {args.scale_config}")
            print(f"  Individual scales defined for {len(scale_config)} pieces")
        except Exception as e:
            print(f"\nWarning: Failed to load scale config: {e}")
            print("  Using global scale only")

    # 4. 출력 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)

    # 5. 복원 가이드 생성 (번호 오버레이)
    guide_path = os.path.join(args.output_dir, 'restoration_guide.png')
    create_restoration_guide(image, holes, guide_path)

    # 6. 간단한 오버레이 생성
    overlay_path = os.path.join(args.output_dir, 'simple_overlay.png')
    create_simple_overlay(image, holes, overlay_path)

    # 7. 복원 미리보기 생성 (SVG 조각 렌더링)
    preview_path = os.path.join(args.output_dir, 'restoration_preview.png')
    create_restoration_preview(image, holes, preview_path, scale_config, args.scale)

    # 8. 커버리지 시각화 (스케일된 조각 vs 원본 구멍)
    coverage_path = os.path.join(args.output_dir, 'coverage_visualization.png')
    create_coverage_visualization(image, holes, coverage_path, scale_config, args.scale)

    # 9. CSV 출력
    csv_path = os.path.join(args.output_dir, 'piece_locations.csv')
    export_csv(holes, csv_path)

    print("\n" + "=" * 60)
    print("Restoration guide generation completed!")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Guide image: restoration_guide.png")
    print(f"  Simple overlay: simple_overlay.png")
    print(f"  Restoration preview: restoration_preview.png")
    print(f"  Coverage visualization: coverage_visualization.png")
    print(f"  CSV data: piece_locations.csv")
    print("=" * 60)


if __name__ == '__main__':
    main()
