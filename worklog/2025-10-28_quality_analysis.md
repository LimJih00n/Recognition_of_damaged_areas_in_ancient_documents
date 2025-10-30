# 품질 분석 - 2025-10-28

## 분석 대상
- **이미지**: `datasets/test_image.tif`
- **감지 결과**: `results/svg/holes_improved.svg`
- **파라미터**: threshold=210, edge-strength=40, simplify=0.5, min-area=50

## 분석 도구
`analyze_detection_quality.py` 생성 - 자동으로 품질 분석 수행

### 기능
1. 잠재적 구멍 추출 (낮은 threshold=200으로 모든 가능성 탐색)
2. 놓친 구멍 분석 (면적, 밝기, 위치)
3. 경계 노이즈 분석 (원형도, 압축률)
4. 시각화 비교 이미지 생성

## 자동 분석 결과

### 1. 전체 통계
- **감지된 구멍**: 276개
- **잠재적 구멍 영역**: 15.33% (threshold=200 기준)
- **자동 감지된 놓친 구멍**: 50개 (면적 100+ 픽셀)

### 2. 경계 품질
- **매끄러운 경계**: 198개 (71.7%)
- **노이즈가 많은 경계**: 63개 (22.8%)
  - 원형도 < 0.3
  - 압축률 > 50

### 3. 상위 10개 놓친 구멍 (자동 분석)
| 순위 | 면적 | 밝기 | 위치 (x, y) |
|------|------|------|-------------|
| 1 | 9,562 | 221.5 | (6627, 2600) |
| 2 | 6,600 | 223.4 | (7061, 2130) |
| 3 | 2,648 | 221.8 | (7114, 2419) |
| 4 | 2,382 | 227.2 | (6025, 2462) |
| 5 | 2,002 | 226.4 | (2627, 1966) |
| 6 | 1,974 | 223.8 | (5947, 2748) |
| 7 | 1,668 | 230.3 | (4657, 2299) |
| 8 | 1,526 | 225.8 | (5040, 2234) |
| 9 | 1,500 | 222.3 | (7085, 3641) |
| 10 | 1,160 | 226.3 | (2935, 3194) |

### 4. 상위 10개 노이즈 경계
| 순위 | 면적 | 원형도 | 압축률 | 위치 (x, y) |
|------|------|--------|--------|-------------|
| 1 | 4,172 | 0.017 | 732.5 | (3121, 3185) |
| 2 | 207 | 0.019 | 657.9 | (6105, 4160) |
| 3 | 12,883 | 0.030 | 414.2 | (1430, 2537) |
| 4 | 456 | 0.040 | 315.2 | (1237, 4292) |
| 5 | 11,924,001 | 0.041 | 307.8 | (0, 0) |
| 6 | 28,905 | 0.041 | 306.5 | (4911, 2357) |
| 7 | 388 | 0.046 | 270.9 | (1496, 2091) |
| 8 | 188 | 0.047 | 265.4 | (2784, 2200) |
| 9 | 466 | 0.049 | 256.8 | (1475, 3848) |
| 10 | 506 | 0.049 | 255.1 | (1501, 2259) |

## 사용자 피드백 (수동 검토)

### 실제 놓친 구멍: ~4개
- 자동 분석의 50개는 과다 추정
- **실제로 중요한 놓친 구멍은 4개 정도**
- 대부분의 구멍은 잘 감지됨 ✓

### 왼쪽 상단 문제
- **위치**: 왼쪽 상단 영역
- **원인 추정**: 배경색이 더 진함 (beige → darker beige)
- **증상**: 구멍이 주변과 대비가 낮아서 edge detection 실패
- **밝기**: 해당 영역의 배경이 ~190-200 (다른 부분 206.8)

### 경계 노이즈
- 위쪽/왼쪽 가장자리의 큰 찢어진 부분
- 원형도 매우 낮음 (0.017-0.049) → 복잡한 모양
- 이것은 실제 손상의 특성이므로 큰 문제는 아님
- 하지만 윤곽선 단순화는 개선 가능

## 문제점 및 원인 분석

### 1. 왼쪽 상단 구멍 놓침
**원인**:
- 해당 영역의 배경색이 더 어두움 (shadow or discoloration)
- 밝기 기반 threshold(210)가 이 영역에는 너무 높음
- CLAHE가 전역적으로 적용되지만 충분하지 않음

**해결 방향**:
1. **Adaptive thresholding** 적용 - 지역별로 다른 threshold
2. **CLAHE 강화** - clipLimit 2.0 → 3.0
3. **밝기 정규화** - 배경 불균일도 보정

### 2. Edge Coverage Threshold
**현재**: 15% 이상이 edge와 겹쳐야 구멍으로 인정
**문제**:
- 밝기는 충분하지만 (221-230) edge가 약한 구멍
- bilateral filter가 너무 강해서 일부 edge 소실

**해결 방향**:
1. Edge coverage 15% → **10%**로 낮추기
2. 또는 밝기가 충분히 높으면 (225+) edge coverage 무시

### 3. 경계 노이즈
**현재**: 63개 구멍이 복잡한 경계 (원형도 < 0.3)
**문제**:
- 대부분 가장자리의 큰 찢어진 부분
- 실제 손상의 특성이므로 불가피한 측면 있음

**해결 방향**:
1. **Morphological smoothing** - 경계를 부드럽게
2. **윤곽선 단순화** - simplify 0.5 → 1.0~1.5
3. 단, 정확도와 트레이드오프 존재

## 개선 우선순위

### 1순위: 왼쪽 상단 영역 구멍 감지 개선
**방법 A - Adaptive Thresholding**:
```python
# 전역 threshold 대신 지역별 threshold
adaptive = cv2.adaptiveThreshold(
    enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY, 51, -10
)
```

**방법 B - CLAHE 강화 + 낮은 threshold**:
```python
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16, 16))
threshold = 200  # 210 → 200
```

**방법 C - 밝기 정규화**:
```python
# 배경 불균일도 보정
blur = cv2.GaussianBlur(gray, (51, 51), 0)
normalized = gray - blur + 200
```

### 2순위: Edge Coverage 조정
**현재 로직**:
```python
if edge_coverage > 0.15:  # 15%
    if mean_brightness > 170 or edge_coverage > 0.35:
        valid_contours.append(contour)
```

**개선 로직**:
```python
# 밝기가 매우 높으면 edge 요구사항 완화
if edge_coverage > 0.10:  # 15% → 10%
    if mean_brightness > 225:  # 매우 밝음
        valid_contours.append(contour)
    elif mean_brightness > 170 or edge_coverage > 0.30:
        valid_contours.append(contour)
```

### 3순위: 경계 스무딩 (선택사항)
**방법 A - Morphological Smoothing**:
```python
# 윤곽선 추출 후 smoothing
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
smoothed_mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
smoothed_mask = cv2.morphologyEx(smoothed_mask, cv2.MORPH_OPEN, kernel)
```

**방법 B - 윤곽선 단순화 강화**:
```python
simplify_epsilon = 1.0  # 0.5 → 1.0
# 또는 면적에 따라 다르게
if area > 5000:
    epsilon = 2.0  # 큰 영역은 더 단순화
else:
    epsilon = 0.5  # 작은 영역은 정밀하게
```

## 다음 작업 계획 (내일)

### Step 1: 파라미터 실험
다음 조합들을 테스트:

**실험 1 - Adaptive Threshold**:
```bash
# 코드 수정 필요
# adaptive thresholding 추가
```

**실험 2 - CLAHE 강화**:
```bash
python extract_holes_with_edges.py \
  --input "datasets/test_image.tif" \
  --output "results/svg/holes_v2.svg" \
  --threshold 200 \
  --edge-strength 40 \
  --simplify 0.5 \
  --min-area 50
  # CLAHE clipLimit 3.0으로 코드 수정
```

**실험 3 - Edge Coverage 완화**:
```bash
# edge_coverage > 0.10으로 코드 수정
# 밝기 225+ 조건 추가
```

**실험 4 - 경계 스무딩**:
```bash
# simplify 1.0
python extract_holes_with_edges.py \
  --input "datasets/test_image.tif" \
  --output "results/svg/holes_smooth.svg" \
  --threshold 210 \
  --edge-strength 40 \
  --simplify 1.0 \
  --min-area 50
```

### Step 2: 재분석
각 실험 결과를 분석:
```bash
python analyze_detection_quality.py \
  --image "datasets/test_image.tif" \
  --svg "results/svg/holes_v2.svg" \
  --output "results/analysis_v2"
```

### Step 3: 최적 설정 확정
- 놓친 구멍 최소화
- 경계 노이즈 감소
- 정확도와 완성도 밸런스

### Step 4: 배치 처리
최적 설정으로 전체 이미지 처리:
```bash
# 배치 처리 스크립트 작성
for file in datasets/1첩/*.tif; do
    python extract_holes_with_edges.py \
      --input "$file" \
      --output "results/svg_batch/$(basename $file .tif).svg" \
      --threshold [최적값] \
      --edge-strength [최적값] \
      --simplify [최적값]
done
```

## 생성된 파일

### 분석 도구
- `analyze_detection_quality.py` - 품질 분석 자동화

### 분석 결과
- `results/analysis/missed_holes.png` - 놓친 구멍 시각화 (빨강/노랑)
- `results/analysis/noisy_boundaries.png` - 노이즈 경계 시각화 (빨강)
- `results/analysis/comparison.png` - 6개 패널 비교 시각화

### 현재 최선 결과
- `results/svg/holes_improved.svg` - 276개 구멍 감지
- `results/svg/holes_improved_mask.png` - 마스크 시각화

## 핵심 인사이트

1. **배경 불균일성**
   - 고문서의 특성상 배경색이 균일하지 않음
   - 왼쪽 상단은 더 어두운 배경 (shadow or aging)
   - 단일 threshold 방식의 근본적 한계

2. **Edge Detection의 한계**
   - Bilateral filter로 노이즈 제거 시 약한 edge도 소실
   - 대비가 낮은 구멍은 edge detection 실패
   - Edge coverage 기준이 너무 엄격할 수 있음

3. **실제 vs 자동 분석 차이**
   - 자동 분석: 50개 놓침
   - 실제 검토: 4개만 놓침
   - 자동 분석의 false positive 높음
   - threshold=200 기준이 너무 낮음

4. **경계 복잡도**
   - 찢어진 부분은 본질적으로 복잡한 모양
   - 과도한 단순화는 정확도 손실
   - 적절한 밸런스 필요

## 기술적 교훈

1. **지역적 처리의 필요성**
   - Adaptive thresholding
   - 배경 불균일도 보정
   - 지역별 파라미터 조정

2. **다중 기준 검증**
   - 밝기만으로 부족
   - Edge만으로도 부족
   - 둘의 적절한 조합이 중요

3. **품질 평가의 중요성**
   - 자동 분석 후 수동 검토 필수
   - 정량적 지표 + 시각적 확인
   - 사용자 피드백 반영

4. **완벽한 자동화의 한계**
   - 모든 케이스를 커버하는 단일 파라미터는 없음
   - 이미지별 특성 고려 필요
   - 후처리 또는 수동 보정 가능성 열어두기

## 내일 할 일 체크리스트

- [ ] **실험 1**: Adaptive thresholding 구현 및 테스트
- [ ] **실험 2**: CLAHE clipLimit 3.0 + threshold 200 테스트
- [ ] **실험 3**: Edge coverage 10% + 밝기 기반 예외 처리
- [ ] **실험 4**: Simplify 1.0으로 경계 스무딩 테스트
- [ ] 각 실험 결과 분석 (analyze_detection_quality.py 사용)
- [ ] 최적 설정 확정 및 문서화
- [ ] 배치 처리 스크립트 작성
- [ ] worklog 업데이트

## 참고 자료

### OpenCV 함수
- `cv2.adaptiveThreshold()` - 지역별 threshold
- `cv2.createCLAHE()` - 대비 향상
- `cv2.bilateralFilter()` - edge-preserving smoothing
- `cv2.morphologyEx()` - morphological operations
- `cv2.approxPolyDP()` - polyline simplification

### 평가 지표
- **원형도 (Circularity)**: 4π×area / perimeter² (1.0 = 완전한 원)
- **압축률 (Compactness)**: perimeter² / area (낮을수록 매끄러움)
- **Edge Coverage**: overlap / perimeter (경계 명확도)
