# 구멍 검출 최종 정리: 파라미터 및 방법론

**작성일**: 2025-10-29
**목적**: 고문서 구멍 검출 최적 파라미터 및 전체 파이프라인 정리

---

## 📋 목차

1. [최종 권장 파라미터](#최종-권장-파라미터)
2. [전체 처리 파이프라인](#전체-처리-파이프라인)
3. [파라미터 결정 과정](#파라미터-결정-과정)
4. [다중 이미지 테스트 결과](#다중-이미지-테스트-결과)
5. [Edge Detection 비교](#edge-detection-비교)
6. [사용법 및 예시](#사용법-및-예시)
7. [문제 해결](#문제-해결)

---

## 최종 권장 파라미터

### 🏆 일반 문서용 (b평균 > 140)

```bash
python extract_whiteness_based.py \
  --method lab_b \
  --s-threshold 138 \
  --min-area 10 \
  --max-area 200000
```

| 파라미터 | 값 | 의미 | 중요도 |
|---------|-----|------|--------|
| `--method` | `lab_b` | LAB b-channel 단독 사용 | ⭐⭐⭐ |
| `--s-threshold` | `138` | b<138인 픽셀을 구멍으로 판단 | ⭐⭐⭐ |
| `--min-area` | `10` | 최소 구멍 크기 (pixels) | ⭐⭐ |
| `--max-area` | `200000` | 최대 구멍 크기 (pixels) | ⭐⭐⭐ |

**적용 대상**: test_small, w_0001, w_0003, w_0005, w_0007, w_0015

---

### ⚠️ 심각한 손상 문서용 (b평균 ≈ 138)

```bash
python extract_whiteness_based.py \
  --method lab_b \
  --s-threshold 135 \
  --min-area 10 \
  --max-area 200000
```

**변경 사항**: `--s-threshold 138 → 135` (더 엄격하게)

**적용 대상**: w_0010 (b=138.2, Coverage 52.91%), w_0018 (b=137.8)

---

## 전체 처리 파이프라인

### 7단계 처리 과정

```
입력 이미지
    ↓
[1] LAB 색공간 변환
    ↓
[2] b-channel Threshold (b<138)
    ↓
[3] Morphological Operations (정리)
    ↓
[4] Contour Detection (윤곽선 찾기)
    ↓
[5] Size Filtering (크기 필터)
    ↓
[6] 개별 구멍 추출
    ↓
[7] y좌표 역순 정렬
    ↓
결과 저장
```

---

### 단계별 상세 설명

#### [1] LAB 색공간 변환
```python
lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
L, a, b = cv2.split(lab)
```

**LAB 색공간**:
- **L**: Lightness (명도) 0~100
- **a**: Green(-) ↔ Red(+)
- **b**: Blue(-) ↔ Yellow(+) ← **구멍 검출에 사용**

**왜 LAB?**:
- RGB는 밝기와 색상이 섞여있음
- LAB는 명도(L)와 색상(a,b)이 분리됨
- **b-channel만으로 흰색 구멍과 노란 종이를 구분 가능**

---

#### [2] b-channel Threshold
```python
b_thresh = 138  # 고정값
white_mask = (b < b_thresh).astype(np.uint8) * 255
```

**결과**: 이진 마스크 (binary mask)
- `255` (흰색): b<138인 픽셀 = 구멍
- `0` (검은색): b≥138인 픽셀 = 종이

**b=138의 물리적 의미**:
```
b < 128: 파란색 계열
b = 128: 중립 (회색)
b = 138: 흰색~약간 노란색 ⭐ (우리의 threshold)
b > 140: 노란색/베이지색 (변색된 종이)
```

---

#### [3] Morphological Operations
```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)
```

**(1) MORPH_CLOSE (닫기)**:
- 목적: 작은 구멍이나 틈을 메움
- 효과: 끊어진 영역을 연결

**(2) MORPH_OPEN (열기)**:
- 목적: 작은 점 노이즈 제거
- 효과: 튀어나온 작은 점들 제거

**커널 크기**: 3x3 타원형 (보수적 정리)

---

#### [4] Contour Detection
```python
contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

**파라미터**:
- `RETR_EXTERNAL`: 외곽 윤곽선만 (구멍 안의 구멍은 무시)
- `CHAIN_APPROX_SIMPLE`: 윤곽선 단순화 (메모리 절약)

---

#### [5] Size Filtering ⭐⭐⭐
```python
area = cv2.contourArea(cnt)
if area < min_area or area > max_area:
    excluded += 1
    continue
```

**현재 설정**:
- `min_area = 10` pixels (10픽셀 미만 제외)
- `max_area = 200000` pixels (20만 픽셀 초과 제외)

**효과**: **87-93% contour 감소!** (가장 중요한 단계!)

| 이미지 | Filter 전 | Filter 후 | 감소율 |
|--------|----------|----------|--------|
| w_0003 | 2,273 | 267 | **88%** |
| w_0007 | 5,182 | 367 | **93%** |
| w_0010 | 2,655 | 348 | **87%** |

---

#### [6] 개별 구멍 추출
```python
x, y, bw, bh = cv2.boundingRect(cnt)
hole_region = image[y:y+bh, x:x+bw].copy()

# 마스크 적용 (배경을 흰색으로)
hole_extracted = hole_region.copy()
hole_extracted[hole_mask_small == 0] = [255, 255, 255]
```

**처리 과정**:
1. 구멍의 bounding box 계산
2. 원본 이미지에서 해당 영역만 잘라냄
3. 구멍 부분만 남기고 배경은 흰색으로 채움

---

#### [7] y좌표 역순 정렬
```python
# y좌표 역순 정렬 (아래→위)
holes = sorted(holes, key=lambda h: h['bbox'][1], reverse=True)
# ID 재할당
for i, hole in enumerate(holes):
    hole['id'] = i
```

**정렬 기준**: y좌표 (역순)
- hole_0000: y좌표 가장 큼 (맨 아래)
- hole_0001: y좌표 두 번째 큼
- ...
- hole_last: y좌표 가장 작음 (맨 위)

**목적**: 일관된 ID 부여

---

## 파라미터 결정 과정

### 1. Method 선택: lab_b vs lab_hsv

**테스트 결과**:
- `lab_hsv` (AND 연산): Coverage 18.45%
- `lab_b` (단독): Coverage 32.40% ⭐

**결론**: **lab_b 선택**
- 더 많은 영역 검출
- 구멍만 정확히 포착

---

### 2. Threshold 결정: Percentile vs Fixed

#### Percentile 방식 (--s-percentile)
```bash
--s-percentile 33  # 가장 흰색인 33% 픽셀
```

**장점**: 이미지에 자동 적응
**단점**: 이미지마다 다른 threshold

**test_small 결과**:
- p=33 → b=140 자동 계산 → 258개 구멍

**w_0005 결과**:
- p=30~35 → 모두 b=144 → 18,920개 구멍 ⚠️ (너무 많음!)

**문제**: 변색된 문서에서는 실패!

---

#### Fixed Threshold (--s-threshold)
```bash
--s-threshold 138  # 고정값
```

**장점**:
- 모든 이미지에 동일한 기준
- 재현성 완벽
- 물리적 의미 명확

**test_small 결과**: 254개 구멍
**w_0005 결과**: 239개 구멍

**결론**: **고정 b=138 선택** ⭐⭐⭐

---

### 3. Threshold 값 선택: 130~140 비교

| Threshold | test_small | w_0005 | 평가 |
|-----------|-----------|--------|------|
| b=130 | 61개 | 6,287개 | ❌ 극단적 |
| b=132 | 401개 | 1,505개 | ⚠️ 많음 |
| b=135 | 241개 | 249개 | ✅ 균형 |
| b=136 | 245개 | 208개 | ✅ 비슷 |
| b=137 | 251개 | 221개 | ✅ 비슷 |
| **b=138** | **254개** | **239개** | ✅✅ **최적!** |
| b=140 | 258개 | 877개 | ⚠️ w_0005 많음 |

**선택 이유**:
- test_small과 w_0005에서 **거의 동일한 개수** (254 vs 239)
- 일관성 최고
- 두 이미지 모두 적당한 개수

---

### 4. min-area 설정: 10 pixels

```bash
--min-area 10
```

**의미**: 10 pixels 미만은 노이즈로 판단

**효과**:
- w_0007: 853개 → 367개 (486개 제외)
- 작은 점 노이즈 효과적 제거

**권장**: **10** (너무 높이면 작은 구멍 놓침)

---

### 5. max-area 설정: 100000 → 200000

**문제 발견**:
- w_0001: 최대 구멍 **71,158 px** (100k 미만이지만 큼)
- w_0010: 최대 구멍 **73,984 px** (100k 미만이지만 큼)

**해결**: `--max-area 200000` ⭐⭐⭐

**이유**:
- 큰 구멍도 포함
- 100k로는 제한적
- 20만으로 충분한 여유

---

## 다중 이미지 테스트 결과

### 전체 비교표

| 이미지 | 크기 | 평균 b값 | Coverage | 구멍 개수 | 최대 구멍 | 총 손상 면적 | 평가 |
|--------|------|---------|----------|----------|----------|-------------|------|
| **test_small.jpg** | 1443x1082 | 141.7±7.6 | 32.40% | 254 | 2,477 px | 23,764 px (1.52%) | ✅ 기준 |
| **w_0001.tif** | 7216x5412 | 141.6±7.9 | 32.70% | 335 | **71,158 px** | 753,494 px (1.93%) | ✅ 큰 구멍 |
| **w_0003.tif** | 7216x5412 | 143.8±6.6 | 15.56% | 267 | 49,840 px | 411,886 px (1.05%) | ✅ 적당 |
| **w_0005.tif** | 7216x5412 | 144.1±6.7 | 15.89% | 239 | 17,676 px | 252,193 px (0.65%) | ✅ 적당 |
| **w_0007.tif** | 7216x5412 | 143.5±6.0 | 14.28% | 367 | 61,350 px | 429,198 px (1.10%) | ✅ 적당 |
| **w_0010.tif** | 7216x5412 | 138.2±8.0 | 52.91% | 348 | **73,984 px** | 431,252 px (1.10%) | ⚠️ threshold 근접 |
| **w_0015.tif** | 7216x5412 | 144.9±5.7 | 11.36% | 163 | 49,955 px | 211,946 px (0.54%) | ✅ 가장 변색 |
| **w_0018.tif** | 5412x7216 | 137.8±8.5 | 51.93% | **2,626** | 4,872 px | 140,263 px (0.36%) | ❌ 과검출 |

---

### 이미지 분류

#### ✅ 그룹 A: 깨끗한 배경 (b≈141-142)
- **test_small.jpg** (b=141.7)
- **w_0001.tif** (b=141.6)

**특징**:
- Coverage 높음 (32%대)
- 구멍 254-335개
- b=138 최적

---

#### ✅ 그룹 B: 변색된 배경 (b≈143-145)
- **w_0003.tif** (b=143.8)
- **w_0005.tif** (b=144.1)
- **w_0007.tif** (b=143.5)
- **w_0015.tif** (b=144.9)

**특징**:
- Coverage 낮음 (11-16%)
- 구멍 163-367개
- 배경이 노란색으로 변색
- b=138로 정확히 구분 가능

---

#### ⚠️ 그룹 C: 심각한 손상 (b≈137-138)
- **w_0010.tif** (b=138.2, Coverage 52.91%)
- **w_0018.tif** (b=137.8, Coverage 51.93%)

**특징**:
- 평균 b값이 threshold에 근접
- Coverage 50%대 (절반 이상 손상!)
- b=138로는 과검출 가능

**권장**: b=135 사용

---

### b값과 Coverage의 관계

```
평균 b값          Coverage    구멍 개수
──────────────────────────────────────
137.8 (w_0018)    51.93%      2,626    ❌
138.2 (w_0010)    52.91%        348    ⚠️
141.6 (w_0001)    32.70%        335    ✅
141.7 (test)      32.40%        254    ✅
143.5 (w_0007)    14.28%        367    ✅
143.8 (w_0003)    15.56%        267    ✅
144.1 (w_0005)    15.89%        239    ✅
144.9 (w_0015)    11.36%        163    ✅
```

**패턴**:
- b평균 < 138: 과검출 (전체가 손상)
- b평균 ≈ 140-142: Coverage 높음 (32%대)
- b평균 ≈ 143-145: Coverage 낮음 (11-16%)

**결론**: **b=138은 b평균이 140 이상인 문서에 최적**

---

## Edge Detection 비교

### 테스트한 방법들

1. **Morphological Gradient**: Dilation - Erosion
2. **Canny Edge**: Gradient + Non-max suppression
3. **Sobel Edge**: X/Y 방향 gradient
4. **Direct Contours**: 기존 방법 (mask에서 직접)
5. **Enhanced Gradient**: Morphological gradient + Dilation

---

### 결과 비교

#### w_0003 (기존: 267개)
| 방법 | Contour 개수 | Direct 대비 |
|------|-------------|------------|
| Enhanced Gradient | 1,847 | **-19%** ✅ |
| Sobel | 2,067 | -9% |
| Morph Gradient | 2,138 | -6% |
| Direct (기존) | 2,273 | 기준 |
| Canny | 3,692 | +62% ⚠️ |

#### w_0007 (기존: 367개)
| 방법 | Contour 개수 | Direct 대비 |
|------|-------------|------------|
| Enhanced Gradient | 4,122 | **-20%** ✅ |
| Sobel | 4,577 | -12% |
| Morph Gradient | 4,740 | -9% |
| Direct (기존) | 5,182 | 기준 |
| Canny | 7,613 | +47% ⚠️ |

#### w_0010 (기존: 348개) ⚠️ 특이 케이스!
| 방법 | Contour 개수 | Direct 대비 |
|------|-------------|------------|
| **Direct (기존)** | **2,655** | **기준 (최소!)** ✅ |
| Enhanced Gradient | 2,916 | +10% ⚠️ |
| Sobel | 3,259 | +23% |
| Morph Gradient | 3,428 | +29% |
| Canny | 5,967 | +125% ⚠️ |

---

### 핵심 발견

#### 1. Enhanced Gradient 효과

**일반 문서** (w_0003, w_0007): 약 20% 감소 ✅
**심각한 손상** (w_0010): 오히려 10% 증가 ⚠️

**이유**:
- Enhanced Gradient는 큰 구멍의 경계를 여러 개로 분할
- Direct는 큰 구멍을 하나로 유지
- w_0010은 큰 구멍이 많아서 Direct가 더 효과적

---

#### 2. Size Filter의 중요성 ⭐⭐⭐

| 이미지 | Direct (filter 전) | 실제 (filter 후) | 감소율 |
|--------|-------------------|-----------------|--------|
| w_0003 | 2,273 | 267 | **88%** |
| w_0007 | 5,182 | 367 | **93%** |
| w_0010 | 2,655 | 348 | **87%** |

**결론**: **Size filter가 가장 중요한 역할!** (87-93% 감소)

---

#### 3. Canny는 비추천

모든 이미지에서 과검출:
- w_0003: +62%
- w_0007: +47%
- w_0010: +125%

**이유**: 작은 노이즈까지 검출

---

### 권장 사항

#### ✅ 일반 문서: 현재 방법 유지
```python
# Mask → Morph CLOSE → Morph OPEN → Contours → Size Filter
```

**이유**:
- Size filter가 87-93% 감소 (핵심!)
- 안정적이고 예측 가능
- Enhanced Gradient는 size filter 적용 후 차이 불명확

---

#### 💡 Enhanced Gradient: 선택적 테스트
```python
gradient = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, kernel)
gradient_thick = cv2.dilate(gradient, kernel, iterations=1)
```

**적용 조건**:
- 일반 문서에서만 (b평균 > 140)
- 심각한 손상 문서에는 비추천

---

#### ❌ Canny: 사용 안 함
모든 경우 과검출

---

## 사용법 및 예시

### 1. 단일 이미지 처리

```bash
python extract_whiteness_based.py \
  --input "datasets/test_small.jpg" \
  --output-dir "results/test_small_output" \
  --method lab_b \
  --s-threshold 138 \
  --min-area 10 \
  --max-area 200000
```

**출력**:
```
results/test_small_output/
├── comparison.png          # 원본 vs 구멍 표시
├── white_mask.png          # 이진 마스크
└── individual_holes/       # 개별 구멍 이미지
    ├── hole_0000_x390_y892_w23_h18_a287.png
    ├── hole_0001_x422_y890_w25_h23_a384.png
    └── ...
```

---

### 2. 배치 처리 (여러 이미지)

#### Windows (PowerShell)
```powershell
Get-ChildItem "datasets\1첩\*.tif" | ForEach-Object {
    $name = $_.BaseName
    python extract_whiteness_based.py `
      --input $_.FullName `
      --output-dir "results\${name}_b138" `
      --method lab_b `
      --s-threshold 138 `
      --min-area 10 `
      --max-area 200000
}
```

#### Linux/Mac (Bash)
```bash
for img in datasets/1첩/*.tif; do
    name=$(basename "$img" .tif)
    python extract_whiteness_based.py \
      --input "$img" \
      --output-dir "results/${name}_b138" \
      --method lab_b \
      --s-threshold 138 \
      --min-area 10 \
      --max-area 200000
done
```

---

### 3. 심각한 손상 문서 처리

```bash
# w_0010, w_0018 같은 경우
python extract_whiteness_based.py \
  --input "datasets/1첩/w_0010.tif" \
  --output-dir "results/w_0010_b135" \
  --method lab_b \
  --s-threshold 135 \    # 138 → 135로 낮춤
  --min-area 10 \
  --max-area 200000
```

---

### 4. Edge Detection 테스트

```bash
# 기존 결과의 mask로 edge detection 테스트
python test_edge_detection.py \
  "results/test_small_output/white_mask.png" \
  "edge_test_output"
```

**출력**:
```
edge_test_output/
├── comparison_edges.png       # Edge 방법 비교
├── comparison_contours.png    # Contour 결과 비교
├── 1_morphological_gradient.png
├── 2_canny_edges.png
├── 3_sobel_edges.png
└── ...
```

---

## 문제 해결

### Q1. 구멍이 너무 많이 검출됨

**원인**:
- Threshold가 너무 높음
- 배경이 너무 어둡거나 노란색

**해결**:
```bash
# b값을 낮춰서 더 엄격하게
--s-threshold 135  # 또는 132, 130
```

**확인 방법**:
```bash
# 여러 threshold 테스트
python extract_whiteness_based.py ... --s-threshold 135 --output-dir results/test_b135
python extract_whiteness_based.py ... --s-threshold 138 --output-dir results/test_b138
python extract_whiteness_based.py ... --s-threshold 140 --output-dir results/test_b140

# 각 결과의 comparison.png 비교
```

---

### Q2. 구멍을 놓침 (너무 적게 검출)

**원인**:
- Threshold가 너무 낮음
- min-area가 너무 큼

**해결**:
```bash
# b값을 높여서 더 관대하게
--s-threshold 140  # 또는 142, 145

# 또는 min-area 줄이기
--min-area 5  # 기본값 10 → 5
```

---

### Q3. 큰 구멍이 누락됨

**원인**: max-area가 너무 작음

**해결**:
```bash
# max-area 증가
--max-area 300000  # 또는 더 크게
```

**확인 방법**:
출력 로그에서 "Area range" 확인
```
Area range: 10 - 73984
```
→ 최대 구멍이 73,984 pixels이므로 max-area는 100,000 이상 필요

---

### Q4. 전체가 손상된 문서 (Coverage > 50%)

**증상**:
- Coverage 50% 이상
- 평균 b값이 threshold에 근접
- 구멍이 너무 많음

**예시**: w_0010 (b=138.2, 52.91%), w_0018 (b=137.8, 51.93%)

**해결**:
```bash
# Threshold를 크게 낮춤
--s-threshold 135  # 또는 130

# 또는 다른 방법 시도 (edge detection 등)
```

---

### Q5. 작은 노이즈가 많음

**원인**: min-area가 너무 작음

**해결**:
```bash
# min-area 증가
--min-area 20  # 또는 30
```

**확인 방법**:
출력 로그에서 "Excluded (size)" 확인
```
Total contours: 853
Valid holes: 367
Excluded (size): 486  ← 486개가 크기로 제외됨
```

---

## 파일 구조

### 코드 파일
```
extract_whiteness_based.py    # 메인 구멍 검출 스크립트
test_edge_detection.py        # Edge detection 테스트 스크립트
compare_masks.py              # Mask 비교 스크립트
```

### Worklog (문서)
```
worklog/
├── FINAL_SUMMARY_hole_detection_b138.md           # 이 문서 ⭐
├── current_pipeline_b138.md                       # 파이프라인 상세
├── what_are_b_and_p.md                            # b와 p 설명
├── 2025-10-29_FINAL_all_combinations_b138_p30_35.md
├── 2025-10-29_threshold_comparison_130_to_140.md
├── 2025-10-29_multiple_images_test_b138.md
├── 2025-10-29_edge_detection_comparison.md
└── 2025-10-29_edge_detection_better_testset.md
```

### 결과 디렉토리
```
results/
├── test_small_b138_maxarea200k/
│   ├── comparison.png
│   ├── white_mask.png
│   └── individual_holes/
├── w_0001_b138/
├── w_0003_b138/
├── w_0005_b138/
├── w_0007_b138/
├── w_0010_b138/
├── w_0015_b138/
└── w_0018_b138/

edge_test_small/
edge_test_w0003/
edge_test_w0005/
edge_test_w0007/
edge_test_w0010/
```

---

## 핵심 요약

### 최종 파라미터 ⭐⭐⭐
```bash
--method lab_b \
--s-threshold 138 \
--min-area 10 \
--max-area 200000
```

### 가장 중요한 것들
1. **b=138**: test_small과 w_0005에서 거의 동일한 개수 (254 vs 239)
2. **max-area=200000**: 큰 구멍 포함 (71k, 73k pixels)
3. **Size filter**: 87-93% contour 감소 (가장 중요!)

### 적용 대상
- **일반 문서** (b평균 > 140): b=138 ✅
- **심각한 손상** (b평균 ≈ 138): b=135 ⚠️

### 권장 방법
- **현재 파이프라인 유지** ✅
- **Enhanced Gradient**: 선택적 테스트 💡
- **Canny**: 사용 안 함 ❌

---

## 참고 자료

### 관련 문서
- `current_pipeline_b138.md`: 전체 파이프라인 상세 설명
- `what_are_b_and_p.md`: b-channel과 percentile 설명
- `2025-10-29_multiple_images_test_b138.md`: 8개 이미지 테스트 결과
- `2025-10-29_edge_detection_better_testset.md`: Edge detection 비교

### 확인해야 할 이미지
```
results/*/comparison.png          # 각 결과의 시각적 비교
edge_test_*/comparison_contours.png  # Edge detection 비교
```

### 명령어 치트시트
```bash
# 단일 이미지
python extract_whiteness_based.py --input IMAGE --output-dir OUTPUT --method lab_b --s-threshold 138 --min-area 10 --max-area 200000

# 배치 처리 (PowerShell)
Get-ChildItem "datasets\1첩\*.tif" | ForEach-Object { python extract_whiteness_based.py --input $_.FullName --output-dir "results\$($_.BaseName)_b138" --method lab_b --s-threshold 138 --min-area 10 --max-area 200000 }

# Edge detection 테스트
python test_edge_detection.py "results/OUTPUT/white_mask.png" "edge_test_output"
```

---

**마지막 업데이트**: 2025-10-29
**테스트 완료**: test_small, w_0001, w_0003, w_0005, w_0007, w_0010, w_0015, w_0018
**권장 파라미터**: b=138, min=10, max=200000
