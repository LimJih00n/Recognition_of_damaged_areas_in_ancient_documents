# 작업 로그 - 2025-10-29 16:31 방법론 비교 및 분석

## 작업 개요
기존 results/goodcase/ 결과물의 생성 코드를 추적하고, w_0005.tif 이미지에 대해 다양한 파라미터와 방법론을 체계적으로 비교 실험

## 1단계: 기존 결과물 코드 추적

### `results/goodcase/` 디렉토리 분석

#### 1. `extracted_holes_complete/` 디렉토리
**생성 스크립트**: `extract_and_map_holes.py`
- **파일 구성**:
  - `extraction_grid.png`: 추출된 구멍들의 10열 그리드 시각화
  - `hole_mask.png`: 이진 마스크 이미지
  - `mapped_holes.png`: 원본 이미지에 구멍 위치 매핑
  - `comparison.png`: 원본 vs 매핑 나란히 비교
  - `individual_holes/`: 각 구멍의 개별 이미지

**핵심 코드**:
```python
# extract_and_map_holes.py:354
create_mapping_visualization(image, holes, "mapped_holes.png")

# extract_and_map_holes.py:357
create_extraction_visualization(image, holes, "extraction_grid.png", grid_cols=10)

# extract_and_map_holes.py:360
create_side_by_side_comparison(image, holes, "comparison.png")
```

**특징**: LAB 색공간 b-채널 기반 추출 + 시각화

#### 2. `lab_hsv_w0005/` 및 `lab_hsv_test_small/` 디렉토리
**생성 스크립트**: `extract_whiteness_based.py --method lab_hsv`
- **파일 구성**:
  - `white_mask.png`: 흰색 영역 마스크 (extract_whiteness_based.py:351)
  - `comparison.png`: 원본 vs 추출 결과 (extract_whiteness_based.py:367)
  - `individual_holes/`: 개별 구멍 이미지

**핵심 원리**:
```python
# LAB + HSV 결합 방법
# 1. LAB b-channel (노란색 정도) - 낮을수록 흰색
# 2. HSV Saturation (채도) - 낮을수록 무채색
# 두 조건을 AND로 결합
```

#### 3. `holes_improved_*.png/svg` 파일들
**생성 스크립트**: `extract_holes_to_svg.py`
- **파일**:
  - `holes_improved.svg`: SVG 벡터 형식의 구멍 데이터
  - `holes_improved_preview.png`: 회색 배경에 흰색 구멍 미리보기 (line 109)
  - `holes_improved_mask.png`: 이진 마스크 (외부에서 생성 추정)

**특징**:
- 단순 밝기 임계값(threshold) 기반 추출
- SVG path 형식으로 변환하여 벡터 데이터 생성
- 윤곽선 단순화(approxPolyDP) 적용

---

## 2단계: 체계적 방법론 비교 실험

### 실험 대상
- **이미지**: `datasets/1첩/w_0005.tif`
- **크기**: 7216 x 5412 (약 39 megapixels)
- **b-channel 통계**: mean=144.1, std=6.7, p25=143

### 방법 1: LAB b-channel 기반 (기준 방법)

#### 실험 1-1: min-area 변화
```bash
# 작은 구멍까지 모두 추출
python extract_and_map_holes.py \
  --input "datasets/1첩/w_0005.tif" \
  --b-threshold auto \
  --output-dir results/extracted_1chup_w0005_auto \
  --min-area 10
```
**결과**:
- Threshold: `b < 143` (p25 자동 계산)
- 마스크 커버리지: 20.45%
- 총 후보 윤곽선: 28,298개
- 유효 구멍: **12,004개**
- 면적 범위: 10 ~ 93,388 pixels
- 평균 면적: 122.2 pixels
- 중간값 면적: 23.0 pixels
- 총 손상 면적: 1,467,405 pixels (**3.76%**)

```bash
# 중간 크기 필터링
python extract_and_map_holes.py \
  --input "datasets/1첩/w_0005.tif" \
  --b-threshold auto \
  --output-dir results/size_filtered_w0005_50 \
  --min-area 50
```
**결과**:
- Threshold: `b < 143`
- 유효 구멍: **2,922개**
- 면적 범위: 50 ~ 93,388 pixels
- 평균 면적: 436.1 pixels
- 중간값 면적: 96.5 pixels
- 총 손상 면적: 1,274,180 pixels (**3.26%**)

```bash
# 큰 구멍만 추출
python extract_and_map_holes.py \
  --input "datasets/1첩/w_0005.tif" \
  --b-threshold auto \
  --output-dir results/size_filtered_w0005_100 \
  --min-area 100
```
**결과**:
- Threshold: `b < 143`
- 유효 구멍: **1,413개**
- 면적 범위: 100 ~ 93,388 pixels
- 평균 면적: 827.9 pixels
- 중간값 면적: 197.5 pixels
- 총 손상 면적: 1,169,808 pixels (**3.00%**)

**분석**:
- min-area를 높일수록 작은 노이즈가 제거되지만, 실제 작은 구멍도 함께 제거됨
- 10 → 50: 12,004 → 2,922개 (75.6% 감소)
- 50 → 100: 2,922 → 1,413개 (51.6% 감소)
- 총 손상 면적은 상대적으로 완만하게 감소 (3.76% → 3.00%)

---

### 방법 2: 하이브리드 (LAB + Edge)

```bash
python extract_holes_hybrid.py \
  --input "datasets/1첩/w_0005.tif" \
  --output-dir results/hybrid_w0005 \
  --b-percentile 25 \
  --edge-coverage 0.10 \
  --min-area 10
```

**핵심 알고리즘**:
```
Step 1: Color 기반 후보 생성
  - LAB b-channel < 143 (p25)
  - 후보 영역: 20.45%

Step 2: Edge Detection (Canny)
  - Threshold: 40-120
  - 엣지 픽셀: 66.97%

Step 3: Edge Coverage 필터링
  - 각 후보 윤곽선의 경계선 중 10% 이상이 엣지와 겹치는 것만 선택
  - 28,298개 후보 → 11,922개 통과 (86개 제거)
```

**결과**:
- 최종 마스크 커버리지: 20.41%
- 유효 구멍: **11,918개**
- 면적 범위: 10 ~ 93,388 pixels
- 평균 면적: 123.0 pixels
- 중간값 면적: 23.5 pixels
- 총 손상 면적: 1,465,651 pixels (**3.75%**)

**비교 (vs LAB 단독 min-area=10)**:
- 구멍 개수: 12,004 → 11,918 (86개, 0.7% 감소)
- 손상 면적: 3.76% → 3.75% (거의 동일)
- **결론**: Edge 필터링으로 명확한 경계가 없는 86개 영역을 제거

---

### 방법 3: 전처리 + LAB (CLAHE)

```bash
python extract_with_preprocessing.py \
  --input "datasets/1첩/w_0005.tif" \
  --output-dir results/preprocess_clahe_w0005 \
  --method clahe \
  --min-area 100
```

**CLAHE (Contrast Limited Adaptive Histogram Equalization)**:
```python
# 전처리 효과
Original b: 144.1 ± 6.7
Enhanced b: 141.7 ± 13.7  # 표준편차 2배 증가 (대비 향상)
```

**결과**:
- Threshold: `b < 134` (p25, 전처리 후)
- 마스크 커버리지: 23.09%
- 총 후보: 44,469개
- 유효 구멍: **2,610개**
- 면적 범위: 100 ~ 71,680 pixels
- 평균 면적: 800.2 pixels
- 중간값 면적: 202.0 pixels
- 총 손상 면적: 2,088,500 pixels (**5.35%**)

**분석**:
- CLAHE로 대비가 향상되어 더 많은 미세한 변화 감지
- 후보 개수는 크게 증가했지만 (28,298 → 44,469), 크기 필터링(min-area=100)으로 최종 개수는 적음
- ⚠️ **과다 감지 위험**: 5.35% 손상은 과도하게 높음 (베이지 변색 부분도 포함)

---

### 방법 4: 흰색 기반 (Whiteness)

#### 실험 4-1: HSV 기본
```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/w_0005.tif" \
  --output-dir results/whiteness_hsv_w0005 \
  --method hsv \
  --min-area 100
```

**HSV 통계**:
- S (saturation): 49.9 ± 20.9
- V (value): 218.0 ± 13.3

**Threshold (기본값)**:
- S < 46 (p25, 낮은 채도)
- V > 226 (p75, 높은 밝기)

**결과**:
- 흰색 커버리지: 15.15%
- 총 후보: 29,491개
- 유효 구멍: **767개**
- 면적 범위: 100 ~ 24,750 pixels
- 평균 면적: 542.8 pixels
- 총 손상 면적: 416,356 pixels (**1.07%**)

#### 실험 4-2: HSV Strict (엄격한 조건)
```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/w_0005.tif" \
  --output-dir results/whiteness_strict_w0005 \
  --method hsv \
  --s-percentile 15 \
  --v-percentile 85 \
  --min-area 100
```

**Threshold (strict)**:
- S < 18 (p15, 매우 낮은 채도)
- V > 230 (p85, 매우 높은 밝기)

**결과**:
- 흰색 커버리지: 9.52%
- 총 후보: 7,353개
- 유효 구멍: **597개**
- 면적 범위: 100 ~ 42,492 pixels
- 평균 면적: 660.0 pixels
- 총 손상 면적: 394,016 pixels (**1.01%**)

#### 실험 4-3: Combined (HSV + RGB + LAB)
```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/w_0005.tif" \
  --output-dir results/whiteness_combined_w0005 \
  --method combined \
  --min-area 100
```

**결합 방식**:
```python
# 세 가지 색공간에서 흰색 감지
HSV mask: 15.15%
RGB balance mask: 13.29%
LAB achromatic mask: 16.11%
# AND 연산으로 결합 (교집합)
Combined: 13.10%
```

**결과**:
- 최종 커버리지: 13.10%
- 총 후보: 12,487개
- 유효 구멍: **231개**
- 면적 범위: 100 ~ 13,721 pixels
- 평균 면적: 674.9 pixels
- 총 손상 면적: 155,907 pixels (**0.40%**)

**분석**:
- Combined 방법이 가장 보수적 (세 조건 모두 만족)
- 767 → 597 → 231개로 점점 엄격해짐
- ⚠️ **과소 감지 위험**: 0.40%는 너무 낮음 (많은 구멍 놓침)

---

## 3. 종합 비교 및 분석

### 방법별 결과 요약

| 방법 | 파라미터 | 구멍 수 | 평균 면적 | 총 손상율 | 특징 |
|------|---------|---------|----------|----------|------|
| **LAB b-channel** | min-area=10 | 12,004 | 122.2 | 3.76% | 가장 많은 구멍 검출 |
| **LAB b-channel** | min-area=50 | 2,922 | 436.1 | 3.26% | 중간 필터링 |
| **LAB b-channel** | min-area=100 | 1,413 | 827.9 | 3.00% | 큰 구멍 위주 |
| **Hybrid (LAB+Edge)** | edge-cov=0.1 | 11,918 | 123.0 | 3.75% | 명확한 경계만 |
| **CLAHE + LAB** | min-area=100 | 2,610 | 800.2 | 5.35% | ⚠️ 과다 감지 |
| **HSV** | 기본값 | 767 | 542.8 | 1.07% | 흰색만 엄격히 |
| **HSV Strict** | p15/p85 | 597 | 660.0 | 1.01% | 매우 엄격 |
| **Combined** | HSV+RGB+LAB | 231 | 674.9 | 0.40% | ⚠️ 과소 감지 |

### 핵심 인사이트

#### 1. 크기 필터링의 영향
```
min-area=10:  12,004개 (노이즈 포함)
min-area=50:   2,922개 (균형)
min-area=100:  1,413개 (주요 손상만)

→ min-area=50이 노이즈 제거와 민감도의 균형점
```

#### 2. Edge 필터링의 효과
```
LAB 단독:    12,004개
LAB+Edge:    11,918개 (86개 제거, 0.7%)

→ Edge 필터링의 효과는 제한적
→ 대부분의 b-channel 낮은 영역이 이미 명확한 경계 가짐
```

#### 3. CLAHE 전처리의 함정
```
일반 LAB:   28,298개 후보 → 1,413개 유효 (min-area=100)
CLAHE+LAB:  44,469개 후보 → 2,610개 유효 (min-area=100)

→ 대비 향상으로 더 많은 영역 감지
→ BUT 5.35% 손상율은 과도 (베이지 변색도 포함)
```

#### 4. 흰색 기반 방법의 한계
```
LAB b-channel: 3.76% 손상
HSV 흰색:      1.07% 손상
Combined:      0.40% 손상

→ 흰색만 감지하면 베이지색 변색 영역 누락
→ 실제 구멍은 완전한 흰색이 아닐 수 있음
```

### 권장 파라미터

#### 목적별 권장 설정

**1. 정밀 분석 (모든 손상 검출)**
```bash
python extract_and_map_holes.py \
  --input IMAGE \
  --b-threshold auto \
  --min-area 10 \
  --output-dir results/detailed/
```
- 12,004개 구멍, 3.76% 손상
- 작은 구멍까지 모두 감지
- 후처리로 노이즈 제거 필요

**2. 균형잡힌 검출 (권장)**
```bash
python extract_and_map_holes.py \
  --input IMAGE \
  --b-threshold auto \
  --min-area 50 \
  --output-dir results/balanced/
```
- 2,922개 구멍, 3.26% 손상
- 노이즈 대부분 제거 + 주요 손상 유지

**3. 주요 손상만**
```bash
python extract_and_map_holes.py \
  --input IMAGE \
  --b-threshold auto \
  --min-area 100 \
  --output-dir results/major_damage/
```
- 1,413개 구멍, 3.00% 손상
- 큰 구멍만 추출

**4. 하이브리드 (명확한 경계)**
```bash
python extract_holes_hybrid.py \
  --input IMAGE \
  --b-percentile 25 \
  --edge-coverage 0.10 \
  --min-area 10 \
  --output-dir results/hybrid/
```
- 11,918개 구멍, 3.75% 손상
- 명확한 경계가 있는 구멍만

---

## 4. 생성된 파일 구조

### 각 방법의 출력 파일

```
results/
├── extracted_1chup_w0005_auto/           # LAB b-channel (min-area=10)
│   ├── comparison.png                     # 원본 vs 결과 비교
│   ├── mapped_holes.png                   # 구멍 위치 매핑
│   ├── extraction_grid.png                # 10열 그리드
│   ├── hole_mask.png                      # 이진 마스크
│   └── individual_holes/                  # 12,004개 개별 이미지
│       ├── hole_0000.png
│       ├── hole_0001.png
│       └── ...
│
├── size_filtered_w0005_50/               # LAB (min-area=50)
│   └── [동일 구조, 2,922개]
│
├── size_filtered_w0005_100/              # LAB (min-area=100)
│   └── [동일 구조, 1,413개]
│
├── hybrid_w0005/                         # LAB + Edge
│   └── [동일 구조, 11,918개]
│
├── preprocess_clahe_w0005/               # CLAHE + LAB
│   └── [동일 구조, 2,610개]
│
├── whiteness_hsv_w0005/                  # HSV 흰색
│   ├── comparison.png
│   ├── white_mask.png                    # 흰색 마스크
│   └── individual_holes/                 # 767개
│
├── whiteness_strict_w0005/               # HSV Strict
│   └── [동일 구조, 597개]
│
└── whiteness_combined_w0005/             # Combined
    └── [동일 구조, 231개]
```

---

## 5. 결론 및 다음 단계

### 주요 발견

1. **LAB b-channel이 가장 효과적**: 베이지색 종이에서 흰색/밝은 구멍을 찾는데 최적
2. **min-area=50이 균형점**: 노이즈 제거 + 실제 손상 유지
3. **Edge 필터링 효과 제한적**: b-channel 이미 좋은 결과
4. **CLAHE는 과도 감지**: 변색 부분까지 포함하여 5.35%로 과다
5. **흰색 기반은 과소 감지**: 실제 구멍이 완전한 흰색이 아님

### 최종 권장 방법

```bash
# 가장 신뢰할 수 있는 방법
python extract_and_map_holes.py \
  --input "datasets/1첩/w_0005.tif" \
  --b-threshold auto \
  --min-area 50 \
  --output-dir results/final_w0005/

# 결과: 2,922개 구멍, 3.26% 손상율
```

### 다음 단계 제안

1. **다른 이미지 테스트**: 다른 고문서 이미지에도 동일한 파라미터 적용
2. **시각적 검증**: 결과 이미지를 육안으로 확인하여 false positive/negative 분석
3. **SVG 변환**: 최종 결과를 SVG로 변환하여 벡터 데이터 생성
4. **복원 워크플로우**: 추출된 구멍 데이터를 활용한 이미지 복원 파이프라인 구축

---

## 참고: 코드 위치

- **LAB 기반**: `extract_and_map_holes.py:94-135` (detect_holes 함수)
- **하이브리드**: `extract_holes_hybrid.py:85-185` (hybrid_detect 함수)
- **전처리**: `extract_with_preprocessing.py:23-67` (preprocess_image 함수)
- **흰색 기반**: `extract_whiteness_based.py:13-173` (detect_whiteness 함수)
- **시각화**:
  - `extract_and_map_holes.py:167-218` (create_mapping_visualization)
  - `extract_and_map_holes.py:221-249` (create_extraction_visualization)
  - `extract_and_map_holes.py:253-279` (create_side_by_side_comparison)
