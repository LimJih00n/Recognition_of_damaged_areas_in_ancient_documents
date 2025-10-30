# 해상도 자동 스케일링 & SVG 벡터 출력 구현

**작성일**: 2025-10-30
**목적**: 레이저 커팅을 위한 벡터 출력 및 해상도 독립적 처리

---

## 📋 목차

1. [작업 개요](#작업-개요)
2. [문제 인식](#문제-인식)
3. [해상도 자동 스케일링 구현](#해상도-자동-스케일링-구현)
4. [SVG 벡터 출력 구현](#svg-벡터-출력-구현)
5. [파라미터 최적화](#파라미터-최적화)
6. [테스트 결과](#테스트-결과)
7. [최종 권장 사항](#최종-권장-사항)

---

## 작업 개요

### 목표
- **레이저 커팅/프린팅**을 위한 벡터(SVG) 형식 출력
- 해상도에 따른 일관된 처리를 위한 자동 스케일링
- 형태의 정확한 캡처 (해상도보다 형태가 중요)

### 구현 항목
1. ✅ 고해상도 기준 자동 스케일링 시스템
2. ✅ SVG 벡터 출력 기능
3. ✅ 물리적 크기(mm) 메타데이터 포함
4. ✅ 레이저 커팅 최적화된 path 단순화

---

## 문제 인식

### 해상도 의존성 문제

#### 발견
```
test_small (1443x1082):  254개 구멍, min-area=70 → 72개만 검출
w_0001 (7216x5412):      335개 구멍, min-area=70 → 291개 검출
```

**같은 min-area=70 픽셀이지만:**
- test_small: 실제 약 8x8mm 구멍
- w_0001: 실제 약 1.5x1.5mm 구멍 (5배 더 작음!)

#### 해상도가 영향을 미치는 부분들

1. **min-area / max-area 필터** ⚠️⚠️⚠️
   - 같은 픽셀 값이 다른 물리적 크기를 의미

2. **Morphology 커널** ⚠️⚠️
   - 3x3 커널이 해상도에 따라 다른 효과
   - 저해상도: 노이즈 제거 효과 강함
   - 고해상도: 노이즈 제거 효과 약함

3. **border-margin** ⚠️
   - 같은 픽셀 값이 다른 영역을 제외

4. **b-channel threshold** ✅
   - 색상 값이라서 해상도 무관 (문제 없음)

---

## 해상도 자동 스케일링 구현

### 기준 해상도 설정

```python
# 고해상도 .tif 이미지를 기준으로 설정
REFERENCE_PIXELS = 7216 * 5412  # 39,052,992 pixels
```

**선택 이유:**
- 실제 작업 대상이 고해상도 .tif 파일
- test_small은 테스트용 저해상도 샘플

### 스케일링 공식

```python
# 현재 이미지 크기
current_pixels = height * width

# 스케일 팩터 계산
scale_factor = current_pixels / REFERENCE_PIXELS

# 면적 기준 스케일링 (min-area, max-area)
min_area_scaled = int(min_area * scale_factor)
max_area_scaled = int(max_area * scale_factor)

# 선형 기준 스케일링 (커널, border)
linear_scale = sqrt(scale_factor)
kernel_size = max(3, int(3 * linear_scale))
border_margin_scaled = int(border_margin * linear_scale)
```

### 구현 위치

**파일**: `extract_whiteness_based.py`
**함수**: `extract_individual_holes()`
**라인**: 216-247

```python
def extract_individual_holes(image, mask, min_area=50, max_area=500000, ...):
    """개별 구멍 추출 (자동 해상도 스케일링 적용)

    Note:
        입력된 min_area, max_area는 고해상도(7216x5412, 39M pixels) 기준값입니다.
        실제 이미지 해상도에 따라 자동으로 스케일링됩니다.
    """
    h, w = image.shape[:2]
    current_pixels = h * w
    REFERENCE_PIXELS = 7216 * 5412

    scale_factor = current_pixels / REFERENCE_PIXELS

    # 파라미터 스케일링
    min_area_scaled = int(min_area * scale_factor)
    max_area_scaled = int(max_area * scale_factor)

    linear_scale = np.sqrt(scale_factor)
    kernel_size = max(3, int(3 * linear_scale))
    # ...
```

### 출력 정보

```
=== Auto-Scaling (Resolution-Aware) ===
  Current resolution: 1443x1082 (1,561,326 pixels)
  Reference resolution: 7216x5412 (39,052,992 pixels)
  Scale factor: 0.0400 (0.20x linear)
  min-area: 70 → 2 pixels
  max-area: 500,000 → 19,989 pixels
  kernel size: 3x3 → 3x3
```

---

## SVG 벡터 출력 구현

### 레이저 커팅 요구사항

1. **해상도 독립적**: 픽셀이 아닌 벡터로 저장
2. **크기 조절 가능**: 무한 확대/축소
3. **정확한 형태**: 구멍의 형태를 정밀하게 캡처
4. **물리적 크기**: mm 단위 크기 정보 필요

### 구현된 기능

#### 1. Contour to SVG Path 변환

```python
def contour_to_svg_path(contour, simplify_epsilon=1.0):
    """OpenCV contour를 SVG path로 변환

    Args:
        contour: OpenCV contour
        simplify_epsilon: 윤곽선 단순화 정도

    Returns:
        SVG path string (예: "M 10,20 L 30,40 Z")
    """
    # 윤곽선 단순화 (레이저 커팅 최적화)
    simplified = cv2.approxPolyDP(contour, simplify_epsilon, True)

    path_data = []
    start = simplified[0][0]
    path_data.append(f'M {start[0]},{start[1]}')

    for point in simplified[1:]:
        x, y = point[0]
        path_data.append(f'L {x},{y}')

    path_data.append('Z')  # 경로 닫기
    return ' '.join(path_data)
```

#### 2. 물리적 크기 계산

```python
# DPI 기반 물리적 크기 (mm 단위)
mm_per_inch = 25.4
width_mm = (image_width / dpi) * mm_per_inch
height_mm = (image_height / dpi) * mm_per_inch

# 구멍 면적 (mm²)
area_mm2 = area_px / (dpi / mm_per_inch) ** 2
```

#### 3. 통합 SVG 파일

**파일명**: `all_holes_vector.svg`

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     width="611.0mm" height="458.2mm"
     viewBox="0 0 7216 5412">
  <metadata>
    <total_holes>153</total_holes>
    <document_size_mm>611.0x458.2</document_size_mm>
  </metadata>
  <g id="all_holes" fill="none" stroke="black" stroke-width="1">
    <path id="hole_0000" d="M 3526,5330 L 3520,5335 ..."
          data-area-px="780" data-area-mm2="5.59"/>
    ...
  </g>
</svg>
```

**특징**:
- `fill='none'` + `stroke='black'` = 레이저가 선을 따라 커팅
- `width/height` in mm = 물리적 크기
- `data-area-mm2` = 각 구멍의 실제 면적

#### 4. 개별 SVG 파일

**파일명**: `hole_0023_x4700_y4442_a465373.svg`

```xml
<svg width="611.0mm" height="458.2mm" viewBox="0 0 7216 5412">
  <metadata>
    <hole_id>23</hole_id>
    <area_pixels>465373</area_pixels>
    <area_mm2>3339.00</area_mm2>
  </metadata>
  <path d="M 4700,4442 L ..."
        fill="none" stroke="black"
        vector-effect="non-scaling-stroke"/>
</svg>
```

### Path Simplification

**목적**: 레이저 커팅 속도 향상, 파일 크기 감소

```python
simplified = cv2.approxPolyDP(contour, epsilon, True)
```

**효과**:
- w_0001: 25,355 → 8,286 points (67.3% 감소)
- w_0005: 16,226 → 5,441 points (66.5% 감소)
- w_0007: 17,967 → 6,243 points (65.3% 감소)

**파라미터**:
- `--svg-simplify 0.5`: 매우 정밀 (포인트 많음)
- `--svg-simplify 1.0`: 균형 (기본값, 권장)
- `--svg-simplify 2.0`: 단순함 (포인트 적음, 빠름)

### 구현 위치

**파일**: `extract_whiteness_based.py`
**함수**:
- `contour_to_svg_path()` (라인 324-359)
- `save_holes_svg()` (라인 362-435)
- `create_individual_svg()` (라인 438-467)
- `create_unified_svg()` (라인 470-504)

---

## 파라미터 최적화

### min-area 테스트 (10 vs 50 vs 70)

#### 테스트 목적
고해상도 기준으로 적절한 min-area 값 찾기

#### 결과

| 이미지 | min=10 | min=50 | min=70 | 권장 |
|--------|--------|--------|--------|------|
| test_small | 254개 | 129개 | 72개 | 10-50 |
| w_0001 | 335개 | 296개 | 291개 | 70 ✅ |
| w_0003 | 267개 | 185개 | 176개 | 70 ✅ |
| w_0005 | 239개 | 159개 | 151개 | 70 ✅ |
| w_0007 | 367개 | 191개 | 174개 | 70 ✅ |
| w_0010 | 348개 | 188개 | 169개 | 70 ✅ |
| w_0015 | 163개 | 116개 | 113개 | 70 ✅ |

**결론**: **min-area=70** 권장 (고해상도 기준)
- 작은 노이즈 효과적 제거
- 의미 있는 구멍은 모두 포함
- 자동 스케일링으로 저해상도에서도 잘 작동

### max-area 증가 (100k → 200k → 500k)

#### 문제 발견

**초기 설정**: max-area=100,000
```
w_0001 최대 구멍: 71,158 px ⚠️ (100k 이하지만 근접)
w_0010 최대 구멍: 73,984 px ⚠️
```

**1차 증가**: max-area=200,000
```
w_0003 최대 구멍: 120,354 px ✅
w_0007 최대 구멍: 175,104 px ✅
```

**2차 증가 (최종)**: max-area=500,000
```
w_0005 최대 구멍: 465,374 px 🔥 발견!
```

#### 최종 설정

```python
parser.add_argument('--max-area', type=int, default=500000,
                   help='Maximum hole area in pixels (7216x5412 reference)')
```

**이유**:
- w_0005에서 465k 픽셀 거대 구멍 발견
- 500k는 전체 문서의 약 1.3% 크기
- 충분한 여유 확보 (465k / 500k = 93%)

---

## 테스트 결과

### 최종 파라미터

```bash
python extract_whiteness_based.py \
  --input IMAGE \
  --output-dir OUTPUT \
  --method lab_b \
  --s-threshold 138 \
  --min-area 70 \
  --max-area 500000 \
  --export-svg \
  --svg-simplify 1.0 \
  --svg-individual
```

### 전체 이미지 테스트 결과

#### test_small.jpg (저해상도)

```
크기: 1443x1082 (1.56M pixels)
물리적 크기: 122.2x91.6 mm

Auto-Scaling:
  Scale factor: 0.0400 (0.20x linear)
  min-area: 70 → 2 pixels
  max-area: 500,000 → 19,989 pixels
  kernel: 3x3 → 3x3

결과:
  검출된 구멍: 268개
  SVG 출력: 262개 (97.8%)
  최대 구멍: 2,477 px (0.16%)
  평균 크기: 89 px
  총 손상: 1.53%

Path simplification: 57.4% (4,221 → 1,798)
```

#### w_0001.tif (고해상도, 큰 구멍)

```
크기: 7216x5412 (39.05M pixels)
물리적 크기: 611.0x458.2 mm

Auto-Scaling:
  Scale factor: 1.0000 (1.00x linear)
  min-area: 70 → 70 pixels (기준)
  max-area: 500,000 → 500,000 pixels
  kernel: 3x3 → 3x3

결과:
  검출된 구멍: 291개
  SVG 출력: 291개 (100%) ✅
  최대 구멍: 71,158 px (14.2%)
  평균 크기: 2,586 px
  총 손상: 1.93%

Path simplification: 67.3% (25,355 → 8,286)
```

#### w_0005.tif (거대 구멍 발견!)

```
크기: 7216x5412 (39.05M pixels)
물리적 크기: 611.0x458.2 mm
배경: 변색됨 (b=144.1)

Auto-Scaling:
  Scale factor: 1.0000
  min-area: 70 → 70 pixels
  max-area: 500,000 → 500,000 pixels
  kernel: 3x3 → 3x3

결과:
  검출된 구멍: 153개
  SVG 출력: 153개 (100%) ✅
  최대 구멍: 465,374 px (93.1%) 🔥🔥🔥
  평균 크기: 5,990 px
  총 손상: 2.35%

Path simplification: 66.5% (16,226 → 5,441)

TOP 큰 구멍:
  1. hole_0023: 465,373 px (≈ 58x58mm)
  2. hole_0136: 201,306 px (≈ 38x38mm)
  3. hole_0109: 17,676 px
  4. hole_0007: 13,250 px
  5. hole_0056: 10,409 px
```

#### w_0007.tif (많은 구멍)

```
크기: 7216x5412 (39.05M pixels)
물리적 크기: 611.0x458.2 mm

Auto-Scaling:
  Scale factor: 1.0000
  min-area: 70 → 70 pixels
  max-area: 500,000 → 500,000 pixels
  kernel: 3x3 → 3x3

결과:
  검출된 구멍: 174개
  SVG 출력: 174개 (100%) ✅
  최대 구멍: 175,104 px (35.0%)
  평균 크기: 3,447 px
  총 손상: 1.54%
  제외된 노이즈: 679개

Path simplification: 65.3% (17,967 → 6,243)
```

### 비교 요약표

| 이미지 | 해상도 | 구멍 수 | 최대 구멍 | max 대비 | SVG 출력 | 평균 크기 |
|--------|--------|---------|----------|----------|----------|----------|
| test_small | 1.56M | 268 | 2,477 px | 0.5% | 262 (97.8%) | 89 px |
| w_0001 | 39.05M | 291 | 71,158 px | 14.2% | 291 (100%) | 2,586 px |
| **w_0005** | 39.05M | **153** | **465,374 px** | **93.1%** | 153 (100%) | **5,990 px** |
| w_0007 | 39.05M | 174 | 175,104 px | 35.0% | 174 (100%) | 3,447 px |

---

## 주요 발견

### 1. w_0005의 거대 구멍

**최대 구멍 크기 비교**:
```
w_0005: 465,374 px  🥇 (1위)
w_0007: 175,104 px  🥈 (2위, 2.7배 차이)
w_0001:  71,158 px  🥉 (3위, 6.5배 차이)
```

**물리적 크기**:
- 465,374 px ÷ (300 DPI / 25.4)² ≈ 3,339 mm²
- 약 58mm x 58mm (거의 6cm x 6cm!)

**의미**:
- 문서의 심각한 손상 부위
- max-area=500k가 꼭 필요했음
- 이전 200k 설정이었다면 놓쳤을 것

### 2. 해상도 스케일링 효과

**test_small 자동 조정**:
```
min-area: 70 → 2 pixels (35배 감소)
max-area: 500,000 → 19,989 pixels (25배 감소)
```

**효과**:
- 268개 구멍 검출 (이전 72개에서 3.7배 증가)
- 고해상도와 동일한 기준 적용
- 작은 구멍도 놓치지 않음

### 3. SVG Path Simplification

**평균 65-67% 포인트 감소**:
- 레이저 커팅 속도 2-3배 향상 예상
- 파일 크기 65% 감소
- 형태는 거의 동일 유지

### 4. 필터 효과

**Size Filter**:
- w_0007: 853개 → 174개 (79.6% 제외)
- 대부분 min-area=70 미만 작은 노이즈

**SVG Simplification Filter**:
- 3포인트 미만 구멍 자동 제외
- test_small: 268 → 262 (6개 제외, 97.8%)
- 매우 작은 점들은 레이저 커팅 불가

---

## 파일 구조

### 출력 디렉토리

```
results/w_0005_max500k/
├── all_holes_vector.svg          # ⭐ 통합 SVG (레이저 커팅용)
├── comparison.png                 # 시각적 비교
├── white_mask.png                # 이진 마스크
├── individual_holes/              # PNG 153개
│   ├── hole_0000_x3517_y5330_a780.png
│   └── ...
└── svg_vectors/                   # ⭐⭐ 개별 SVG 153개
    ├── hole_0023_x4700_y4442_a465373.svg  # 거대 구멍!
    ├── hole_0136_x6056_y1163_a201306.svg
    └── ...
```

### 코드 변경사항

**파일**: `extract_whiteness_based.py`

**주요 변경**:
1. `extract_individual_holes()` (라인 205-315)
   - 자동 스케일링 로직 추가
   - contour를 hole 딕셔너리에 저장

2. `contour_to_svg_path()` (라인 324-359)
   - SVG path 변환 함수 추가

3. `save_holes_svg()` (라인 362-435)
   - SVG 벡터 출력 메인 함수

4. `create_individual_svg()` (라인 438-467)
   - 개별 구멍 SVG 생성

5. `create_unified_svg()` (라인 470-504)
   - 통합 SVG 생성

6. 새로운 커맨드라인 옵션:
   - `--export-svg`: SVG 출력 활성화
   - `--svg-dpi 300`: DPI 설정 (물리적 크기 계산용)
   - `--svg-simplify 1.0`: Path 단순화 정도
   - `--svg-individual`: 개별 SVG 파일 생성
   - `--svg-unified`: 통합 SVG 파일 생성 (기본값 True)

7. 기본값 변경:
   - `max-area`: 100,000 → 500,000 (5배 증가)

---

## 최종 권장 사항

### 일반 사용 (권장)

```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/IMAGE.tif" \
  --output-dir "results/IMAGE_vector" \
  --method lab_b \
  --s-threshold 138 \
  --min-area 70 \
  --export-svg \
  --svg-simplify 1.0
```

**파라미터 설명**:
- `--method lab_b`: LAB b-channel 사용 (최적)
- `--s-threshold 138`: 고정 threshold (일관성)
- `--min-area 70`: 고해상도 기준 최소 크기
- `--max-area 500000`: 기본값 (충분함)
- `--export-svg`: SVG 벡터 출력
- `--svg-simplify 1.0`: 균형잡힌 단순화

### 개별 SVG 파일도 필요한 경우

```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/IMAGE.tif" \
  --output-dir "results/IMAGE_vector" \
  --method lab_b \
  --s-threshold 138 \
  --min-area 70 \
  --export-svg \
  --svg-individual \
  --svg-simplify 1.0
```

### 매우 정밀한 형태 필요 시

```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/IMAGE.tif" \
  --output-dir "results/IMAGE_vector" \
  --method lab_b \
  --s-threshold 138 \
  --min-area 70 \
  --export-svg \
  --svg-simplify 0.5  # 더 정밀
```

### 심각한 손상 문서 (b평균 < 140)

```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/w_0010.tif" \
  --output-dir "results/w_0010_vector" \
  --method lab_b \
  --s-threshold 135 \  # 더 엄격하게
  --min-area 70 \
  --export-svg
```

### 배치 처리

**PowerShell**:
```powershell
Get-ChildItem "datasets\1첩\*.tif" | ForEach-Object {
    $name = $_.BaseName
    python extract_whiteness_based.py `
      --input $_.FullName `
      --output-dir "results\${name}_vector" `
      --method lab_b `
      --s-threshold 138 `
      --min-area 70 `
      --export-svg `
      --svg-individual
}
```

**Bash**:
```bash
for img in datasets/1첩/*.tif; do
    name=$(basename "$img" .tif)
    python extract_whiteness_based.py \
      --input "$img" \
      --output-dir "results/${name}_vector" \
      --method lab_b \
      --s-threshold 138 \
      --min-area 70 \
      --export-svg \
      --svg-individual
done
```

---

## 레이저 커팅 워크플로우

### 1. SVG 생성
```bash
python extract_whiteness_based.py \
  --input document.tif \
  --output-dir results/laser_cut \
  --method lab_b --s-threshold 138 --min-area 70 \
  --export-svg --svg-simplify 1.5
```

### 2. SVG 확인 및 편집
- `all_holes_vector.svg`를 Illustrator/Inkscape로 열기
- 필요시 구멍 선택, 삭제, 이동
- 레이어별 정리

### 3. 레이저 커터로 전송
- 대부분의 레이저 커터는 SVG 직접 지원
- 검은 선(`stroke='black'`)을 따라 커팅
- 물리적 크기(mm)로 정확히 출력

### 4. 재료 선택
- 종이: 복원용 한지
- 플라스틱: 투명 필름
- 기타: 레이저 커터 호환 재료

---

## 기술적 세부사항

### 자동 스케일링 계산

**면적 기준** (min-area, max-area):
```
scale_factor = (current_width * current_height) / (7216 * 5412)
scaled_value = original_value * scale_factor
```

**선형 기준** (커널, border):
```
linear_scale = sqrt(scale_factor)
scaled_value = original_value * linear_scale
```

### SVG 좌표계

**viewBox**: 픽셀 좌표계 유지
```xml
viewBox="0 0 7216 5412"
```

**width/height**: 물리적 크기 (mm)
```xml
width="611.0mm" height="458.2mm"
```

**효과**:
- 픽셀 좌표는 그대로 사용
- 출력 시 자동으로 물리적 크기로 변환
- 확대/축소 시 형태 유지

### Path Data 형식

```
M x,y    : MoveTo (시작점)
L x,y    : LineTo (선 그리기)
Z        : ClosePath (경로 닫기)
```

**예시**:
```
M 3526,5330 L 3520,5335 L 3517,5349 L 3525,5359 Z
```

---

## 검증 및 품질 관리

### SVG 출력 성공률

| 이미지 | 검출 | SVG 출력 | 성공률 |
|--------|------|----------|--------|
| test_small | 268 | 262 | 97.8% |
| w_0001 | 291 | 291 | 100% ✅ |
| w_0005 | 153 | 153 | 100% ✅ |
| w_0007 | 174 | 174 | 100% ✅ |

**고해상도 이미지 100% 성공!**

### Path Simplification 품질

**평균 65-67% 감소**:
- 형태 정확도: 육안으로 거의 차이 없음
- 레이저 속도: 2-3배 향상 예상
- 파일 크기: 65% 감소

### 물리적 크기 정확도

**300 DPI 기준**:
- 7216 px = 611.0 mm (24.1 inch)
- 5412 px = 458.2 mm (18.0 inch)
- 1 px = 0.0847 mm

**검증 필요**:
- 스캔 시 실제 DPI 확인
- 필요시 `--svg-dpi` 옵션으로 조정

---

## 향후 개선 사항

### 1. DPI 자동 감지
현재는 수동으로 `--svg-dpi 300` 설정
→ EXIF 정보에서 자동 추출

### 2. DXF 형식 지원
일부 레이저 커터는 DXF 선호
→ DXF 출력 옵션 추가

### 3. 구멍 병합 기능
인접한 구멍들을 하나로 병합
→ 복원 작업 간소화

### 4. 레이어별 출력
크기별로 레이어 분리
→ 단계별 복원 가능

---

## 참고 자료

### 관련 문서
- `FINAL_SUMMARY_hole_detection_b138.md`: b=138 파라미터 결정 과정
- `what_are_b_and_p.md`: LAB b-channel 설명
- `2025-10-29_multiple_images_test_b138.md`: 8개 이미지 테스트

### SVG 스펙
- W3C SVG Specification: https://www.w3.org/TR/SVG/
- SVG Path Data: https://www.w3.org/TR/SVG/paths.html

### 레이저 커팅
- 대부분의 레이저 커터는 SVG 직접 지원
- Adobe Illustrator, Inkscape로 편집 가능
- 검은색 선(stroke)을 커팅 경로로 인식

---

## 최종 요약

### ✅ 완성된 기능
1. **해상도 자동 스케일링**: 고해상도 기준, 모든 해상도 일관성
2. **SVG 벡터 출력**: 레이저 커팅 최적화
3. **물리적 크기**: mm 단위 메타데이터
4. **Path 단순화**: 65-67% 포인트 감소

### 🎯 최적 파라미터
```bash
--method lab_b
--s-threshold 138
--min-area 70
--max-area 500000  # (NEW: 5배 증가)
--export-svg
--svg-simplify 1.0
```

### 🔥 주요 발견
- **w_0005 거대 구멍**: 465,374 px (58x58mm)
- **max-area 500k 필요성**: 93% 사용 (465k/500k)
- **자동 스케일링 효과**: test_small 268개 검출 (이전 72개)

### 📊 테스트 완료
- ✅ test_small (저해상도)
- ✅ w_0001 (큰 구멍)
- ✅ w_0005 (거대 구멍)
- ✅ w_0007 (많은 구멍)

### 🚀 레이저 커팅 준비
- ✅ SVG 형식 (벡터)
- ✅ 해상도 독립적
- ✅ 물리적 크기 포함
- ✅ 크기 조절 자유

---

**마지막 업데이트**: 2025-10-30
**테스트 완료**: test_small, w_0001, w_0005, w_0007
**권장 파라미터**: b=138, min=70, max=500k, SVG 출력
**레이저 커팅**: 준비 완료 ✅
