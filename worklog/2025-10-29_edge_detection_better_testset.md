# Edge Detection 비교: 더 나은 테스트 셋

**작성일**: 2025-10-29
**테스트 이미지**: w_0003, w_0007, w_0010 (w_0018 제외)

---

## 전체 비교표

### w_0003.tif (b=143.8, 기존: 267개)
| 방법 | Contour 개수 | Direct 대비 | 비고 |
|------|-------------|------------|------|
| **기존 (size 필터 적용)** | **267** | - | ⭐ 실제 결과 |
| Enhanced Gradient | 1,847 | -19% | ✅ 가장 적음 |
| Sobel | 2,067 | -9% | - |
| Morphological Gradient | 2,138 | -6% | - |
| **Direct (mask 직접)** | **2,273** | - | 기준 |
| Canny | 3,692 | +62% | ⚠️ 과검출 |

**패턴**: Enhanced Gradient < Sobel < Morph Gradient < Direct < Canny

---

### w_0007.tif (b=143.5, 기존: 367개)
| 방법 | Contour 개수 | Direct 대비 | 비고 |
|------|-------------|------------|------|
| **기존 (size 필터 적용)** | **367** | - | ⭐ 실제 결과 |
| Enhanced Gradient | 4,122 | -20% | ✅ 가장 적음 |
| Sobel | 4,577 | -12% | - |
| Morphological Gradient | 4,740 | -9% | - |
| **Direct (mask 직접)** | **5,182** | - | 기준 |
| Canny | 7,613 | +47% | ⚠️ 과검출 |

**패턴**: Enhanced Gradient < Sobel < Morph Gradient < Direct < Canny

---

### w_0010.tif (b=138.2, 기존: 348개) ⚠️
| 방법 | Contour 개수 | Direct 대비 | 비고 |
|------|-------------|------------|------|
| **기존 (size 필터 적용)** | **348** | - | ⭐ 실제 결과 |
| **Direct (mask 직접)** | **2,655** | - | ✅ 기준 (가장 적음!) |
| Enhanced Gradient | 2,916 | +10% | ⚠️ Direct보다 많음 |
| Sobel | 3,259 | +23% | - |
| Morphological Gradient | 3,428 | +29% | - |
| Canny | 5,967 | +125% | ⚠️ 과검출 |

**주목**: w_0010에서는 **Direct가 가장 적음!**

**패턴 변화**: Direct < Enhanced Gradient < Sobel < Morph Gradient < Canny

---

## 핵심 발견

### 1. w_0010의 특이 패턴 ⚠️

**다른 이미지들** (w_0003, w_0007):
```
Enhanced Gradient < Direct  (20% 감소)
```

**w_0010만**:
```
Direct < Enhanced Gradient  (10% 증가)
```

**원인 분석**:
- w_0010의 평균 b=138.2 (threshold 138에 매우 근접!)
- Coverage 52.91% (절반 이상 손상)
- 큰 구멍들이 많음 (최대 73,984 px)

**추론**:
- Enhanced Gradient는 큰 구멍의 경계를 여러 개로 분할할 수 있음
- Direct는 큰 구멍을 하나의 contour로 유지
- 심각한 손상 문서에서는 Direct가 더 효과적!

---

### 2. Enhanced Gradient의 효과

**일반 문서** (w_0003, w_0007):
```
Direct → Enhanced Gradient
2,273 → 1,847 (19% 감소) ✅
5,182 → 4,122 (20% 감소) ✅
```

**심각한 손상** (w_0010):
```
Direct → Enhanced Gradient
2,655 → 2,916 (10% 증가) ⚠️
```

**결론**:
- **일반 문서**: Enhanced Gradient 효과적
- **심각한 손상**: Direct가 더 나음

---

### 3. Size Filter의 역할 ⭐

모든 이미지에서 Direct → 실제 결과의 차이:

| 이미지 | Direct | 실제 | 감소율 | 비고 |
|--------|--------|------|--------|------|
| w_0003 | 2,273 | 267 | **88%** | ⭐⭐⭐ |
| w_0007 | 5,182 | 367 | **93%** | ⭐⭐⭐ |
| w_0010 | 2,655 | 348 | **87%** | ⭐⭐⭐ |

**발견**: Size filter가 **87-93% 감소** 효과!

**현재 파이프라인**:
```
Mask → Morph CLOSE → Morph OPEN → Contours → Size Filter (10~100k)
     → 실제 결과
```

**핵심**: **Size filter가 가장 중요한 역할!**

---

## 이미지별 상세 분석

### w_0003.tif (변색된 문서)

**특징**:
- 평균 b=143.8 (노란색으로 변색)
- Coverage 15.56% (적당)
- 구멍 267개

**Edge Detection 결과**:
```
Enhanced Gradient:  1,847  ████████████
Sobel:              2,067  ██████████████
Morph Gradient:     2,138  ██████████████▌
Direct:             2,273  ███████████████  (기준)
Canny:              3,692  ████████████████████████
```

**결론**: Enhanced Gradient가 19% 감소 효과

---

### w_0007.tif (많은 작은 구멍)

**특징**:
- 평균 b=143.5 (약간 변색)
- Coverage 14.28%
- 구멍 367개
- 총 윤곽선 853개 → 367개 (486개 제외됨)

**Edge Detection 결과**:
```
Enhanced Gradient:  4,122  ███████████████
Sobel:              4,577  █████████████████
Morph Gradient:     4,740  ██████████████████
Direct:             5,182  ████████████████████  (기준)
Canny:              7,613  ██████████████████████████████
```

**결론**: Enhanced Gradient가 20% 감소 효과

**주목**: 가장 많은 작은 노이즈 (486개 제외)

---

### w_0010.tif (심각한 손상) ⚠️

**특징**:
- 평균 b=138.2 (threshold에 매우 근접!)
- Coverage 52.91% (절반 이상 손상!)
- 구멍 348개
- 최대 구멍 73,984 px (매우 큼)

**Edge Detection 결과**:
```
Direct:             2,655  ███████████████  (기준, 가장 적음!)
Enhanced Gradient:  2,916  ████████████████▌
Sobel:              3,259  ██████████████████▌
Morph Gradient:     3,428  ███████████████████▌
Canny:              5,967  ██████████████████████████████████
```

**결론**: Direct가 가장 효과적!

**차이점**:
- w_0003, w_0007: Enhanced < Direct
- w_0010: Direct < Enhanced

**이유**:
- 큰 구멍들이 많음
- Enhanced Gradient는 큰 구멍의 경계를 여러 개로 나눔
- Direct는 큰 구멍을 하나로 유지

---

## Edge Pixel 개수 비교

### w_0003 (Coverage 15.56%)
```
Edge 종류          Edge Pixel 개수
──────────────────────────────────
Canny              70,958 px
Morph Gradient    131,018 px
Sobel             178,436 px
```

### w_0007 (Coverage 14.28%)
```
Edge 종류          Edge Pixel 개수
──────────────────────────────────
Canny             111,093 px
Morph Gradient    203,233 px
Sobel             274,916 px
```

### w_0010 (Coverage 52.91%)
```
Edge 종류          Edge Pixel 개수
──────────────────────────────────
Canny             106,506 px
Morph Gradient    201,941 px
Sobel             272,296 px
```

**패턴**:
- Canny: 가장 얇은 edge (pixel 적음)
- Morph Gradient: 중간
- Sobel: 가장 두꺼운 edge (pixel 많음)

**흥미로운 점**:
- w_0010 (Coverage 52.91%)과 w_0007 (Coverage 14.28%)의 edge pixel 개수가 비슷
- Coverage보다는 **contour의 복잡도**가 edge pixel 개수 결정

---

## 결과 디렉토리

```
edge_test_w0003/
├── comparison_edges.png           # Edge 비교
├── comparison_contours.png        # Contour 비교 ⭐ 확인 필수
└── ...

edge_test_w0007/
├── comparison_edges.png
├── comparison_contours.png        ⭐ 확인 필수
└── ...

edge_test_w0010/
├── comparison_edges.png
├── comparison_contours.png        ⭐ 확인 필수
└── ...
```

---

## 권장 사항

### ✅ 일반 문서 (b평균 > 140)

**현재 방법 유지 권장**:
```python
# Mask → Morph CLOSE → Morph OPEN → Contours → Size Filter
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)
contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
# + Size Filter (min=10, max=200000)
```

**이유**:
- Size filter가 87-93% 감소 효과 (가장 중요!)
- 안정적이고 예측 가능
- Enhanced Gradient는 약 20% 감소지만, size filter 적용 후 차이 불명확

**적용 대상**: w_0003, w_0007, w_0001, w_0005, w_0015 등

---

### ⚠️ 심각한 손상 (b평균 ≈ 138)

**Direct 방법 유지**:
```python
# Enhanced Gradient는 큰 구멍을 여러 개로 분할할 수 있음
# Direct가 더 효과적
```

**이유**:
- w_0010: Direct 2,655 < Enhanced 2,916
- 큰 구멍 유지에 유리

**적용 대상**: w_0010 (b=138.2, Coverage 52.91%)

---

### ❌ Canny 비추천

모든 이미지에서 과검출:
- w_0003: +62% (3,692 vs 2,273)
- w_0007: +47% (7,613 vs 5,182)
- w_0010: +125% (5,967 vs 2,655)

---

## 다음 단계

### 1. 육안 확인 필수 ⭐

**확인할 이미지**:
```
edge_test_w0003/comparison_contours.png
edge_test_w0007/comparison_contours.png
edge_test_w0010/comparison_contours.png
```

**확인 사항**:
- 각 방법이 찾은 contour의 품질
- 실제 구멍과 노이즈 구분
- 큰 구멍 처리 방식

---

### 2. Enhanced Gradient 실제 적용 (옵션)

**방법**: Size filter 포함하여 테스트

```python
# Enhanced Gradient + Size Filter
gradient = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, kernel)
gradient_thick = cv2.dilate(gradient, kernel, iterations=1)
contours, _ = cv2.findContours(gradient_thick, cv2.RETR_EXTERNAL, ...)

# Size filter 적용
for cnt in contours:
    area = cv2.contourArea(cnt)
    if area < 10 or area > 200000:
        continue
    # 유효한 구멍
```

**기대 결과**:
- w_0003: 1,847 → ??? (size filter 후)
- w_0007: 4,122 → ??? (size filter 후)
- w_0010: 2,916 → ??? (size filter 후)

**확인 필요**: size filter 적용 후 실제 구멍 개수

---

### 3. w_0010 특별 처리

**옵션 A**: b threshold 낮추기
```bash
--s-threshold 135  # 138 → 135
```

**옵션 B**: 현재 방법 유지
- Direct가 이미 효과적
- Size filter로 2,655 → 348개

---

## 요약

### 핵심 발견
1. **Size filter가 가장 중요** (87-93% 감소!)
2. **Enhanced Gradient**: 일반 문서에서 20% 감소
3. **w_0010 특이 케이스**: Direct가 더 효과적
4. **Canny 비추천**: 모든 경우 과검출

### 권장
- **일반 문서** (w_0003, w_0007): 현재 방법 유지 ✅
- **심각한 손상** (w_0010): Direct 유지 ✅
- **Enhanced Gradient**: 옵션으로 테스트 가능 💡
- **Canny**: 사용 안 함 ❌

### 결과 확인 필수
```
edge_test_w0003/comparison_contours.png
edge_test_w0007/comparison_contours.png
edge_test_w0010/comparison_contours.png
```

이 3개 이미지를 확인하고 어떤 방법이 실제로 구멍을 더 잘 찾는지 판단하세요!
