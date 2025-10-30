# SVG 최적화 및 시각화 개선

**작성일**: 2025-10-30

---

## 목차
1. [작업 개요](#작업-개요)
2. [문제점 및 개선사항](#문제점-및-개선사항)
3. [주요 변경사항](#주요-변경사항)
4. [SVG 개별 파일 중앙 배치](#svg-개별-파일-중앙-배치)
5. [검증 도구 개선](#검증-도구-개선)
6. [처리 결과](#처리-결과)
7. [최종 권장 설정](#최종-권장-설정)

---

## 작업 개요

타일 경계 감지 기능이 완성된 후, SVG 벡터 출력과 시각화를 최적화하는 작업을 수행했습니다.

### 주요 목표:
1. ✅ 시각화 선 두께 최적화
2. ✅ SVG 벡터 정밀도 향상 (원본 형태 보존)
3. ✅ 개별 SVG 파일 사용성 개선 (중앙 배치)
4. ✅ 구멍 번호 추적 기능 추가
5. ✅ 다중 이미지 일괄 처리

---

## 문제점 및 개선사항

### 문제 1: 시각화 선이 너무 두꺼움

**증상**:
```
comparison.png에서:
- 파란색 문서 경계선: 3px
- 녹색 구멍 박스: 2px
→ 선이 두꺼워서 문서 내용이 잘 안보임
```

**해결**:
```python
# extract_whiteness_based.py (Line 1026-1034)

# 변경 전:
cv2.rectangle(mapped, (bx, by), (bx+bw, by+bh), (255, 0, 0), 3)  # 파란색 경계
cv2.rectangle(mapped, (x, y), (x+hw, y+hh), (0, 255, 0), 2)      # 녹색 구멍

# 변경 후:
cv2.rectangle(mapped, (bx, by), (bx+bw, by+bh), (255, 0, 0), 1)  # 1px
cv2.rectangle(mapped, (x, y), (x+hw, y+hh), (0, 255, 0), 1)      # 1px
```

**결과**: ✅ 문서가 훨씬 잘 보이고, 선이 방해하지 않음

---

### 문제 2: SVG 벡터가 너무 단순화됨

**증상**:
```
기본 설정 (--svg-simplify 1.0):
- 4,223 → 1,797 points (57% 감소)
- 형태가 둥글둥글하게 단순화됨
- 원본의 세밀한 형태 손실
```

**원인**:
```python
# contour_to_svg_path() 함수
simplified = cv2.approxPolyDP(contour, simplify_epsilon, True)
# epsilon=1.0이면 1픽셀 오차 허용 → 많은 점 제거됨
```

**해결**:
```bash
# 명령줄 옵션
--svg-simplify 0.1   # 0.1픽셀 오차만 허용 → 원본 거의 그대로
```

**비교 결과**:

| simplify | Points | 파일 크기 | 형태 정확도 |
|----------|--------|----------|------------|
| 1.0 (기본) | 1,797 (57% 감소) | 38KB | 단순화됨 |
| 3.0 (경량) | 913 (78% 감소) | 28KB | 매우 단순 |
| **0.1 (정밀)** | **4,223 (0% 감소)** | **63KB** | **원본 그대로** ⭐ |

**결과**: ✅ 원본 픽셀 윤곽선을 완벽히 보존

---

### 문제 3: 개별 SVG 파일이 사용 불편함

**증상**:
```xml
<!-- 변경 전: 전체 이미지 크기의 캔버스 -->
<svg width="611mm" height="458mm" viewBox="0 0 7216 5412">
  <!-- 작은 구멍이 큰 캔버스의 한쪽 구석에 작게 그려짐 -->
  <path d="M 1221,1028 L 1223,1030..."/>
</svg>

문제점:
- SVG 파일을 열면 구멍이 작게 보임
- 확대/축소해야 제대로 보임
- 편집 불편
```

**해결**:
```python
# create_individual_svg() 함수 수정 (Line 949-991)

# Bounding box 계산 (10% 여백 추가)
x, y, w, h = hole_info['bbox']
margin = max(10, int(max(w, h) * 0.1))

vb_x = max(0, x - margin)
vb_y = max(0, y - margin)
vb_w = min(img_w - vb_x, w + margin * 2)
vb_h = min(img_h - vb_y, h + margin * 2)

# viewBox를 구멍 주변만 포함하도록 설정
svg = ET.Element('svg', {
    'viewBox': f'{vb_x} {vb_y} {vb_w} {vb_h}'  # 구멍 중심!
})

# 메타데이터에 원본 위치 저장
ET.SubElement(metadata, 'original_position').text = f"x={x}, y={y}"
ET.SubElement(metadata, 'original_image_size').text = f"{img_w}x{img_h}"
ET.SubElement(metadata, 'bbox').text = f"x={x}, y={y}, w={w}, h={h}"
```

**변경 후**:
```xml
<!-- 구멍 중심 배치 -->
<svg width="9.48mm" height="6.18mm" viewBox="1211 1009 112 73">
  <metadata>
    <hole_id>10</hole_id>
    <original_position>x=1221, y=1019</original_position>
    <original_image_size>1443x1082</original_image_size>
    <bbox>x=1221, y=1019, w=92, h=63</bbox>
  </metadata>
  <!-- 구멍이 SVG 중앙에 크게 표시됨 -->
  <path d="M 1221,1028 L 1223,1030..."/>
</svg>
```

**결과**: ✅ 구멍이 SVG 중앙에 크게 표시, 확대/축소 용이, 원본 위치 정보는 메타데이터에 보존

---

### 문제 4: 구멍 추적이 어려움

**증상**:
- SVG에서 특정 구멍이 원본 이미지의 어디에 있는지 확인 어려움
- 구멍 ID와 위치를 매칭하기 어려움

**해결**: `verify_svg_alignment.py` 개선
```python
# 번호 표시 기능 추가

# 중심점 계산
M = cv2.moments(points)
cx = int(M["m10"] / M["m00"])
cy = int(M["m01"] / M["m00"])

# 배경 사각형 (가독성)
cv2.rectangle(numbered,
             (cx - text_w//2 - 2, cy - text_h//2 - 2),
             (cx + text_w//2 + 2, cy + text_h//2 + baseline),
             (255, 255, 255), -1)

# 번호 텍스트 (파란색)
cv2.putText(numbered, str(i + 1),
           (cx - text_w//2, cy + text_h//2),
           cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 0, 0), thickness)
```

**출력**:
```
4분할 이미지:
┌────────────┬────────────┐
│ 원본       │ SVG Overlay│
│            │ (빨간선)    │
├────────────┼────────────┤
│ SVG Only   │ Numbered   │
│ (검은채움)  │ (번호표시)  │
└────────────┴────────────┘
```

**결과**: ✅ 각 구멍에 1-N번 번호 표시, ID와 위치 매칭 용이

---

## 주요 변경사항

### 1. comparison.png 선 두께 (extract_whiteness_based.py)

**파일**: `extract_whiteness_based.py`
**위치**: Line 1026-1034

```python
def create_comparison(original, holes, output_path, boundary=None):
    # ...

    # 문서 경계 표시 (파란색 사각형)
    if boundary is not None:
        bx, by, bw, bh = boundary
        cv2.rectangle(mapped, (bx, by), (bx+bw, by+bh), (255, 0, 0), 1)  # 3→1

    # 구멍 표시 (녹색 사각형)
    for hole in holes:
        x, y, hw, hh = hole['bbox']
        cv2.rectangle(mapped, (x, y), (x+hw, y+hh), (0, 255, 0), 1)  # 2→1
```

---

### 2. SVG Simplification (명령줄 옵션)

**기본 사용법**:
```bash
# 원본 형태 그대로 보존 (권장)
python extract_whiteness_based.py \
  --input image.tif \
  --export-svg \
  --svg-simplify 0.1 \
  --svg-individual
```

**파라미터 비교**:
- `--svg-simplify 0.1`: 원본 그대로 (0% 감소)
- `--svg-simplify 1.0`: 균형 (50-70% 감소)
- `--svg-simplify 3.0`: 경량화 (80% 감소)

---

### 3. 개별 SVG 중앙 배치 (extract_whiteness_based.py)

**파일**: `extract_whiteness_based.py`
**위치**: Line 949-991

```python
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
```

**장점**:
- ✅ 구멍이 SVG 중앙에 크게 배치
- ✅ 확대/축소 용이
- ✅ 원본 위치 정보 보존 (메타데이터)
- ✅ Path 좌표는 원본 그대로 (정확도 유지)
- ✅ 10% 여백으로 여유 있게 표시

---

### 4. SVG 검증 도구 개선 (verify_svg_alignment.py)

**새 파일**: `verify_svg_alignment.py`

**주요 기능**:
1. 한글 경로 지원 (numpy를 통한 이미지 로드)
2. 번호 표시 기능
3. 4분할 비교 이미지 생성

```python
def verify_svg_alignment(image_path, svg_path, output_path):
    """SVG 경로를 원본 이미지에 오버레이하여 검증"""

    # 1. 한글 경로 지원
    with open(image_path, 'rb') as f:
        image_data = np.frombuffer(f.read(), np.uint8)
        image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

    # 2. 시각화 이미지 생성
    overlay = image.copy()        # 원본 + 빨간 윤곽선
    svg_only = 흰배경 + 검은채움    # SVG만
    numbered = image.copy()       # 원본 + 번호

    # 3. SVG 경로 그리기 + 번호 표시
    for i, points in enumerate(svg_paths):
        cv2.polylines(overlay, [points], True, (0, 0, 255), line_thickness)
        cv2.fillPoly(svg_only, [points], (0, 0, 0))
        cv2.polylines(numbered, [points], True, (0, 255, 0), 1)

        # 번호 표시
        cx, cy = 중심점_계산(points)
        cv2.rectangle(numbered, 배경사각형, (255, 255, 255), -1)
        cv2.putText(numbered, str(i+1), (cx, cy), 파란색)

    # 4. 4분할 결과 생성
    top = np.hstack([image, overlay])
    bottom = np.hstack([svg_only, numbered])
    result = np.vstack([top, bottom])
```

**사용법**:
```bash
python verify_svg_alignment.py \
  --image datasets/1첩/w_0001.tif \
  --svg results/w_0001_svg/all_holes_vector.svg \
  --output verification.png
```

**출력**:
- Top-left: 원본 이미지
- Top-right: SVG 빨간 윤곽선 오버레이
- Bottom-left: SVG만 (검은색 채움)
- Bottom-right: 번호 표시 (1-N)

---

## SVG 개별 파일 중앙 배치

### 변경 전 (전체 캔버스)

```xml
<svg width="611mm" height="458mm" viewBox="0 0 7216 5412">
  <path d="M 1221,1028 L 1223,1030..."/>
</svg>
```

**문제점**:
- 7216x5412 캔버스에 작은 구멍
- SVG를 열면 구멍이 작게 보임
- 확대해야 제대로 확인 가능

---

### 변경 후 (중앙 배치)

```xml
<svg width="9.48mm" height="6.18mm" viewBox="1211 1009 112 73">
  <metadata>
    <hole_id>10</hole_id>
    <original_position>x=1221, y=1019</original_position>
    <original_image_size>1443x1082</original_image_size>
    <bbox>x=1221, y=1019, w=92, h=63</bbox>
    <area_pixels>2473</area_pixels>
    <area_mm2>17.73</area_mm2>
  </metadata>
  <path d="M 1221,1028 L 1223,1030..."/>
</svg>
```

**개선점**:
- ✅ viewBox가 구멍 주변만 포함 (112x73)
- ✅ 구멍이 SVG 중앙에 크게 표시
- ✅ 10% 여백으로 여유 있음
- ✅ 원본 위치는 메타데이터에 보존
- ✅ Path 좌표는 원본 그대로

---

### 좌표 체계

```
원본 이미지: 7216x5412
┌─────────────────────────────────┐
│                                 │
│    구멍 위치: x=1221, y=1019    │
│    크기: w=92, h=63             │
│                                 │
└─────────────────────────────────┘

개별 SVG: viewBox="1211 1009 112 73"
┌─────────────┐
│  [10px여백] │
│  ┌────────┐ │
│  │ 구멍   │ │  ← 중앙에 크게!
│  └────────┘ │
│  [10px여백] │
└─────────────┘

Path 좌표는 원본 그대로!
M 1221,1028 L 1223,1030...
→ 원본 이미지 좌표계 사용
```

---

## 검증 도구 개선

### verify_svg_alignment.py 주요 기능

#### 1. 한글 경로 지원
```python
# OpenCV의 cv2.imread는 한글 경로 미지원
# → numpy를 통해 우회

with open(image_path, 'rb') as f:
    image_data = np.frombuffer(f.read(), np.uint8)
    image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
```

#### 2. 번호 표시
```python
# 각 구멍 중심에 번호 표시
for i, points in enumerate(svg_paths):
    # 중심점 계산
    M = cv2.moments(points)
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    # 배경 사각형 (가독성)
    cv2.rectangle(numbered,
                 (cx-w//2-2, cy-h//2-2),
                 (cx+w//2+2, cy+h//2+baseline),
                 (255, 255, 255), -1)

    # 번호 텍스트
    cv2.putText(numbered, str(i+1), (cx, cy),
               cv2.FONT_HERSHEY_SIMPLEX,
               font_scale, (255, 0, 0), thickness)
```

#### 3. 4분할 비교 이미지

```
┌──────────────┬──────────────┐
│   Original   │ SVG Overlay  │
│              │  (Red)       │
├──────────────┼──────────────┤
│  SVG Only    │  Numbered    │
│  (Black)     │  (IDs)       │
└──────────────┴──────────────┘
```

**사용 예시**:
```bash
python verify_svg_alignment.py \
  --image "datasets/1첩/w_0005.tif" \
  --svg results/w_0005_svg/all_holes_vector.svg \
  --output verification_w_0005.png
```

---

## 처리 결과

### test_small.jpg (저해상도)

**설정**:
```bash
python extract_whiteness_based.py \
  --input datasets/test_small.jpg \
  --method lab_b \
  --s-threshold 138 \
  --min-area 50 \
  --crop-document \
  --corner-method edges \
  --export-svg \
  --svg-simplify 0.1 \
  --svg-individual \
  --output-dir results/test_small_svg_centered
```

**결과**:
- 구멍 개수: 268개
- SVG 포인트: 4,223 (0% 감소)
- 통합 SVG: 63KB
- 개별 SVG: 268개 파일
- 선 두께: 1px (얇음)

---

### w_0001.tif (고해상도)

**타일 경계**:
- Left: 실제 가장자리 (961px)
- Right: 이어짐 → 7215px
- Top: 실제 가장자리 (237px)
- Bottom: 이어짐 → 5411px

**결과**:
- 구멍 개수: 297개
- SVG 포인트: 30,212 (0% 감소)
- 통합 SVG: ~400KB
- 개별 SVG: 297개 파일
- 면적 범위: 52 - 1,028,962 pixels

**대표 구멍 (ID 156)**:
```xml
<svg width="118.62mm" height="267.97mm" viewBox="674 2247 1401 3165">
  <metadata>
    <hole_id>156</hole_id>
    <original_position>x=961, y=2534</original_position>
    <bbox>x=961, y=2534, w=827, h=2878</bbox>
    <area_pixels>1028962</area_pixels>
    <area_mm2>7376.06</area_mm2>
  </metadata>
  <!-- 매우 큰 손상 영역도 중앙 배치됨 -->
</svg>
```

---

### w_0002.tif

**타일 경계**:
- Left: 실제 가장자리 (839px)
- 나머지: 이어짐

**결과**:
- 구멍 개수: 260개
- SVG 포인트: 30,568 (0% 감소)
- 평균 면적: 10,465 pixels

---

### w_0003.tif

**타일 경계**:
- Left: 실제 가장자리 (795px)
- 나머지: 이어짐

**결과**:
- 구멍 개수: 188개
- SVG 포인트: 21,534 (0% 감소)
- 평균 면적: 9,289 pixels

---

### w_0005.tif

**타일 경계**:
- Left: 실제 가장자리 (762px)
- 나머지: 이어짐

**결과**:
- 구멍 개수: 163개
- SVG 포인트: 21,858 (0% 감소)
- 평균 면적: 12,619 pixels

---

## 최종 권장 설정

### 일반 사용 (정밀도 우선)

```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/w_0001.tif" \
  --method lab_b \
  --s-threshold 138 \
  --min-area 50 \
  --max-area 2500000 \
  --crop-document \
  --corner-method edges \
  --export-svg \
  --svg-simplify 0.1 \
  --svg-individual \
  --output-dir results/output
```

**특징**:
- ✅ 원본 형태 완벽 보존 (simplify=0.1)
- ✅ 개별 SVG 중앙 배치
- ✅ 타일 경계 자동 감지
- ✅ 얇은 선 (1px)

---

### 경량화 (파일 크기 우선)

```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/w_0001.tif" \
  --method lab_b \
  --s-threshold 138 \
  --min-area 50 \
  --max-area 2500000 \
  --crop-document \
  --corner-method edges \
  --export-svg \
  --svg-simplify 3.0 \
  --svg-unified \
  --output-dir results/output
```

**특징**:
- ✅ 파일 크기 최소화 (simplify=3.0)
- ✅ 통합 SVG만 생성
- ⚠️ 형태 정확도 감소

---

### SVG 검증

```bash
python verify_svg_alignment.py \
  --image "datasets/1첩/w_0001.tif" \
  --svg results/w_0001_svg/all_holes_vector.svg \
  --output verification_w_0001.png
```

**출력**:
- 4분할 비교 이미지
- 번호 표시 (1-N)
- 픽셀 단위 정확도 확인

---

## 파라미터 비교표

### SVG Simplification

| 파라미터 | Points | 파일 크기 | 형태 | 용도 |
|----------|--------|----------|------|------|
| `0.1` | 100% (0% 감소) | 큼 | 원본 그대로 | **레이저 커팅, 정밀 작업** ⭐ |
| `0.5` | ~80% | 중간 | 매우 정확 | 고품질 보존 |
| `1.0` | ~50% | 작음 | 정확 | 일반 사용 |
| `3.0` | ~20% | 매우 작음 | 단순화 | 파일 크기 중요 |
| `5.0` | ~10% | 극소 | 매우 단순 | 개략적 형태만 |

---

### 선 두께

| 위치 | 이전 | 현재 | 개선 |
|------|------|------|------|
| 문서 경계 (파란색) | 3px | **1px** | ✅ 가시성 향상 |
| 구멍 박스 (녹색) | 2px | **1px** | ✅ 가시성 향상 |
| 텍스트 두께 | 2px | **자동** | ✅ 해상도 적응 |

---

## 파일 구조

### 출력 디렉토리 구조

```
results/w_0001_svg_centered/
├── all_holes_vector.svg              # 통합 SVG (모든 구멍)
├── comparison.png                    # 원본 vs 검출 결과 (얇은 선)
├── document_boundary.png             # 경계 시각화 (얇은 선)
├── white_mask.png                    # 구멍 마스크
├── white_mask_raw.png                # 구멍 마스크 (경계 전)
├── individual_holes/                 # 개별 구멍 PNG
│   ├── hole_0001_x961_y2534_a1028962.png
│   └── ...
└── svg_vectors/                      # 개별 SVG (중앙 배치)
    ├── hole_0000_x2120_y5395_a287.svg
    ├── hole_0001_x1183_y5385_a1308.svg
    └── ... (297개)
```

---

### 개별 SVG 파일명 형식

```
hole_0156_x961_y2534_a1028962.svg
  │      │    │     └─ 면적 (1,028,962 픽셀)
  │      │    └──────── y좌표 (2534)
  │      └───────────── x좌표 (961)
  └──────────────────── 구멍 ID (156번)
```

---

### SVG 파일 내부 구조

```xml
<?xml version="1.0" ?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="118.62mm" height="267.97mm"
     viewBox="674 2247 1401 3165">

  <!-- 메타데이터: 원본 위치 정보 -->
  <metadata>
    <hole_id>156</hole_id>
    <original_position>x=961, y=2534</original_position>
    <original_image_size>7216x5412</original_image_size>
    <bbox>x=961, y=2534, w=827, h=2878</bbox>
    <area_pixels>1028962</area_pixels>
    <area_mm2>7376.06</area_mm2>
  </metadata>

  <!-- Path: 원본 좌표 그대로 -->
  <path id="hole_156"
        d="M 1501,2534 L 1500,2535 L 1493,2535..."
        fill="none"
        stroke="black"
        stroke-width="1"
        vector-effect="non-scaling-stroke"/>
</svg>
```

**주요 속성**:
- `viewBox`: 구멍 주변만 포함 (중앙 배치)
- `width/height`: 물리적 크기 (mm)
- `metadata`: 원본 위치, 크기, 면적 정보
- `path d`: 원본 픽셀 좌표 (정확도 보존)
- `vector-effect`: 선 두께 고정 (확대해도 1px 유지)

---

## 기술적 세부사항

### 1. viewBox 계산 로직

```python
# Bounding box 계산
x, y, w, h = hole_info['bbox']

# 10% 여백 또는 최소 10px
margin = max(10, int(max(w, h) * 0.1))

# viewBox 좌표 (이미지 경계 체크)
vb_x = max(0, x - margin)
vb_y = max(0, y - margin)
vb_w = min(img_w - vb_x, w + margin * 2)
vb_h = min(img_h - vb_y, h + margin * 2)

# viewBox 문자열
viewBox = f"{vb_x} {vb_y} {vb_w} {vb_h}"
```

**예시**:
```
구멍 bbox: x=1221, y=1019, w=92, h=63
최대값: max(92, 63) = 92
margin: max(10, 92 * 0.1) = max(10, 9.2) = 10

viewBox:
  x: max(0, 1221 - 10) = 1211
  y: max(0, 1019 - 10) = 1009
  w: min(1443 - 1211, 92 + 20) = min(232, 112) = 112
  h: min(1082 - 1009, 63 + 20) = min(73, 83) = 73

결과: viewBox="1211 1009 112 73"
```

---

### 2. 물리적 크기 계산

```python
# DPI 기준 물리적 크기 계산
dpi = 300
inch_to_mm = 25.4

# 픽셀 → 인치 → mm
physical_w = (vb_w / dpi) * inch_to_mm
physical_h = (vb_h / dpi) * inch_to_mm

# 예시:
# vb_w = 112 pixels
# (112 / 300) * 25.4 = 0.373 * 25.4 = 9.48 mm
```

---

### 3. SVG Path 좌표

**중요**: Path 좌표는 원본 이미지 좌표계를 그대로 사용!

```xml
<!-- viewBox는 1211,1009를 기준으로 하지만 -->
<svg viewBox="1211 1009 112 73">

  <!-- Path는 원본 좌표 그대로 -->
  <path d="M 1221,1028 L 1223,1030..."/>
        ↑         ↑
        원본 이미지 좌표계 (0,0 ~ 7216,5412)
</svg>
```

**이유**:
- 원본 위치 정보 보존
- 레이저 커팅 시 정확한 위치 사용 가능
- viewBox가 자동으로 확대/축소 처리

---

### 4. 한글 경로 처리

```python
# OpenCV는 한글 경로 미지원
# cv2.imread("datasets/1첩/w_0001.tif")  # ❌ 실패

# 해결: numpy 우회
with open(image_path, 'rb') as f:
    image_data = np.frombuffer(f.read(), np.uint8)
    image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)  # ✅ 성공
```

---

## 활용 시나리오

### 1. 레이저 커팅

```
1. 개별 SVG 열기 (중앙 배치로 쉽게 확인)
2. 메타데이터 확인 (원본 위치, 크기)
3. Path 좌표로 정확한 위치에 절단
4. 물리적 크기(mm) 정보로 스케일 조정
```

---

### 2. 벡터 편집

```
1. Adobe Illustrator / Inkscape에서 SVG 열기
2. 구멍이 중앙에 크게 표시됨 (편집 용이)
3. 형태 수정 가능 (원본 정밀도 보존)
4. 메타데이터로 원본 위치 파악
```

---

### 3. 문서화 / 보고서

```
1. 통합 SVG로 전체 손상 현황 파악
2. 개별 SVG로 특정 구멍 상세 분석
3. 번호 표시 이미지로 구멍 추적
4. 벡터이므로 확대해도 깨지지 않음
```

---

### 4. 3D 모델링

```
1. SVG → 3D 소프트웨어로 import
2. Path를 Extrude하여 3D 형상 생성
3. 물리적 크기 정보로 정확한 스케일
4. 3D 프린팅으로 실물 복원
```

---

### 5. 구멍 추적 및 분석

```
1. verification 이미지로 구멍 번호 확인
2. 개별 SVG 파일명에서 위치/면적 파악
3. 메타데이터에서 상세 정보 추출
4. 통계 분석 (면적 분포, 위치 패턴 등)
```

---

## 성능 비교

### 파일 크기

| 이미지 | simplify=1.0 | simplify=0.1 | 증가율 |
|--------|-------------|-------------|--------|
| test_small | 38 KB | 63 KB | +66% |
| w_0005 | 97 KB | 263 KB | +171% |

**결론**: 정밀도를 위해 파일 크기 2-3배 증가는 허용 가능

---

### 처리 시간

| 이미지 | 크기 | 구멍 개수 | 처리 시간 |
|--------|------|----------|----------|
| test_small.jpg | 1443x1082 | 268 | ~5초 |
| w_0001.tif | 7216x5412 | 297 | ~20초 |
| w_0005.tif | 7216x5412 | 163 | ~15초 |

**참고**: 시간은 대부분 이미지 로드와 형태 분석에 소요

---

## 문제 해결

### 문제: OpenCV 한글 경로 오류

**증상**:
```python
cv2.imread("datasets/1첩/w_0001.tif")
# Error: can't open/read file
```

**해결**:
```python
# verify_svg_alignment.py에 구현됨
with open(image_path, 'rb') as f:
    image_data = np.frombuffer(f.read(), np.uint8)
    image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
```

---

### 문제: SVG 파일이 너무 큼

**증상**:
```
simplify=0.1로 설정 시:
- w_0001: 400KB+
- 개별 파일 수백개
```

**해결 옵션**:
1. `--svg-simplify 1.0` 사용 (파일 크기 절반)
2. `--svg-unified`만 사용 (개별 파일 생성 안함)
3. 필요한 구멍만 선택적 추출

---

### 문제: 작은 구멍이 SVG에서 안보임

**증상**:
- viewBox가 전체 이미지 크기
- 작은 구멍이 점으로만 보임

**해결**: ✅ 이미 해결됨
- viewBox를 구멍 bbox 기준으로 설정
- 자동으로 중앙 배치 및 확대

---

## 향후 개선 가능 사항

### 1. 배치 처리 스크립트
```bash
# 폴더 내 모든 이미지 자동 처리
for file in datasets/1첩/*.tif; do
    python extract_whiteness_based.py --input "$file" ...
done
```

### 2. SVG 메타데이터 확장
- 손상 유형 (찢김, 구멍, 얼룩 등)
- 감지 신뢰도
- 처리 일시
- 파라미터 정보

### 3. 웹 뷰어
- 웹 브라우저에서 SVG 인터랙티브 표시
- 구멍 클릭 → 상세 정보 표시
- 필터링 (크기, 위치 등)

### 4. 통계 대시보드
- 전체 손상 현황 시각화
- 구멍 크기 분포 히스토그램
- 위치 히트맵

---

## 관련 파일

### 수정된 파일
- `extract_whiteness_based.py`: 주요 처리 스크립트
  - Line 949-991: 개별 SVG 중앙 배치
  - Line 1026-1034: 선 두께 1px

### 새 파일
- `verify_svg_alignment.py`: SVG 검증 도구
  - 한글 경로 지원
  - 번호 표시 기능
  - 4분할 비교 이미지

---

## 요약

### 주요 개선사항
1. ✅ **시각화 선 얇게** (3px/2px → 1px)
2. ✅ **SVG 원본 형태 보존** (simplify=0.1, 0% 감소)
3. ✅ **개별 SVG 중앙 배치** (viewBox 최적화)
4. ✅ **구멍 번호 추적** (검증 이미지에 ID 표시)
5. ✅ **한글 경로 지원** (numpy 우회)

### 최종 권장 명령어
```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/w_0001.tif" \
  --method lab_b \
  --s-threshold 138 \
  --min-area 50 \
  --max-area 2500000 \
  --crop-document \
  --corner-method edges \
  --export-svg \
  --svg-simplify 0.1 \
  --svg-individual \
  --output-dir results/output
```

### 처리 결과
- ✅ 타일 경계 자동 감지
- ✅ 얇은 선으로 가시성 향상
- ✅ 원본 형태 완벽 보존
- ✅ 개별 SVG 사용 편의성 극대화
- ✅ 위치 추적 용이

---

**작성자**: Claude Code
**날짜**: 2025-10-30
**프로젝트**: 고문서 손상 자동 검출 시스템
