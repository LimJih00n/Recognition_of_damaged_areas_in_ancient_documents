"""
흰색 기반 구멍 추출
핵심: 구멍 = 흰색 배경 = 채도 낮음 + 밝음
얼룩/변색 = 베이지색 = 채도 있음
"""

import cv2
import numpy as np
import os
import argparse
import xml.etree.ElementTree as ET
from xml.dom import minidom


def detect_whiteness(image, method='hsv', s_percentile=None, v_percentile=None, s_threshold=None, v_threshold=None):
    """
    흰색 정도 감지

    Args:
        method: 'hsv', 'rgb_balance', 'lab_achromatic', 'combined'
        s_percentile: Saturation percentile (None이면 s_threshold 사용)
        v_percentile: Value percentile (None이면 v_threshold 사용)
        s_threshold: 절대 Saturation threshold (우선순위)
        v_threshold: 절대 Value threshold (우선순위)
    """
    print(f"\n=== Whiteness Detection: {method} ===")

    if method == 'lab_b':
        # LAB에서 b-channel이 낮음 = 흰색 (베이지는 b가 높음)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        L, a, b = cv2.split(lab)

        print(f"  b (yellowness): {b.mean():.1f} ± {b.std():.1f}")

        # b-channel threshold (낮을수록 흰색, 높을수록 베이지)
        if s_threshold is not None:  # s_threshold를 b_threshold로 재사용
            b_thresh = s_threshold
            print(f"  b threshold: < {b_thresh} (absolute)")
        else:
            b_thresh = int(np.percentile(b, s_percentile if s_percentile else 25))
            print(f"  b threshold: < {b_thresh} (p{s_percentile if s_percentile else 25})")

        white_mask = (b < b_thresh).astype(np.uint8) * 255

        return white_mask, {'b': b}

    elif method == 'hsv':
        # HSV에서 Saturation이 낮고 Value가 높음 = 흰색
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        H, S, V = cv2.split(hsv)

        print(f"  S (saturation): {S.mean():.1f} ± {S.std():.1f}")
        print(f"  V (value): {V.mean():.1f} ± {V.std():.1f}")

        # Threshold 결정 (절대값 우선, 없으면 percentile)
        if s_threshold is not None:
            s_thresh = s_threshold
            print(f"  S threshold: < {s_thresh} (absolute)")
        else:
            s_thresh = int(np.percentile(S, s_percentile if s_percentile else 25))
            print(f"  S threshold: < {s_thresh} (p{s_percentile if s_percentile else 25})")

        if v_threshold is not None:
            v_thresh = v_threshold
            print(f"  V threshold: > {v_thresh} (absolute)")
        else:
            v_thresh = int(np.percentile(V, v_percentile if v_percentile else 75))
            print(f"  V threshold: > {v_thresh} (p{v_percentile if v_percentile else 75})")

        white_mask = (S < s_thresh) & (V > v_thresh)
        white_mask = white_mask.astype(np.uint8) * 255

        return white_mask, {'S': S, 'V': V}

    elif method == 'rgb_balance':
        # RGB 채널 간 차이가 작음 = 무채색 = 흰색/회색
        B, G, R = cv2.split(image)

        # RGB 표준편차 (각 픽셀별)
        rgb_stack = np.stack([R, G, B], axis=-1)
        rgb_std = np.std(rgb_stack, axis=2)

        print(f"  RGB std: {rgb_std.mean():.1f} ± {rgb_std.std():.1f}")

        # 밝기
        brightness = np.max(rgb_stack, axis=2)

        # 흰색: RGB 차이 작고, 밝음
        std_threshold = int(np.percentile(rgb_std, 25))
        brightness_threshold = int(np.percentile(brightness, 75))

        print(f"  RGB std threshold: < {std_threshold}")
        print(f"  Brightness threshold: > {brightness_threshold}")

        white_mask = (rgb_std < std_threshold) & (brightness > brightness_threshold)
        white_mask = white_mask.astype(np.uint8) * 255

        return white_mask, {'rgb_std': rgb_std, 'brightness': brightness}

    elif method == 'lab_achromatic':
        # LAB에서 a,b가 중립(128)에 가까움 = 무채색
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        L, a, b = cv2.split(lab)

        # a,b의 중립값(128)으로부터의 거리
        chroma = np.sqrt((a.astype(float) - 128)**2 + (b.astype(float) - 128)**2)

        print(f"  L: {L.mean():.1f} ± {L.std():.1f}")
        print(f"  Chroma: {chroma.mean():.1f} ± {chroma.std():.1f}")

        # 흰색: 채도 낮고 밝음
        chroma_threshold = int(np.percentile(chroma, 25))
        L_threshold = int(np.percentile(L, 75))

        print(f"  Chroma threshold: < {chroma_threshold}")
        print(f"  L threshold: > {L_threshold}")

        white_mask = (chroma < chroma_threshold) & (L > L_threshold)
        white_mask = white_mask.astype(np.uint8) * 255

        return white_mask, {'L': L, 'chroma': chroma}

    elif method == 'lab_hsv':
        # LAB b-channel AND HSV saturation 교집합
        # LAB: 베이지 vs 흰색 구분
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        L, a, b = cv2.split(lab)

        # HSV: 채도 기반 흰색 구분
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        H, S, V = cv2.split(hsv)

        print(f"  b (yellowness): {b.mean():.1f} ± {b.std():.1f}")
        print(f"  S (saturation): {S.mean():.1f} ± {S.std():.1f}")
        print(f"  V (value): {V.mean():.1f} ± {V.std():.1f}")

        # LAB b threshold
        if s_threshold is not None:
            b_thresh = s_threshold
            print(f"  b threshold: < {b_thresh} (absolute)")
        else:
            b_thresh = int(np.percentile(b, s_percentile if s_percentile else 25))
            print(f"  b threshold: < {b_thresh} (p{s_percentile if s_percentile else 25})")

        # HSV S threshold (v_threshold를 s용으로 재사용)
        if v_threshold is not None:
            s_thresh_hsv = v_threshold
            print(f"  S threshold: < {s_thresh_hsv} (absolute)")
        else:
            s_thresh_hsv = int(np.percentile(S, 50))  # 중간값 사용
            print(f"  S threshold: < {s_thresh_hsv} (p50)")

        # 교집합: LAB AND HSV 모두 만족
        mask_lab = (b < b_thresh)
        mask_hsv = (S < s_thresh_hsv)
        white_mask = (mask_lab & mask_hsv).astype(np.uint8) * 255

        lab_coverage = mask_lab.sum() / mask_lab.size * 100
        hsv_coverage = mask_hsv.sum() / mask_hsv.size * 100
        combined_coverage = (white_mask > 0).sum() / white_mask.size * 100

        print(f"  LAB mask: {lab_coverage:.2f}%")
        print(f"  HSV mask: {hsv_coverage:.2f}%")
        print(f"  Combined (AND): {combined_coverage:.2f}%")

        return white_mask, {'b': b, 'S': S, 'V': V}

    elif method == 'combined':
        # 세 가지 방법 모두 사용 (교집합)

        # 1. HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        H, S, V = cv2.split(hsv)
        s_thresh = int(np.percentile(S, 25))
        v_thresh = int(np.percentile(V, 75))
        mask1 = (S < s_thresh) & (V > v_thresh)

        # 2. RGB balance
        B, G, R = cv2.split(image)
        rgb_stack = np.stack([R, G, B], axis=-1)
        rgb_std = np.std(rgb_stack, axis=2)
        brightness = np.max(rgb_stack, axis=2)
        std_thresh = int(np.percentile(rgb_std, 25))
        bright_thresh = int(np.percentile(brightness, 75))
        mask2 = (rgb_std < std_thresh) & (brightness > bright_thresh)

        # 3. LAB achromatic
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        L, a, b_lab = cv2.split(lab)
        chroma = np.sqrt((a.astype(float) - 128)**2 + (b_lab.astype(float) - 128)**2)
        chroma_thresh = int(np.percentile(chroma, 25))
        L_thresh = int(np.percentile(L, 75))
        mask3 = (chroma < chroma_thresh) & (L > L_thresh)

        # 교집합 (모든 방법이 동의)
        white_mask = mask1 & mask2 & mask3
        white_mask = white_mask.astype(np.uint8) * 255

        print(f"  HSV mask: {mask1.sum() / mask1.size * 100:.2f}%")
        print(f"  RGB mask: {mask2.sum() / mask2.size * 100:.2f}%")
        print(f"  LAB mask: {mask3.sum() / mask3.size * 100:.2f}%")
        print(f"  Combined: {white_mask.sum() / white_mask.size * 100:.2f}%")

        return white_mask, {'S': S, 'V': V, 'chroma': chroma}


def extract_individual_holes(image, mask, min_area=50, max_area=100000, enhance_holes=False, dilation_size=3, border_margin=0):
    """개별 구멍 추출 (자동 해상도 스케일링 적용)

    Args:
        min_area, max_area: 고해상도 기준값 (7216x5412)에서 자동 스케일링
        border_margin: 이미지 가장자리에서 제외할 픽셀 수 (0이면 제외 안함)

    Note:
        입력된 min_area, max_area는 고해상도(7216x5412, 39M pixels) 기준값입니다.
        실제 이미지 해상도에 따라 자동으로 스케일링됩니다.
    """
    h, w = image.shape[:2]
    current_pixels = h * w

    # 기준 해상도: 7216x5412 = 39,061,392 픽셀 (고해상도 .tif 기준)
    REFERENCE_PIXELS = 7216 * 5412

    # 스케일 팩터 계산 (면적 기준)
    scale_factor = current_pixels / REFERENCE_PIXELS

    # 파라미터 스케일링
    min_area_scaled = int(min_area * scale_factor)
    max_area_scaled = int(max_area * scale_factor)

    # 커널 크기 스케일링 (선형 스케일 팩터 사용, 최소 3x3)
    linear_scale = np.sqrt(scale_factor)
    kernel_size = max(3, int(3 * linear_scale))
    # 홀수로 만들기
    if kernel_size % 2 == 0:
        kernel_size += 1

    # border_margin 스케일링
    border_margin_scaled = int(border_margin * linear_scale) if border_margin > 0 else 0

    print(f"\n=== Auto-Scaling (Resolution-Aware) ===")
    print(f"  Current resolution: {w}x{h} ({current_pixels:,} pixels)")
    print(f"  Reference resolution: 7216x5412 ({REFERENCE_PIXELS:,} pixels)")
    print(f"  Scale factor: {scale_factor:.4f} ({linear_scale:.2f}x linear)")
    print(f"  min-area: {min_area} → {min_area_scaled} pixels")
    print(f"  max-area: {max_area:,} → {max_area_scaled:,} pixels")
    print(f"  kernel size: 3x3 → {kernel_size}x{kernel_size}")
    if border_margin > 0:
        print(f"  border-margin: {border_margin} → {border_margin_scaled} pixels")

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Morphological cleanup (스케일링된 커널 사용)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)

    # 구멍 강조: 주변 흰색을 확장하고 내부 검은 점 제거
    if enhance_holes:
        print(f"\n=== Hole Enhancement (dilation: {dilation_size}) ===")
        # Dilation: 흰색 영역을 확장하여 주변 흰색 강조
        dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation_size, dilation_size))
        mask_clean = cv2.dilate(mask_clean, dilate_kernel, iterations=1)

        # Closing: 구멍 내부의 작은 검은 점들 제거
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_CLOSE, close_kernel)

    contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    holes = []
    excluded = 0
    excluded_border = 0

    for cnt in contours:
        area = cv2.contourArea(cnt)

        # 스케일링된 min/max area 사용
        if area < min_area_scaled or area > max_area_scaled:
            excluded += 1
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)

        # 가장자리 필터링 (이미지 테두리에 닿는 것 제외, 스케일링된 margin 사용)
        if border_margin_scaled > 0:
            if (x < border_margin_scaled or y < border_margin_scaled or
                x + bw > w - border_margin_scaled or y + bh > h - border_margin_scaled):
                excluded_border += 1
                continue

        hole_region = image[y:y+bh, x:x+bw].copy()
        hole_mask_small = np.zeros((bh, bw), dtype=np.uint8)
        cnt_shifted = cnt - [x, y]
        cv2.drawContours(hole_mask_small, [cnt_shifted], -1, 255, -1)

        hole_extracted = hole_region.copy()
        hole_extracted[hole_mask_small == 0] = [255, 255, 255]

        holes.append({
            'id': len(holes),
            'image': hole_extracted,
            'bbox': (x, y, bw, bh),
            'area': area,
            'contour': cnt  # SVG 벡터화를 위해 contour 저장
        })

    print(f"\nTotal contours: {len(contours)}")
    print(f"Valid holes: {len(holes)}")
    print(f"Excluded (size): {excluded}")
    if border_margin_scaled > 0:
        print(f"Excluded (border): {excluded_border}")

    # contour는 각 hole 딕셔너리에 저장됨
    return holes


def save_holes(holes, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for hole in holes:
        x, y, w, h = hole['bbox']
        filename = f"hole_{hole['id']:04d}_x{x}_y{y}_w{w}_h{h}_a{int(hole['area'])}.png"
        cv2.imwrite(os.path.join(output_dir, filename), hole['image'])


def detect_tiled_edges(image, contour, margin_threshold=50):
    """타일 스캔에서 이어지는 변 vs 실제 가장자리 구분

    Args:
        image: 원본 이미지
        contour: 문서 contour
        margin_threshold: 이미지 끝으로부터 이 거리 안에 있으면 "이어지는 부분"

    Returns:
        (is_left_edge, is_top_edge, is_right_edge, is_bottom_edge)
        True = 실제 가장자리, False = 이어지는 부분
    """
    h, w = image.shape[:2]
    points = contour.reshape(-1, 2)
    x_coords = points[:, 0]
    y_coords = points[:, 1]

    # 각 변이 이미지 끝에 닿아있는지 확인
    x_min = x_coords.min()
    x_max = x_coords.max()
    y_min = y_coords.min()
    y_max = y_coords.max()

    # 이미지 끝에서 margin 안에 있으면 "이어지는 부분"
    is_left_edge = x_min > margin_threshold  # 왼쪽이 여유있으면 실제 가장자리
    is_top_edge = y_min > margin_threshold   # 위쪽이 여유있으면 실제 가장자리
    is_right_edge = (w - x_max) > margin_threshold  # 오른쪽이 여유있으면 실제 가장자리
    is_bottom_edge = (h - y_max) > margin_threshold  # 아래쪽이 여유있으면 실제 가장자리

    print(f"  Tile edge detection:")
    print(f"    Left: {'real edge' if is_left_edge else 'continues to next tile'} (dist from border: {x_min})")
    print(f"    Right: {'real edge' if is_right_edge else 'continues to next tile'} (dist from border: {w - x_max})")
    print(f"    Top: {'real edge' if is_top_edge else 'continues to next tile'} (dist from border: {y_min})")
    print(f"    Bottom: {'real edge' if is_bottom_edge else 'continues to next tile'} (dist from border: {h - y_max})")

    return is_left_edge, is_top_edge, is_right_edge, is_bottom_edge


def find_edge_boundaries(contour, image_shape, percentile=2.0, tile_edges=None):
    """Contour에서 상하좌우 각 변을 독립적으로 찾기

    Args:
        contour: 문서 contour
        image_shape: (height, width)
        percentile: 극단값 제거 비율 (2 = 2%~98%, 작은 노이즈 무시)
        tile_edges: (is_left, is_top, is_right, is_bottom) 타일 경계 정보

    Returns:
        (x, y, w, h): 사각형 좌표
    """
    h, w = image_shape[:2]
    points = contour.reshape(-1, 2)
    x_coords = points[:, 0]
    y_coords = points[:, 1]

    # 각 변을 독립적으로 찾기
    # 각 변에서 극단값 5%를 후보로 추출

    # 왼쪽 변
    left_candidates = x_coords[x_coords <= np.percentile(x_coords, 5)]
    x_min = int(np.percentile(left_candidates, percentile)) if len(left_candidates) > 0 else int(x_coords.min())

    # 오른쪽 변
    right_candidates = x_coords[x_coords >= np.percentile(x_coords, 95)]
    x_max = int(np.percentile(right_candidates, 100 - percentile)) if len(right_candidates) > 0 else int(x_coords.max())

    # 위쪽 변
    top_candidates = y_coords[y_coords <= np.percentile(y_coords, 5)]
    y_min = int(np.percentile(top_candidates, percentile)) if len(top_candidates) > 0 else int(y_coords.min())

    # 아래쪽 변
    bottom_candidates = y_coords[y_coords >= np.percentile(y_coords, 95)]
    y_max = int(np.percentile(bottom_candidates, 100 - percentile)) if len(bottom_candidates) > 0 else int(y_coords.max())

    # 타일 경계 정보가 있으면 확장
    if tile_edges is not None:
        is_left, is_top, is_right, is_bottom = tile_edges

        original_x_min, original_y_min = x_min, y_min
        original_x_max, original_y_max = x_max, y_max

        # 이어지는 부분은 이미지 끝까지 확장 (마진 없이!)
        if not is_left:  # 왼쪽이 이어지는 부분
            x_min = 0
        if not is_top:   # 위쪽이 이어지는 부분
            y_min = 0
        if not is_right:  # 오른쪽이 이어지는 부분
            x_max = w - 1
        if not is_bottom:  # 아래쪽이 이어지는 부분
            y_max = h - 1

        print(f"  Edge boundaries (with tile expansion):")
        print(f"    Left: x={original_x_min} → {x_min} {'(expanded to tile edge)' if not is_left else ''}")
        print(f"    Right: x={original_x_max} → {x_max} {'(expanded to tile edge)' if not is_right else ''}")
        print(f"    Top: y={original_y_min} → {y_min} {'(expanded to tile edge)' if not is_top else ''}")
        print(f"    Bottom: y={original_y_max} → {y_max} {'(expanded to tile edge)' if not is_bottom else ''}")
    else:
        print(f"  Edge boundaries (independent):")
        print(f"    Left: x={x_min} (from {len(left_candidates)} candidates)")
        print(f"    Right: x={x_max} (from {len(right_candidates)} candidates)")
        print(f"    Top: y={y_min} (from {len(top_candidates)} candidates)")
        print(f"    Bottom: y={y_max} (from {len(bottom_candidates)} candidates)")

    return (x_min, y_min, x_max - x_min, y_max - y_min)


def find_robust_rectangle_from_contour(contour, image_shape, corner_method='convex', image=None):
    """Contour에서 robust하게 4개 코너를 찾아 사각형 생성

    Args:
        contour: 문서 contour
        image_shape: (height, width)
        corner_method: 'edges', 'convex', 'percentile', 'minarea', 'bbox'
        image: 원본 이미지 (타일 경계 감지용, 선택)

    Returns:
        (x, y, w, h): 사각형 좌표
    """
    h, w = image_shape[:2]

    if corner_method == 'edges':
        # 각 변을 독립적으로 찾기 (추천!)
        # 타일 경계 감지: 이미지가 있으면 어느 변이 이어지는지 판단
        tile_edges = None
        if image is not None:
            tile_edges = detect_tiled_edges(image, contour, margin_threshold=50)
            is_left, is_top, is_right, is_bottom = tile_edges
            print(f"  Tile edge detection: left={is_left}, top={is_top}, right={is_right}, bottom={is_bottom}")
            print(f"    (True = 실제 가장자리, False = 다른 타일과 이어지는 부분)")

        return find_edge_boundaries(contour, image_shape, percentile=0.5, tile_edges=tile_edges)

    elif corner_method == 'convex':
        # Convex hull로 울퉁불퉁한 부분 메우기
        hull = cv2.convexHull(contour)

        # 4개 점으로 근사 (사각형)
        epsilon = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)

        # 점을 더 줄여가며 4개가 될 때까지 시도
        max_attempts = 20
        for attempt in range(max_attempts):
            if len(approx) <= 4:
                break
            epsilon *= 1.5
            approx = cv2.approxPolyDP(hull, epsilon, True)

        # 4개 점이면 사용, 아니면 bounding rect
        if len(approx) == 4:
            points = approx.reshape(-1, 2)
            x_min, y_min = points.min(axis=0)
            x_max, y_max = points.max(axis=0)
            print(f"  Convex hull approximation: 4 corners found")
            return (int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min))
        else:
            print(f"  ⚠️ Could not approximate to 4 corners ({len(approx)} points), using bounding rect")
            return cv2.boundingRect(hull)

    elif corner_method == 'percentile':
        # 각 변에서 extreme points를 찾고 robust하게 평균
        points = contour.reshape(-1, 2)
        x_coords = points[:, 0]
        y_coords = points[:, 1]

        # 각 방향에서 extreme points 여러 개 추출
        # 왼쪽 변: x가 가장 작은 상위 N개 점들
        n_samples = max(10, len(points) // 100)  # 최소 10개, 또는 1%

        left_indices = np.argsort(x_coords)[:n_samples]
        right_indices = np.argsort(x_coords)[-n_samples:]
        top_indices = np.argsort(y_coords)[:n_samples]
        bottom_indices = np.argsort(y_coords)[-n_samples:]

        # 각 변에서 median 값 사용 (robust)
        x_min = int(np.median(x_coords[left_indices]))
        x_max = int(np.median(x_coords[right_indices]))
        y_min = int(np.median(y_coords[top_indices]))
        y_max = int(np.median(y_coords[bottom_indices]))

        print(f"  Percentile method: used top {n_samples} extreme points per side")
        return (x_min, y_min, x_max - x_min, y_max - y_min)

    elif corner_method == 'minarea':
        # 최소 면적 회전 사각형
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        # Axis-aligned bounding box로 변환
        x_min, y_min = box.min(axis=0)
        x_max, y_max = box.max(axis=0)

        print(f"  MinAreaRect method: angle={rect[2]:.1f}°")
        return (int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min))

    else:
        # 기본값: 일반 bounding rect
        return cv2.boundingRect(contour)


def find_grid_lines(image, min_line_length_ratio=0.3):
    """이미지에서 문서 격자를 형성하는 가로선/세로선 찾기

    Args:
        image: 원본 이미지
        min_line_length_ratio: 최소 직선 길이 비율

    Returns:
        (vertical_lines, horizontal_lines): 세로선 x좌표들, 가로선 y좌표들
    """
    h, w = image.shape[:2]
    print(f"\n=== Grid Line Detection ===")

    # Canny edge detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)

    # Hough Line으로 직선 찾기
    min_length_h = int(w * min_line_length_ratio)  # 가로선 최소 길이
    min_length_v = int(h * min_line_length_ratio)  # 세로선 최소 길이

    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80,
                            minLineLength=min(min_length_h, min_length_v),
                            maxLineGap=30)

    if lines is None:
        print(f"  No grid lines found")
        return [], []

    vertical_lines = []
    horizontal_lines = []

    for line in lines:
        x1, y1, x2, y2 = line[0]

        # 선의 길이와 각도
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        if x2 - x1 == 0:
            angle = 90
        else:
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

        # 세로선 (85~95도, 길이가 이미지 높이의 50% 이상)
        if 85 < angle < 95 and length >= min_length_v:
            x_mid = (x1 + x2) // 2
            vertical_lines.append((x_mid, length))

        # 가로선 (0~10도 또는 170~180도, 길이가 이미지 너비의 50% 이상)
        elif (angle < 10 or angle > 170) and length >= min_length_h:
            y_mid = (y1 + y2) // 2
            horizontal_lines.append((y_mid, length))

    # 그룹화 및 정렬
    def group_lines(lines, threshold=50):
        if not lines:
            return []
        lines.sort(key=lambda x: x[0])
        grouped = []
        current_group = [lines[0]]

        for line in lines[1:]:
            pos, length = line
            prev_pos = current_group[-1][0]

            if abs(pos - prev_pos) < threshold:
                current_group.append(line)
            else:
                # 가장 긴 선 선택
                best = max(current_group, key=lambda x: x[1])
                grouped.append(best[0])
                current_group = [line]

        if current_group:
            best = max(current_group, key=lambda x: x[1])
            grouped.append(best[0])

        return sorted(grouped)

    v_lines = group_lines(vertical_lines, threshold=50)
    h_lines = group_lines(horizontal_lines, threshold=50)

    print(f"  Vertical lines: {len(v_lines)} found at x={v_lines}")
    print(f"  Horizontal lines: {len(h_lines)} found at y={h_lines}")

    return v_lines, h_lines


def create_grid_tiles(image_shape, v_lines, h_lines, margin=10):
    """격자선으로 타일 영역 생성

    Args:
        image_shape: (height, width)
        v_lines: 세로선 x좌표 리스트
        h_lines: 가로선 y좌표 리스트
        margin: 격자선으로부터의 여백 (선 제외)

    Returns:
        List[(x, y, w, h)]: 타일 영역들
    """
    h, w = image_shape[:2]

    # 경계 포함
    x_boundaries = [0] + v_lines + [w]
    y_boundaries = [0] + h_lines + [h]

    tiles = []
    for i in range(len(y_boundaries) - 1):
        for j in range(len(x_boundaries) - 1):
            x1 = x_boundaries[j] + margin
            x2 = x_boundaries[j + 1] - margin
            y1 = y_boundaries[i] + margin
            y2 = y_boundaries[i + 1] - margin

            if x2 > x1 and y2 > y1:  # 유효한 영역만
                tiles.append((x1, y1, x2 - x1, y2 - y1))

    print(f"  Created {len(tiles)} tiles from grid")
    return tiles


def detect_document_boundary(image, method='brightness', corner_method='percentile',
                             detect_tiles=False, debug=False, return_tile_edges=False):
    """문서의 경계를 자동으로 감지하여 사각형 ROI 반환

    Args:
        image: 입력 이미지 (BGR)
        method: 감지 방법 ('brightness', 'edges')
        corner_method: 코너 찾기 방법 ('convex', 'percentile', 'minarea', 'bbox')
        detect_tiles: 타일 스캔 세로선 감지 여부
        debug: 디버그 이미지 출력 여부
        return_tile_edges: 타일 경계 정보도 반환할지 여부

    Returns:
        (x, y, w, h): 문서 영역의 bounding rectangle
        또는 return_tile_edges=True: ((x, y, w, h), tile_edges)
        또는 detect_tiles=True일 경우: List[(x, y, w, h)] (여러 타일)
        None: 감지 실패시
    """
    print(f"\n=== Document Boundary Detection ({method}, corners={corner_method}) ===")

    h, w = image.shape[:2]

    if method == 'brightness':
        # LAB b-channel 사용 (베이지색/노란색 기반) ⭐⭐⭐
        # 문서(종이)는 베이지/노란색, 배경(스캔)은 흰색
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        L, a, b_channel = cv2.split(lab)

        print(f"  L (brightness): {L.mean():.1f} ± {L.std():.1f}")
        print(f"  b (yellowness): {b_channel.mean():.1f} ± {b_channel.std():.1f}")

        # b-channel threshold 자동 계산 (Otsu)
        # 문서 = 베이지색(b > threshold), 배경 = 흰색(b < threshold)
        b_thresh, doc_mask = cv2.threshold(b_channel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        print(f"  Auto b-channel threshold: b > {b_thresh:.1f} (Otsu)")

        # Morphological operations로 정리 (최소한만 사용)
        # 문서 내부의 작은 구멍들은 채우되, boundary는 최대한 보존
        kernel_close = max(20, int(min(w, h) * 0.005))  # 내부 구멍 메우기용
        kernel_open = max(5, int(min(w, h) * 0.001))    # 외부 노이즈 제거용 (작게)
        print(f"  Morphology kernel: close={kernel_close}x{kernel_close}, open={kernel_open}x{kernel_open}")

        # Close는 크게 해서 내부 구멍 메우기
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_close, kernel_close))
        doc_mask = cv2.morphologyEx(doc_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Open은 작게 해서 경계 보존
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_open, kernel_open))
        doc_mask = cv2.morphologyEx(doc_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # 가장 큰 contour 찾기 (문서 영역)
        contours, _ = cv2.findContours(doc_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            print("  ⚠️ No contours found!")
            return None

        # 면적 기준 정렬
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        largest_contour = contours[0]
        largest_area = cv2.contourArea(largest_contour)

        print(f"  Found {len(contours)} contours")
        print(f"  Largest contour area: {largest_area:,.0f} pixels ({largest_area/(w*h)*100:.1f}%)")

        # 가장 큰 contour가 이미지 전체의 최소 30% 이상이어야 함
        if largest_area < (w * h * 0.3):
            print(f"  ⚠️ Largest contour too small (< 30% of image)")
            return None

        # Robust하게 사각형 찾기 (타일 경계 감지 위해 image 전달)
        x, y, bw, bh = find_robust_rectangle_from_contour(largest_contour, (h, w), corner_method, image=image)

        print(f"  Document boundary: x={x}, y={y}, w={bw}, h={bh}")
        print(f"  Document size: {bw}x{bh} ({bw*bh:,} pixels, {bw*bh/(w*h)*100:.1f}%)")

        # 타일 경계 정보 추출 (return_tile_edges=True일 때)
        tile_edges_info = None
        if return_tile_edges and corner_method == 'edges':
            # detect_tiled_edges를 다시 호출해서 정보 가져오기
            tile_edges_info = detect_tiled_edges(image, largest_contour, margin_threshold=50)

        # 타일 스캔 감지 (격자선으로 분할)
        if detect_tiles:
            v_lines, h_lines = find_grid_lines(image)

            if v_lines or h_lines:
                tiles = create_grid_tiles((h, w), v_lines, h_lines, margin=10)

                print(f"\n=== Tile Grid ===")
                for i, tile in enumerate(tiles):
                    tx, ty, tw, th = tile
                    print(f"  Tile {i+1}: x={tx}, y={ty}, w={tw}, h={th}")

                if debug:
                    return tiles, doc_mask
                return tiles
            else:
                print(f"  No grid lines found, returning single boundary")

        if debug:
            return (x, y, bw, bh), doc_mask

        if return_tile_edges:
            return (x, y, bw, bh), tile_edges_info

        return (x, y, bw, bh)

    elif method == 'edges':
        # Canny edge detection으로 문서 경계 찾기
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Hough lines로 직선 찾기
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100,
                                minLineLength=min(w, h)*0.3, maxLineGap=50)

        if lines is None:
            print("  ⚠️ No lines found!")
            return None

        # 수평선과 수직선 분류
        horizontal_lines = []
        vertical_lines = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

            if angle < 10 or angle > 170:  # 수평선
                horizontal_lines.append((y1 + y2) / 2)
            elif 80 < angle < 100:  # 수직선
                vertical_lines.append((x1 + x2) / 2)

        if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
            print(f"  ⚠️ Not enough lines (H:{len(horizontal_lines)}, V:{len(vertical_lines)})")
            return None

        # 상하좌우 경계 찾기
        top = int(min(horizontal_lines))
        bottom = int(max(horizontal_lines))
        left = int(min(vertical_lines))
        right = int(max(vertical_lines))

        x, y = left, top
        bw, bh = right - left, bottom - top

        print(f"  Document boundary: x={x}, y={y}, w={bw}, h={bh}")

        return (x, y, bw, bh)

    else:
        raise ValueError(f"Unknown method: {method}")


def apply_document_boundary(mask, boundary, margin=0):
    """마스크에 문서 경계를 적용 (경계 밖 영역 제거)

    Args:
        mask: 입력 마스크 (이진 이미지)
        boundary: (x, y, w, h) 문서 경계
        margin: 경계에서 추가로 제외할 픽셀 수 (양수=안쪽으로, 음수=바깥쪽으로)

    Returns:
        bounded_mask: 경계가 적용된 마스크
    """
    if boundary is None:
        return mask

    h, w = mask.shape[:2]
    x, y, bw, bh = boundary

    # margin 적용
    x_start = max(0, x + margin)
    y_start = max(0, y + margin)
    x_end = min(w, x + bw - margin)
    y_end = min(h, y + bh - margin)

    # 새로운 마스크 (경계 밖은 모두 0)
    bounded_mask = np.zeros_like(mask)
    bounded_mask[y_start:y_end, x_start:x_end] = mask[y_start:y_end, x_start:x_end]

    removed_pixels = (mask > 0).sum() - (bounded_mask > 0).sum()
    removed_percent = removed_pixels / mask.size * 100

    print(f"\n=== Document Boundary Applied ===")
    print(f"  Boundary: x={x}, y={y}, w={bw}, h={bh}")
    if margin != 0:
        print(f"  Margin: {margin} pixels ({'inward' if margin > 0 else 'outward'})")
        print(f"  Effective area: {x_start},{y_start} to {x_end},{y_end}")
    print(f"  Removed pixels: {removed_pixels:,} ({removed_percent:.2f}%)")

    return bounded_mask


def remove_tile_edge_artifacts(image, boundary, tile_edges, edge_width=3):
    """타일 경계의 스캔 아티팩트 제거 (원본 이미지 수정)

    Args:
        image: 원본 이미지 (BGR)
        boundary: (x, y, w, h) 문서 경계
        tile_edges: (is_left, is_top, is_right, is_bottom) 타일 경계 정보
        edge_width: 경계선 제거 범위 (픽셀) - 실제 스캔 라인만 (3px 정도)

    Returns:
        cleaned_image: 경계선이 제거된 이미지
    """
    if tile_edges is None:
        return image

    # Inpaint 기능 제거됨 - 원본 이미지 반환
    return image


def contour_to_svg_path(contour, simplify_epsilon=1.0):
    """OpenCV contour를 SVG path로 변환 (벡터화)

    Args:
        contour: OpenCV contour
        simplify_epsilon: 윤곽선 단순화 정도 (작을수록 정밀, 클수록 단순)

    Returns:
        SVG path string (예: "M 10,20 L 30,40 L 50,30 Z")
    """
    if len(contour) < 3:
        return None

    # 윤곽선 단순화 (레이저 커팅에 최적화)
    simplified = cv2.approxPolyDP(contour, simplify_epsilon, True)

    if len(simplified) < 3:
        return None

    path_data = []

    # 시작점
    start = simplified[0][0]
    path_data.append(f'M {start[0]},{start[1]}')

    # 나머지 점들
    for point in simplified[1:]:
        x, y = point[0]
        path_data.append(f'L {x},{y}')

    # 경로 닫기
    path_data.append('Z')

    return ' '.join(path_data)


def save_holes_svg(holes, image_width, image_height, output_dir,
                   simplify_epsilon=1.0, dpi=300, unified=True, individual=True):
    """구멍들을 SVG 벡터 형식으로 저장 (레이저 커팅용)

    Args:
        holes: 구멍 정보 리스트 (각 hole에 'contour' 포함)
        image_width, image_height: 이미지 크기 (픽셀)
        output_dir: 출력 디렉토리
        simplify_epsilon: 윤곽선 단순화 정도
        dpi: 이미지 DPI (물리적 크기 계산용, 기본 300)
        unified: 전체 통합 SVG 파일 생성 여부
        individual: 개별 구멍 SVG 파일 생성 여부
    """
    os.makedirs(output_dir, exist_ok=True)
    svg_dir = os.path.join(output_dir, 'svg_vectors')
    os.makedirs(svg_dir, exist_ok=True)

    # DPI 기반 물리적 크기 계산 (mm 단위)
    mm_per_inch = 25.4
    width_mm = (image_width / dpi) * mm_per_inch
    height_mm = (image_height / dpi) * mm_per_inch

    print(f"\n=== SVG Vector Export ===")
    print(f"  Image size: {image_width}x{image_height} pixels")
    print(f"  Physical size: {width_mm:.1f}x{height_mm:.1f} mm (at {dpi} DPI)")
    print(f"  Simplification: {simplify_epsilon}")
    print(f"  Total holes: {len(holes)}")

    # 각 구멍을 SVG path로 변환
    hole_paths = []
    total_points_before = 0
    total_points_after = 0

    for hole in holes:
        # 각 hole에 contour가 저장되어 있음
        if 'contour' not in hole:
            continue

        contour = hole['contour']
        total_points_before += len(contour)

        path_data = contour_to_svg_path(contour, simplify_epsilon)
        if path_data:
            # 단순화 후 포인트 수 계산
            total_points_after += path_data.count('L') + 1

            hole_info = {
                'id': hole['id'],
                'path': path_data,
                'bbox': hole['bbox'],
                'area_px': hole['area'],
                'area_mm2': (hole['area'] / (dpi / mm_per_inch) ** 2)
            }
            hole_paths.append(hole_info)

            # 개별 SVG 파일 저장
            if individual:
                x, y, w, h = hole['bbox']
                individual_svg_path = os.path.join(
                    svg_dir,
                    f"hole_{hole['id']:04d}_x{x}_y{y}_a{int(hole['area'])}.svg"
                )
                create_individual_svg(hole_info, image_width, image_height,
                                    width_mm, height_mm, individual_svg_path)

    if total_points_before > 0:
        reduction = (1 - total_points_after / total_points_before) * 100
        print(f"  Path simplification: {total_points_before:,} → {total_points_after:,} points ({reduction:.1f}% reduction)")

    # 전체 통합 SVG 파일 저장
    if unified and hole_paths:
        unified_svg_path = os.path.join(output_dir, 'all_holes_vector.svg')
        create_unified_svg(hole_paths, image_width, image_height,
                          width_mm, height_mm, unified_svg_path)
        print(f"  Unified SVG: {unified_svg_path}")

    print(f"  Individual SVGs: {svg_dir}/")
    print(f"  Total exported: {len(hole_paths)} holes")


def create_individual_svg(hole_info, img_w, img_h, width_mm, height_mm, svg_path):
    """개별 구멍 SVG 파일 생성 (중앙 배치, 원본 좌표 유지)"""

    # Bounding box 계산 (약간의 여백 추가)
    x, y, w, h = hole_info['bbox']
    margin = max(10, int(max(w, h) * 0.1))  # 10% 여백 또는 최소 10px

    vb_x = max(0, x - margin)
    vb_y = max(0, y - margin)
    vb_w = min(img_w - vb_x, w + margin * 2)
    vb_h = min(img_h - vb_y, h + margin * 2)

    # 물리적 크기 계산 (DPI 기준)
    dpi = 300
    inch_to_mm = 25.4
    physical_w = (vb_w / dpi) * inch_to_mm
    physical_h = (vb_h / dpi) * inch_to_mm

    svg = ET.Element('svg', {
        'xmlns': 'http://www.w3.org/2000/svg',
        'width': f'{physical_w:.2f}mm',
        'height': f'{physical_h:.2f}mm',
        'viewBox': f'{vb_x} {vb_y} {vb_w} {vb_h}'  # 구멍 주변만 보이도록
    })

    # 메타데이터 (원본 위치 정보 포함)
    metadata = ET.SubElement(svg, 'metadata')
    ET.SubElement(metadata, 'hole_id').text = str(hole_info['id'])
    ET.SubElement(metadata, 'original_position').text = f"x={x}, y={y}"
    ET.SubElement(metadata, 'original_image_size').text = f"{img_w}x{img_h}"
    ET.SubElement(metadata, 'bbox').text = f"x={x}, y={y}, w={w}, h={h}"
    ET.SubElement(metadata, 'area_pixels').text = f"{hole_info['area_px']:.0f}"
    ET.SubElement(metadata, 'area_mm2').text = f"{hole_info['area_mm2']:.2f}"

    # 구멍 path (원본 좌표 그대로 - viewBox가 자동으로 확대)
    path = ET.SubElement(svg, 'path', {
        'id': f"hole_{hole_info['id']}",
        'd': hole_info['path'],
        'fill': 'none',
        'stroke': 'black',
        'stroke-width': '1',
        'vector-effect': 'non-scaling-stroke'
    })

    # 저장
    xml_string = ET.tostring(svg, encoding='unicode')
    dom = minidom.parseString(xml_string)
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(dom.toprettyxml(indent='  '))


def create_unified_svg(hole_paths, img_w, img_h, width_mm, height_mm, svg_path):
    """전체 구멍 통합 SVG 파일 생성 (레이저 커팅용)"""
    svg = ET.Element('svg', {
        'xmlns': 'http://www.w3.org/2000/svg',
        'width': f'{width_mm}mm',
        'height': f'{height_mm}mm',
        'viewBox': f'0 0 {img_w} {img_h}'
    })

    # 메타데이터
    metadata = ET.SubElement(svg, 'metadata')
    ET.SubElement(metadata, 'total_holes').text = str(len(hole_paths))
    ET.SubElement(metadata, 'document_size_mm').text = f'{width_mm:.1f}x{height_mm:.1f}'

    # 모든 구멍을 하나의 그룹으로
    group = ET.SubElement(svg, 'g', {
        'id': 'all_holes',
        'fill': 'none',
        'stroke': 'black',
        'stroke-width': '1'
    })

    for hole_info in hole_paths:
        path = ET.SubElement(group, 'path', {
            'id': f"hole_{hole_info['id']:04d}",
            'd': hole_info['path'],
            'data-area-px': f"{hole_info['area_px']:.0f}",
            'data-area-mm2': f"{hole_info['area_mm2']:.2f}"
        })

    # 저장
    xml_string = ET.tostring(svg, encoding='unicode')
    dom = minidom.parseString(xml_string)
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(dom.toprettyxml(indent='  '))


def create_comparison(original, holes, output_path, boundary=None):
    h, w = original.shape[:2]
    comparison = np.zeros((h, w*2, 3), dtype=np.uint8)

    comparison[0:h, 0:w] = original

    mapped = original.copy()

    # 문서 경계 표시 (파란색 사각형)
    if boundary is not None:
        bx, by, bw, bh = boundary
        cv2.rectangle(mapped, (bx, by), (bx+bw, by+bh), (255, 0, 0), 1)

    # 구멍 표시 (녹색 사각형)
    for hole in holes:
        x, y, hw, hh = hole['bbox']
        cv2.rectangle(mapped, (x, y), (x+hw, y+hh), (0, 255, 0), 1)

    comparison[0:h, w:2*w] = mapped

    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(comparison, "Original", (10, 30), font, 1.0, (255, 255, 255), 2)
    text = f"Detected: {len(holes)} holes"
    if boundary is not None:
        text += " (with boundary)"
    cv2.putText(comparison, text, (w+10, 30), font, 1.0, (0, 255, 0), 2)

    cv2.imwrite(output_path, comparison)


def main():
    parser = argparse.ArgumentParser(description='Whiteness-based hole detection')
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output-dir', type=str, default='results/whiteness')
    parser.add_argument('--method', type=str, default='hsv',
                       choices=['lab_b', 'hsv', 'lab_hsv', 'rgb_balance', 'lab_achromatic', 'combined'])
    parser.add_argument('--s-percentile', type=int, default=25,
                       help='Saturation percentile (lower=stricter, default: 25)')
    parser.add_argument('--v-percentile', type=int, default=75,
                       help='Value percentile (higher=stricter, default: 75)')
    parser.add_argument('--s-threshold', type=int, default=None,
                       help='Absolute saturation threshold (overrides s-percentile)')
    parser.add_argument('--v-threshold', type=int, default=None,
                       help='Absolute value threshold (overrides v-percentile)')
    parser.add_argument('--min-area', type=int, default=50,
                       help='Minimum hole area in pixels (7216x5412 reference, auto-scaled, default: 50)')
    parser.add_argument('--max-area', type=int, default=500000,
                       help='Maximum hole area in pixels (7216x5412 reference, auto-scaled, default: 500000)')
    parser.add_argument('--enhance-holes', action='store_true',
                       help='Enhance holes by dilating and removing internal noise')
    parser.add_argument('--dilation-size', type=int, default=5,
                       help='Dilation kernel size for hole enhancement (default: 5)')
    parser.add_argument('--border-margin', type=int, default=0,
                       help='Exclude holes near image border (7216x5412 reference, auto-scaled, default: 0=disabled)')

    # 문서 경계 감지 옵션
    parser.add_argument('--crop-document', action='store_true',
                       help='Auto-detect and crop to document boundary (excludes background)')
    parser.add_argument('--boundary-method', type=str, default='brightness',
                       choices=['brightness', 'edges'],
                       help='Document boundary detection method (default: brightness)')
    parser.add_argument('--corner-method', type=str, default='edges',
                       choices=['edges', 'convex', 'bbox', 'minarea', 'percentile'],
                       help='Corner detection method: edges=independent edges (recommended), convex=convex hull, bbox=simple box, minarea=min area rect, percentile=experimental (default: edges)')
    parser.add_argument('--boundary-margin', type=int, default=0,
                       help='Additional margin from document boundary in pixels (positive=inward, negative=outward, default: 0)')
    parser.add_argument('--detect-tiles', action='store_true',
                       help='Detect vertical separators in tiled scans (multiple documents side by side)')

    # SVG 벡터 출력 옵션
    parser.add_argument('--export-svg', action='store_true',
                       help='Export holes as SVG vector format (for laser cutting)')
    parser.add_argument('--svg-dpi', type=int, default=300,
                       help='DPI for physical size calculation (default: 300)')
    parser.add_argument('--svg-simplify', type=float, default=1.0,
                       help='SVG path simplification (0.5=detailed, 2.0=simple, default: 1.0)')
    parser.add_argument('--svg-individual', action='store_true',
                       help='Export individual SVG files for each hole')
    parser.add_argument('--svg-unified', action='store_true', default=True,
                       help='Export unified SVG file with all holes (default: True)')

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    holes_dir = os.path.join(args.output_dir, 'individual_holes')

    # 로드
    print(f"Loading: {args.input}")
    try:
        with open(args.input, 'rb') as f:
            image_array = np.frombuffer(f.read(), dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if image is None:
            raise Exception("Failed")
    except Exception as e:
        print(f"Error: {e}")
        return

    h, w = image.shape[:2]
    print(f"Size: {w}x{h}")

    # 문서 경계 감지
    document_boundary = None
    tile_edges = None
    image_cleaned = image  # 경계선 제거 전 원본

    if args.crop_document:
        result = detect_document_boundary(image,
                                         method=args.boundary_method,
                                         corner_method=args.corner_method,
                                         detect_tiles=args.detect_tiles,
                                         return_tile_edges=True)

        # 단일 경계 또는 여러 타일
        if result is not None:
            # 타일인지 단일 경계인지 확인
            if isinstance(result, list):
                # 여러 타일
                document_boundary = result[0]  # 첫 번째 타일만 사용 (임시)
                print(f"\n[WARNING] Multiple tiles detected, but currently using only first tile")
                print(f"   To process all tiles separately, future implementation needed")

                # 모든 타일 시각화 (격자로 표시)
                vis_img = image.copy()
                for i, (bx, by, bw, bh) in enumerate(result):
                    # 각 타일마다 다른 색상
                    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
                             (255, 255, 0), (255, 0, 255), (0, 255, 255)]
                    color = colors[i % len(colors)]
                    cv2.rectangle(vis_img, (bx, by), (bx+bw, by+bh), color, 1)
                    # 타일 번호 표시
                    cv2.putText(vis_img, f"{i+1}", (bx+20, by+50),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 2)
                cv2.imwrite(f"{args.output_dir}/document_boundary_tiles.png", vis_img)
                print(f"  Saved grid visualization: document_boundary_tiles.png")
            elif isinstance(result, tuple) and len(result) == 2:
                # 단일 경계 + tile_edges 정보
                document_boundary, tile_edges = result
                vis_img = image.copy()
                bx, by, bw, bh = document_boundary
                cv2.rectangle(vis_img, (bx, by), (bx+bw, by+bh), (255, 0, 0), 1)
                cv2.imwrite(f"{args.output_dir}/document_boundary.png", vis_img)
            else:
                # 단일 경계 (tile_edges 없음)
                document_boundary = result
                vis_img = image.copy()
                bx, by, bw, bh = document_boundary
                cv2.rectangle(vis_img, (bx, by), (bx+bw, by+bh), (255, 0, 0), 1)
                cv2.imwrite(f"{args.output_dir}/document_boundary.png", vis_img)

    # 타일 경계선 제거 (구멍 검출 전에 원본 이미지 정리)
    if tile_edges is not None and document_boundary is not None:
        image_cleaned = remove_tile_edge_artifacts(image, document_boundary, tile_edges, edge_width=10)
        cv2.imwrite(f"{args.output_dir}/image_cleaned.png", image_cleaned)

    # 흰색 감지 (정리된 이미지 사용)
    white_mask, info = detect_whiteness(image_cleaned, args.method, args.s_percentile, args.v_percentile,
                                       args.s_threshold, args.v_threshold)
    cv2.imwrite(f"{args.output_dir}/white_mask_raw.png", white_mask)

    # 문서 경계 적용
    if document_boundary is not None:
        white_mask = apply_document_boundary(white_mask, document_boundary, args.boundary_margin)

    cv2.imwrite(f"{args.output_dir}/white_mask.png", white_mask)

    coverage = (white_mask > 0).sum() / white_mask.size * 100
    print(f"\nWhite coverage: {coverage:.2f}%")

    # 구멍 추출 (정리된 이미지 사용)
    holes = extract_individual_holes(image_cleaned, white_mask, args.min_area, args.max_area,
                                     enhance_holes=args.enhance_holes,
                                     dilation_size=args.dilation_size,
                                     border_margin=args.border_margin)

    if len(holes) == 0:
        print("No holes found!")
        return

    # y좌표 역순 정렬 (아래→위)
    holes = sorted(holes, key=lambda h: h['bbox'][1], reverse=True)
    # ID 재할당
    for i, hole in enumerate(holes):
        hole['id'] = i

    save_holes(holes, holes_dir)
    create_comparison(image_cleaned, holes, f"{args.output_dir}/comparison.png", boundary=document_boundary)

    # SVG 벡터 출력
    if args.export_svg:
        save_holes_svg(holes, w, h, args.output_dir,
                      simplify_epsilon=args.svg_simplify,
                      dpi=args.svg_dpi,
                      unified=args.svg_unified,
                      individual=args.svg_individual)

    # 통계
    areas = [h['area'] for h in holes]
    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60)
    print(f"Method: Whiteness ({args.method})")
    print(f"Total holes: {len(holes)}")
    print(f"Area range: {min(areas):.0f} - {max(areas):.0f}")
    print(f"Average: {np.mean(areas):.1f}")
    print(f"Median: {np.median(areas):.1f}")
    print(f"Total: {sum(areas):.0f} pixels ({sum(areas)/(w*h)*100:.2f}%)")
    print("="*60)
    print(f"\nResults: {args.output_dir}/")


if __name__ == '__main__':
    main()
