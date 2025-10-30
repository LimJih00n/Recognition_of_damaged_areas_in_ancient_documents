# 텍스처 + 대비 기반 손상 부위 감지 알고리즘

**날짜**: 2025-10-28
**소스 파일**: `extract_holes_texture_contrast.py`
**생성된 이미지**: `1_enhanced.png`, `1_L_enhanced.png`, `4_contrast_mask.png`

## 알고리즘 개요

문서의 손상 부위(구멍)와 정상 문서를 명확하게 구분하기 위한 멀티 스케일 텍스처 및 대비 분석 알고리즘

## 핵심 성공 요인

1. **구멍을 모두 정확히 찾음**
2. **문서와 구멍의 색 구분이 명확함**
3. **손상부위와 원래 문서 간의 색 대비가 명확해짐**

## 주요 단계 (9단계)

### Step 0: 전처리 (Lines 44-57)
```python
# 배경 불균일도 제거
background = cv2.GaussianBlur(gray, (101, 101), 0)
normalized = cv2.subtract(gray, background)
normalized = cv2.add(normalized, int(np.mean(gray)))

# CLAHE (Contrast Limited Adaptive Histogram Equalization)
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(16, 16))
enhanced = clahe.apply(normalized)
```
- **목적**: 조명 불균일 제거 및 대비 향상
- **결과 이미지**: `1_enhanced.png` (line 361)

### Step 1: Multi-scale Local Contrast (Lines 60-92)
```python
scales = [11, 21, 31, 51]
for scale in scales:
    local_mean = cv2.blur(enhanced, (scale, scale))
    contrast = cv2.subtract(enhanced, local_mean)
    contrast = np.maximum(contrast, 0).astype(np.uint8)
    contrast_maps.append(contrast)

combined_contrast = np.mean(contrast_maps, axis=0).astype(np.uint8)
_, contrast_mask = cv2.threshold(combined_contrast, 3, 255, cv2.THRESH_BINARY)
```
- **목적**: 여러 스케일에서 주변보다 밝은 영역 감지
- **핵심**: 주변 평균 대비 3 이상 밝으면 손상 후보
- **결과 이미지**: `4_contrast_mask.png` (line 364)

### Step 2: Texture Analysis (Lines 95-121)
```python
# Local variance로 텍스처 복잡도 측정
window_size = 7
for i in range(0, h - window_size, 3):
    for j in range(0, w - window_size, 3):
        window = enhanced[i:i+window_size, j:j+window_size]
        variance = np.var(window)
        texture_map[i:i+window_size, j:j+window_size] = variance

smooth_mask = (texture_map < 50).astype(np.uint8) * 255
```
- **목적**: 균일한 영역(손상) vs 불균일한 영역(종이 섬유질) 구분
- **기준**:
  - 종이 섬유질: variance 50-200
  - 손상 부위: variance 0-50

### Step 3: 절대 밝기 분석 (Lines 124-139)
```python
_, very_bright = cv2.threshold(enhanced, 215, 255, cv2.THRESH_BINARY)      # 확실한 구멍
_, bright = cv2.threshold(enhanced, 205, 255, cv2.THRESH_BINARY)           # 밝은 구멍
_, moderately_bright = cv2.threshold(enhanced, 195, 255, cv2.THRESH_BINARY) # 베이지 손상
```
- **목적**: 3단계 밝기 레벨로 다양한 손상 감지

### Step 4: 색상 변화 분석 (Lines 142-157)
```python
background_b = cv2.GaussianBlur(b, (51, 51), 0)
b_diff = cv2.subtract(background_b, b)
_, less_yellow = cv2.threshold(b_diff, 2, 255, cv2.THRESH_BINARY)
```
- **목적**: b 채널로 노란색 정도 측정
- **원리**: 손상 부위는 배경보다 덜 노랗다

### Step 5: 후보 결합 (Lines 160-189)
```python
# 규칙 1: 매우 밝음 (무조건 구멍)
candidates_1 = cv2.morphologyEx(very_bright, cv2.MORPH_CLOSE, kernel)

# 규칙 2: 밝음 + (contrast OR smooth OR less_yellow)
bright_enhanced = cv2.bitwise_and(bright,
                                 cv2.bitwise_or(contrast_mask,
                                 cv2.bitwise_or(smooth_mask, less_yellow)))

# 규칙 3: 중간 밝기 + contrast + smooth + less_yellow (베이지 손상)
beige_mask = cv2.bitwise_and(moderately_bright,
             cv2.bitwise_and(contrast_mask,
             cv2.bitwise_and(smooth_mask, less_yellow)))
```
- **목적**: 여러 조건을 조합하여 강건한 감지

### Step 6: Edge 검증 (Lines 193-206)
```python
blurred = cv2.GaussianBlur(enhanced, (9, 9), 2.0)
median = cv2.medianBlur(blurred, 5)
edges = cv2.Canny(median, 35, 70)
edges_dilated = cv2.dilate(edges, kernel_dilate, iterations=1)
```
- **목적**: 경계선이 명확한 영역 우선

### Step 7: 윤곽선 스코어링 (Lines 209-310)
**15점 만점 시스템**:
1. **밝기 점수** (0-4점): 215+ → 4점, 205+ → 3점, 195+ → 2점
2. **Local contrast 점수** (0-3점): 평균 contrast 10+ → 3점
3. **Texture 점수** (0-3점): 평균 variance 30 미만 → 3점
4. **Edge 점수** (0-3점): edge coverage 15%+ → 3점
5. **색상 점수** (0-2점): b 차이 3+ → 2점

**임계값**: 7점 이상만 유효

### Step 8-9: SVG 생성 및 결과 저장

## 생성된 디버그 이미지

디렉토리: `results/svg/debug_texture_contrast/`

1. `1_enhanced.png` - CLAHE 적용 이미지
2. `2_combined_contrast.png` - 멀티스케일 대비 맵
3. `3_texture_map.png` - 텍스처 복잡도 맵
4. `4_contrast_mask.png` - 대비 마스크 (주요 결과!)
5. `5_smooth_mask.png` - 균일 영역 마스크
6. `6_less_yellow.png` - 색상 변화 마스크
7. `7_candidates_1.png` - 매우 밝은 후보
8. `8_candidates_2.png` - 밝음+특징 후보
9. `9_candidates_3_beige.png` - 베이지 손상 후보
10. `10_combined_mask.png` - 최종 결합 마스크
11. `11_edges.png` - Canny 엣지

## 파라미터

- **min_area**: 50 (최소 영역 크기)
- **simplify_epsilon**: 0.5 (윤곽선 단순화)
- **contrast_threshold**: 3 (주변 대비 임계값)
- **texture_threshold**: 50 (텍스처 variance 임계값)
- **score_threshold**: 7 (최소 점수)

## 다음 단계

1. ✅ **성공**: 손상 부위와 문서 간 명확한 구분
2. **TODO**: contrast_mask를 기반으로 손상 부위만 추출
3. **TODO**: 이미지를 문서(정상)와 손상 부위로 이진화
4. **TODO**: 각 영역을 단순화하여 별도 처리

## 코드 실행 방법

```bash
python extract_holes_texture_contrast.py \
  --input input_image.png \
  --output results/svg/output.svg \
  --min-area 50 \
  --simplify 0.5
```
