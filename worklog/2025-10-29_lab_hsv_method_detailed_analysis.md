# LAB+HSV 하이브리드 방법론 상세 분석 및 고도화 방안

**작성일**: 2025-10-29 16:35
**분석 대상**: `results/goodcase/lab_hsv_w0005/` 생성 방법

---

## 1. 알고리즘 개요

### 핵심 아이디어
```
구멍 = 흰색 배경 = LAB에서 b값 낮음 AND HSV에서 채도 낮음
얼룩/변색 = 베이지색 = LAB에서 b값 높음 OR HSV에서 채도 있음
```

**생성 스크립트**: `extract_whiteness_based.py --method lab_hsv`

**코드 위치**: `extract_whiteness_based.py:121-164`

---

## 2. 알고리즘 상세 분석

### Step 1: 두 가지 색공간 변환

#### (1) LAB 색공간 - b-channel 분석
```python
lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
L, a, b = cv2.split(lab)
```

**LAB b-channel의 의미**:
- **b축**: Blue(-) ↔ Yellow(+)
- **낮은 b값 (<128)**: 파란색/무채색/흰색
- **높은 b값 (>128)**: 노란색/베이지색
- **w_0005.tif 통계**: mean=144.1, std=6.7

**베이지 종이 vs 흰색 구멍 구분**:
```
베이지 종이: b ≈ 140-150 (노란 기미)
흰색 구멍:   b < 143 (p25, 파란 기미 또는 무채색)
```

#### (2) HSV 색공간 - Saturation 분석
```python
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
H, S, V = cv2.split(hsv)
```

**HSV Saturation의 의미**:
- **S=0**: 완전한 무채색 (회색/흰색/검은색)
- **S>0**: 채도 있음 (색깔 있음)
- **w_0005.tif 통계**: mean=49.9, std=20.9

**무채색 구분**:
```
베이지 종이: S ≈ 40-60 (약간의 채도)
흰색 구멍:   S < 46 (p25 이하, 낮은 채도)
```

### Step 2: Threshold 자동 계산

```python
# LAB b-channel threshold (percentile 기반)
b_thresh = int(np.percentile(b, s_percentile if s_percentile else 25))
# 기본값: p25 = 143

# HSV Saturation threshold (중간값 사용)
s_thresh_hsv = int(np.percentile(S, 50))
# 기본값: p50 (median)
```

**Percentile 방식의 장점**:
- 이미지마다 자동으로 threshold 조정
- 조명 조건, 스캔 품질에 강건함

### Step 3: 교집합(AND) 마스크 생성

```python
mask_lab = (b < b_thresh)          # LAB: 노란 기미 없음
mask_hsv = (S < s_thresh_hsv)      # HSV: 채도 낮음
white_mask = (mask_lab & mask_hsv) # AND: 둘 다 만족
```

**교집합 효과**:
```
LAB만:        20.45% 커버리지  → 베이지 변색 포함
HSV만:        15.15% 커버리지  → 회색 부분 포함
LAB AND HSV:  13.10% 커버리지  → 순수 흰색만 (교집합)
```

### Step 4: 개별 구멍 추출

```python
def extract_individual_holes(image, mask, min_area=50):
    # 1. Morphological Cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # 구멍 메우기
    mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)  # 노이즈 제거

    # 2. 윤곽선 추출
    contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 3. 크기 필터링
    for cnt in contours:
        if min_area <= cv2.contourArea(cnt) <= max_area:
            # Bounding box 추출
            x, y, w, h = cv2.boundingRect(cnt)
            # 개별 이미지 저장
```

---

## 3. 실제 실행 예시

### goodcase에 사용된 추정 명령어

```bash
# 방법 1: 기본 percentile (가장 가능성 높음)
python extract_whiteness_based.py \
  --input "datasets/test_image.tif" \
  --output-dir results/goodcase/lab_hsv_w0005 \
  --method lab_hsv \
  --min-area 50

# 내부 동작:
# - b threshold: p25 (자동 계산)
# - S threshold: p50 (중간값)
# - 교집합으로 순수 흰색만 추출
```

### 예상 출력
```
=== Whiteness Detection: lab_hsv ===
  b (yellowness): 144.1 ± 6.7
  S (saturation): 49.9 ± 20.9
  V (value): 218.0 ± 13.3
  b threshold: < 143 (p25)
  S threshold: < 50 (p50)
  LAB mask: 20.45%
  HSV mask: 15.15%
  Combined (AND): 13.10%

Total contours: 12487
Valid holes: 231
Area range: 100 - 13721
Average: 674.9
Median: 243.5
Total: 155907 pixels (0.40%)
```

---

## 4. 강점 및 약점 분석

### ✅ 강점

#### 1. 이중 검증 (Dual Validation)
- LAB b-channel: 베이지 vs 흰색 구분
- HSV S-channel: 채도 vs 무채색 구분
- **교집합**: 두 조건 모두 만족 → False Positive 감소

#### 2. 자동 Threshold
- Percentile 기반 → 이미지마다 자동 조정
- 조명/스캔 품질 변화에 강건

#### 3. 직관적 해석
- b < 143: "노란 기미가 적음"
- S < 50: "채도가 낮음"
- → 명확한 물리적 의미

### ⚠️ 약점

#### 1. 과소 감지 (Under-detection)
```
LAB+HSV Combined: 0.40% 손상
LAB 단독:         3.76% 손상

→ 95% 이상의 실제 구멍을 놓침!
```

**원인**:
- 교집합(AND)은 매우 보수적
- 실제 구멍이 완전한 "순수 흰색"이 아닐 수 있음
- 약간의 베이지 기미나 채도가 있으면 제외됨

#### 2. HSV Saturation의 한계
```
HSV S-channel은 조명에 민감:
- 그림자 영역: 밝기 낮음 → S 계산 부정확
- 과노출 영역: 밝기 높음 → S가 인위적으로 낮아짐
```

#### 3. 고정된 Percentile
```python
s_thresh_hsv = int(np.percentile(S, 50))  # 항상 p50 사용
```
- 이미지 특성에 따라 p50이 최적이 아닐 수 있음
- 구멍이 많은 이미지 vs 적은 이미지에서 다른 결과

#### 4. V (Value) 미사용
```python
# HSV에서 V(밝기)를 사용하지 않음
# 단지 S(채도)만 확인
```
- 구멍 = "채도 낮음 + 밝음" 이어야 하는데
- 현재는 채도만 확인 → 어두운 무채색(그림자)도 포함될 위험

---

## 5. 고도화 방안

### 개선 1: 합집합(OR) 옵션 추가

**현재 (AND)**:
```python
white_mask = (mask_lab & mask_hsv)  # 교집합: 매우 엄격
```

**제안 (OR 옵션)**:
```python
if mode == 'strict':
    white_mask = (mask_lab & mask_hsv)  # 순수 흰색만
elif mode == 'loose':
    white_mask = (mask_lab | mask_hsv)  # 둘 중 하나라도
elif mode == 'weighted':
    # LAB 우선, HSV는 보조
    white_mask = mask_lab.copy()
    white_mask[mask_hsv] = True  # HSV도 추가
```

**효과**:
- strict: 0.40% (현재, False Positive 최소)
- loose: 20-25% (False Positive 증가)
- weighted: 3-5% 예상 (균형)

### 개선 2: HSV V(밝기) 조건 추가

**제안**:
```python
# 현재
mask_hsv = (S < s_thresh_hsv)

# 개선
v_thresh = int(np.percentile(V, 75))  # 상위 25%
mask_hsv = (S < s_thresh_hsv) & (V > v_thresh)

# 의미: 채도 낮고 + 밝음 = 진짜 흰색
```

**효과**:
- 어두운 그림자 영역 제거
- 구멍(밝음)과 검은 얼룩(어두움) 구분

### 개선 3: Adaptive Percentile

**현재**:
```python
b_thresh = int(np.percentile(b, 25))      # 고정 p25
s_thresh_hsv = int(np.percentile(S, 50))  # 고정 p50
```

**제안**:
```python
def adaptive_percentile(channel, target_coverage=0.15):
    """
    목표 커버리지(예: 15%)를 달성하는 percentile 자동 탐색
    """
    for p in range(5, 50, 5):
        thresh = np.percentile(channel, p)
        coverage = (channel < thresh).sum() / channel.size
        if coverage >= target_coverage:
            return thresh, p
    return np.percentile(channel, 25), 25

b_thresh, b_p = adaptive_percentile(b, target_coverage=0.15)
print(f"Adaptive b threshold: {b_thresh} (p{b_p})")
```

**효과**:
- 구멍이 많은/적은 이미지 자동 대응
- 목표 커버리지 기반 → 일관된 결과

### 개선 4: LAB L(밝기) 활용

**제안**:
```python
# LAB L-channel 추가 (밝기 정보)
L_thresh = int(np.percentile(L, 75))
mask_lab = (b < b_thresh) & (L > L_thresh)

# 의미: 노란 기미 없고 + 밝음 = 흰색 구멍
```

**효과**:
- 어두운 베이지 얼룩 제거
- 밝은 구멍만 선택

### 개선 5: 지역 적응형 Threshold (Local Adaptive)

**제안**:
```python
def local_adaptive_threshold(channel, block_size=51, C=2):
    """
    이미지를 블록으로 나누어 각 지역마다 다른 threshold 적용
    조명이 불균일한 경우 유용
    """
    mean_local = cv2.blur(channel.astype(float), (block_size, block_size))
    mask = channel < (mean_local - C)
    return mask.astype(np.uint8) * 255
```

**효과**:
- 조명 불균일 대응
- 그림자 영역에서도 구멍 감지 가능

### 개선 6: Morphological Enhancement

**현재**:
```python
# 기본적인 Open/Close만 사용
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)
```

**제안**:
```python
def advanced_cleanup(mask, min_hole_size=50):
    # 1. Close: 구멍 내부 작은 점 제거
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)

    # 2. Remove small components
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < min_hole_size:
            mask[labels == i] = 0

    # 3. Open: 가는 연결 제거
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)

    return mask
```

**효과**:
- 노이즈 더욱 깔끔하게 제거
- 구멍 형태 더욱 정확

### 개선 7: Edge 정보 추가 (Hybrid++)

**제안**:
```python
# LAB + HSV + Edge 세 가지 결합
def lab_hsv_edge_hybrid(image, edge_weight=0.3):
    # 1. LAB+HSV 마스크
    mask_color = detect_lab_hsv(image)

    # 2. Edge detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 40, 120)

    # 3. 색상 후보 중 명확한 경계가 있는 것만
    contours, _ = cv2.findContours(mask_color, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    mask_final = np.zeros_like(mask_color)
    for cnt in contours:
        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue

        # 윤곽선을 따라 edge coverage 계산
        mask_temp = np.zeros_like(mask_color)
        cv2.drawContours(mask_temp, [cnt], -1, 255, 2)
        overlap = cv2.bitwise_and(mask_temp, edges)
        edge_coverage = np.sum(overlap > 0) / perimeter

        # Edge coverage가 충분하면 포함
        if edge_coverage > edge_weight:
            cv2.drawContours(mask_final, [cnt], -1, 255, -1)

    return mask_final
```

**효과**:
- 명확한 경계 있는 구멍만 선택
- 흐릿한 변색 영역 제거

---

## 6. 권장 개선 우선순위

### 🔴 우선순위 1: HSV V(밝기) 추가 (즉시 적용 가능)
```python
mask_hsv = (S < s_thresh_hsv) & (V > v_thresh)
```
- **구현 난이도**: ⭐ (매우 쉬움)
- **효과**: ⭐⭐⭐⭐ (큰 개선 예상)
- **위험도**: 낮음

### 🟠 우선순위 2: LAB L(밝기) 추가
```python
mask_lab = (b < b_thresh) & (L > L_thresh)
```
- **구현 난이도**: ⭐ (매우 쉬움)
- **효과**: ⭐⭐⭐⭐ (큰 개선 예상)
- **위험도**: 낮음

### 🟡 우선순위 3: 합집합/교집합 모드 선택
```python
--combine-mode [strict|balanced|loose]
```
- **구현 난이도**: ⭐⭐ (쉬움)
- **효과**: ⭐⭐⭐⭐⭐ (매우 유연해짐)
- **위험도**: 낮음

### 🟢 우선순위 4: Adaptive Percentile
- **구현 난이도**: ⭐⭐⭐ (중간)
- **효과**: ⭐⭐⭐ (일관성 향상)
- **위험도**: 중간 (튜닝 필요)

### 🔵 우선순위 5: Local Adaptive
- **구현 난이도**: ⭐⭐⭐⭐ (어려움)
- **효과**: ⭐⭐⭐ (특수 케이스에 유용)
- **위험도**: 높음 (복잡도 증가)

---

## 7. 즉시 적용 가능한 개선 코드

### 새 파일: `extract_whiteness_enhanced.py`

```python
def detect_whiteness_enhanced(image, method='lab_hsv_enhanced',
                             b_percentile=25, s_percentile=25,
                             v_percentile=75, l_percentile=75,
                             combine_mode='balanced'):
    """
    Enhanced LAB+HSV detection with brightness conditions

    Args:
        combine_mode: 'strict' (AND), 'balanced' (LAB primary), 'loose' (OR)
    """

    if method == 'lab_hsv_enhanced':
        # LAB 변환
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        L, a, b = cv2.split(lab)

        # HSV 변환
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        H, S, V = cv2.split(hsv)

        # Thresholds
        b_thresh = int(np.percentile(b, b_percentile))
        l_thresh = int(np.percentile(L, l_percentile))
        s_thresh = int(np.percentile(S, s_percentile))
        v_thresh = int(np.percentile(V, v_percentile))

        print(f"  b < {b_thresh} (p{b_percentile})")
        print(f"  L > {l_thresh} (p{l_percentile})")
        print(f"  S < {s_thresh} (p{s_percentile})")
        print(f"  V > {v_thresh} (p{v_percentile})")

        # Enhanced masks with brightness
        mask_lab = (b < b_thresh) & (L > l_thresh)  # 노란기 없고 밝음
        mask_hsv = (S < s_thresh) & (V > v_thresh)  # 채도 낮고 밝음

        # Combine based on mode
        if combine_mode == 'strict':
            white_mask = (mask_lab & mask_hsv)  # 교집합
        elif combine_mode == 'balanced':
            # LAB 기본, HSV로 필터링
            white_mask = mask_lab.copy()
            # HSV가 반대하는 영역은 제거
            white_mask[~mask_hsv & (S > s_thresh * 1.5)] = False
        elif combine_mode == 'loose':
            white_mask = (mask_lab | mask_hsv)  # 합집합

        white_mask = white_mask.astype(np.uint8) * 255

        lab_cov = mask_lab.sum() / mask_lab.size * 100
        hsv_cov = mask_hsv.sum() / mask_hsv.size * 100
        final_cov = (white_mask > 0).sum() / white_mask.size * 100

        print(f"  LAB (b+L): {lab_cov:.2f}%")
        print(f"  HSV (S+V): {hsv_cov:.2f}%")
        print(f"  Combined ({combine_mode}): {final_cov:.2f}%")

        return white_mask, {'b': b, 'L': L, 'S': S, 'V': V}
```

### 실행 예시

```bash
# Strict 모드 (현재와 유사, 하지만 V와 L 추가)
python extract_whiteness_enhanced.py \
  --input "datasets/1첩/w_0005.tif" \
  --output-dir results/enhanced_strict \
  --method lab_hsv_enhanced \
  --combine-mode strict \
  --min-area 50

# Balanced 모드 (권장)
python extract_whiteness_enhanced.py \
  --input "datasets/1첩/w_0005.tif" \
  --output-dir results/enhanced_balanced \
  --method lab_hsv_enhanced \
  --combine-mode balanced \
  --min-area 50

# Loose 모드 (민감하게)
python extract_whiteness_enhanced.py \
  --input "datasets/1첩/w_0005.tif" \
  --output-dir results/enhanced_loose \
  --method lab_hsv_enhanced \
  --combine-mode loose \
  --min-area 50
```

### 예상 결과 비교

| 모드 | 예상 구멍 수 | 예상 손상율 | 특징 |
|------|-------------|-----------|------|
| **현재 lab_hsv** | 231 | 0.40% | ⚠️ 과소 감지 |
| **Enhanced Strict** | 500-800 | 1.5-2.0% | L,V 조건 추가로 개선 |
| **Enhanced Balanced** | 1500-2500 | 2.5-3.5% | **권장: LAB 우선** |
| **Enhanced Loose** | 3000-4000 | 4.0-5.0% | ⚠️ 과다 감지 위험 |
| **LAB b 단독** | 12004 | 3.76% | 기준점 |

---

## 8. 결론 및 다음 단계

### 핵심 발견
1. **현재 lab_hsv는 너무 보수적**: 0.40% 손상 (95% 이상 놓침)
2. **교집합(AND)의 함정**: 엄격하지만 실제 구멍도 많이 제외
3. **V와 L 미사용**: 밝기 정보 활용 안 함 → 어두운 영역 포함 위험

### 즉시 적용 권장
```python
# 최소 개선 (5줄 추가)
l_thresh = int(np.percentile(L, 75))
v_thresh = int(np.percentile(V, 75))
mask_lab = (b < b_thresh) & (L > l_thresh)
mask_hsv = (S < s_thresh) & (V > v_thresh)
# 나머지 동일
```

### 다음 단계
1. **Enhanced 버전 구현** (우선순위 1-3)
2. **세 가지 모드 비교 실험**
3. **시각적 검증** (결과 이미지 확인)
4. **최적 파라미터 튜닝**
5. **다른 이미지에도 적용하여 일반화 성능 확인**

---

## 참고: 핵심 코드 위치

- **원본 lab_hsv**: `extract_whiteness_based.py:121-164`
- **개별 구멍 추출**: `extract_whiteness_based.py:205-273`
- **시각화**: `extract_whiteness_based.py:284-301`
