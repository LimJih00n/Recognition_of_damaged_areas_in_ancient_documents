# Edge Detection 비교: Mask 기반 방법들

**작성일**: 2025-10-29
**목적**: mask 이미지에 edge detection을 적용하여 구멍 검출 개선

---

## 테스트한 방법들

### 1. Morphological Gradient
```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
gradient = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, kernel)
```
- **원리**: Dilation - Erosion = 경계선
- **장점**: 이진 이미지에 최적화
- **특징**: 깔끔한 edge

### 2. Canny Edge Detection
```python
canny = cv2.Canny(mask, 50, 150)
```
- **원리**: Gradient + Non-maximum suppression
- **장점**: 얇고 연속된 edge
- **단점**: 이진 이미지에서는 과검출 가능

### 3. Sobel Edge Detection
```python
sobelx = cv2.Sobel(mask, cv2.CV_64F, 1, 0, ksize=3)
sobely = cv2.Sobel(mask, cv2.CV_64F, 0, 1, ksize=3)
sobel_mag = np.sqrt(sobelx**2 + sobely**2)
```
- **원리**: X/Y 방향 gradient 계산
- **장점**: 방향성 정보 포함
- **특징**: Canny보다 두꺼운 edge

### 4. Direct Contours (기존 방법)
```python
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```
- **원리**: Mask에서 직접 윤곽선 찾기
- **장점**: 간단하고 빠름
- **현재 사용 중**

### 5. Enhanced Gradient (Gradient + Dilation)
```python
gradient = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, kernel)
gradient_thick = cv2.dilate(gradient, kernel, iterations=1)
```
- **원리**: Morphological gradient + 두껍게 만들기
- **장점**: 노이즈 감소, 연결된 구멍 통합
- **특징**: 가장 적은 contour 개수

---

## 전체 비교표

### test_small.jpg (b=138)
| 방법 | Contour 개수 | 차이 | 비고 |
|------|-------------|------|------|
| **기존 (size 필터 적용)** | **254** | - | ⭐ 현재 사용 |
| Direct (mask 직접) | 280 | +26 | - |
| Enhanced Gradient | 271 | +17 | ✅ 가장 적음 |
| Sobel | 279 | +25 | - |
| Morphological Gradient | 287 | +33 | - |
| Canny | 313 | +59 | ⚠️ 가장 많음 |

**주의**: Direct는 280개이지만, 실제 extract_whiteness_based.py는 254개
→ Morphological cleanup (CLOSE+OPEN) + size filtering이 적용됨

---

### w_0005.tif (b=138)
| 방법 | Contour 개수 | 차이 | 비고 |
|------|-------------|------|------|
| **기존 (size 필터 적용)** | **239** | - | ⭐ 현재 사용 |
| Enhanced Gradient | 1,258 | +1,019 | ✅ Direct보다 적음 |
| Sobel | 1,440 | +1,201 | - |
| Morphological Gradient | 1,489 | +1,250 | - |
| Direct (mask 직접) | 1,661 | +1,422 | - |
| Canny | 2,918 | +2,679 | ⚠️ 가장 많음 |

**주의**: Direct는 1,661개이지만, 실제는 239개
→ Morphological cleanup + size filtering이 핵심!

---

### w_0018.tif (심각한 손상, b=138)
| 방법 | Contour 개수 | 차이 | 비고 |
|------|-------------|------|------|
| **기존 (size 필터 적용)** | **2,626** | - | ⭐ 현재 사용 |
| **Enhanced Gradient** | **5,702** | +3,076 | ✅ 가장 적음! |
| Sobel | 9,530 | +6,904 | - |
| Morphological Gradient | 11,710 | +9,084 | - |
| Direct (mask 직접) | 16,284 | +13,658 | - |
| Canny | 36,572 | +33,946 | ⚠️ 너무 많음 |

**발견**: Enhanced Gradient가 16,284 → 5,702로 **65% 감소!**

---

## 핵심 발견

### 1. 기존 방법이 이미 효과적

**기존 방법** (extract_whiteness_based.py):
1. Mask 생성 (LAB b-channel threshold)
2. **Morphological cleanup** (CLOSE + OPEN)
3. Direct contours
4. **Size filtering** (min-area, max-area)

**결과**:
- test_small: 254개 (Direct 280개 → 254개)
- w_0005: 239개 (Direct 1,661개 → 239개)

**결론**: **Morphology + Size filter가 핵심!**

---

### 2. Enhanced Gradient의 효과

**w_0018 비교**:
- Direct: 16,284 contours
- Enhanced Gradient: 5,702 contours (**65% 감소**)

**이유**:
- Gradient를 dilation하면 작은 노이즈들이 연결됨
- 연결된 영역 = 하나의 contour
- 결과적으로 contour 개수 감소

**하지만**: size filter 적용 전이므로, 실제 효과는 확인 필요

---

### 3. Canny는 과검출

모든 이미지에서 가장 많은 contour:
- test_small: 313개 (Direct 280개 대비 +12%)
- w_0005: 2,918개 (Direct 1,661개 대비 +76%)
- w_0018: 36,572개 (Direct 16,284개 대비 +125%)

**이유**: Canny는 얇은 edge를 찾으므로 작은 노이즈도 검출

---

## Edge 이미지 비교

### 결과 위치
```
edge_test_small/
├── 0_original_mask.png           # 원본 mask
├── 1_morphological_gradient.png  # Morphological gradient
├── 1_morphological_gradient_contours.png
├── 2_canny_edges.png              # Canny edge
├── 2_canny_contours.png
├── 3_sobel_edges.png              # Sobel edge
├── 3_sobel_thresh.png
├── 3_sobel_contours.png
├── 4_direct_contours.png          # Direct (기존)
├── 5_gradient_thick.png           # Enhanced gradient
├── 5_gradient_thick_contours.png
├── comparison_edges.png           # Edge 비교 (2x3)
└── comparison_contours.png        # Contour 비교 (2x2)
```

**확인 필수**:
- `comparison_edges.png`: 각 edge detection 결과 비교
- `comparison_contours.png`: 각 방법의 contour 비교

---

## 실제 적용 가능성

### 방법 1: Enhanced Gradient를 기존 파이프라인에 추가

**현재** (extract_whiteness_based.py line 214-217):
```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)
```

**개선안**:
```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

# Option A: Enhanced Gradient 추가
gradient = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, kernel)
gradient_thick = cv2.dilate(gradient, kernel, iterations=1)
# gradient_thick를 mask로 사용

# Option B: 기존 방법 유지 (이미 효과적)
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)
```

---

### 방법 2: Edge 정보를 추가 필터로 활용

**아이디어**: Edge detection을 별도 필터로 사용

```python
# 1. 기존 방법으로 contours 찾기
contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 2. Edge detection으로 경계 확인
gradient = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, kernel)

# 3. Contour가 실제 edge와 얼마나 일치하는지 확인
for cnt in contours:
    # Edge와 겹치는 비율 계산
    # 비율이 낮으면 노이즈로 판단하여 제외
```

---

## 시각적 분석

### Edge Pixel 개수 비교 (w_0005)

```
Edge 종류          Edge Pixel 개수
─────────────────────────────────
Canny              68,641 px   (가장 적음)
Morph Gradient    128,873 px
Sobel             173,951 px   (가장 많음)
```

**의미**:
- Canny: 얇은 edge (pixel 수 적음)
- Sobel: 두꺼운 edge (pixel 수 많음)
- Morph Gradient: 중간 (균형)

---

### Contour 개수 변화 (w_0018)

```
방법                     Contour 개수
──────────────────────────────────────
Enhanced Gradient         5,702  ████
Sobel                     9,530  ███████
Morph Gradient           11,710  █████████
Direct (기존)            16,284  ████████████
Canny                    36,572  ████████████████████████████
```

**결론**: Enhanced Gradient가 노이즈 감소에 가장 효과적

---

## 권장 사항

### ✅ 현재 방법 유지 (1순위)

**이유**:
1. Morphological cleanup (CLOSE+OPEN)이 이미 효과적
2. Size filtering이 핵심 역할
3. 결과가 안정적 (254, 239개)

**현재 파이프라인**:
```
Mask → Morph CLOSE → Morph OPEN → Contours → Size Filter
```

---

### 💡 Enhanced Gradient 시도 (2순위)

**적용 대상**: w_0018 같은 심각한 손상 문서

**방법**:
```python
# Mask → Enhanced Gradient → Contours → Size Filter
gradient = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, kernel)
gradient_thick = cv2.dilate(gradient, kernel, iterations=1)
contours, _ = cv2.findContours(gradient_thick, cv2.RETR_EXTERNAL, ...)
```

**기대 효과**: 16,284 → 5,702 contours (65% 감소)

**주의**: Size filter 적용 후 실제 개수 확인 필요

---

### ❌ Canny는 비추천

**이유**:
- 모든 이미지에서 과검출
- 작은 노이즈까지 검출
- 이진 이미지에는 부적합

---

## 다음 단계

### 1. 결과 이미지 육안 확인
```
edge_test_small/comparison_contours.png
edge_test_w0005/comparison_contours.png
edge_test_w0018/comparison_contours.png
```

**확인 사항**:
- 각 방법이 찾은 contour의 품질
- 노이즈 제거 정도
- 실제 구멍 검출 정확도

---

### 2. Enhanced Gradient 실제 적용 (옵션)

**테스트 필요**:
- Enhanced Gradient + Size Filter
- 실제 구멍 개수 비교
- 품질 확인

**구현**:
```bash
# extract_whiteness_based.py에 --edge-method 옵션 추가
python extract_whiteness_based.py \
  --method lab_b \
  --s-threshold 138 \
  --min-area 10 \
  --max-area 200000 \
  --edge-method gradient  # 새 옵션
```

---

### 3. Hybrid 방법 (고급)

**아이디어**: Edge 정보를 필터로 활용

```python
# 1. 기존 방법으로 후보 찾기
contours = find_contours(mask_clean)

# 2. Edge detection으로 검증
gradient = morphological_gradient(mask)

# 3. Edge와 일치하는 contour만 유지
validated_contours = filter_by_edge_match(contours, gradient)
```

---

## 요약

### 핵심 발견
1. **기존 방법이 이미 효과적** (Morph + Size filter)
2. **Enhanced Gradient가 노이즈 감소에 효과적** (65% 감소)
3. **Canny는 과검출** (비추천)

### 권장
- **일반 문서**: 기존 방법 유지 ✅
- **심각한 손상**: Enhanced Gradient 시도 💡
- **Canny**: 사용 안 함 ❌

### 결과 확인
```
edge_test_small/comparison_contours.png
edge_test_w0005/comparison_contours.png
edge_test_w0018/comparison_contours.png
```

이 이미지들을 확인하고 어떤 방법이 가장 좋은지 육안으로 판단하세요!
