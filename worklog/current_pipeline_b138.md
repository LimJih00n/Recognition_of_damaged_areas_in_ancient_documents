# 현재 적용되는 전체 로직 (b=138)

**작성일**: 2025-10-29
**최종 파라미터**: `--method lab_b --s-threshold 138 --min-area 10`

---

## 전체 처리 파이프라인

```
입력 이미지
    ↓
[1] LAB 색공간 변환
    ↓
[2] b-channel threshold (b<138)
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

## 단계별 상세 설명

### [1] LAB 색공간 변환 (line 28-29)

**목적**: BGR(OpenCV 기본) → LAB 색공간으로 변환

```python
lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
L, a, b = cv2.split(lab)
```

**LAB 색공간**:
- **L**: Lightness (명도) 0~100
- **a**: Green(-) ↔ Red(+)
- **b**: Blue(-) ↔ Yellow(+) ← **우리가 사용**

**왜 LAB인가?**
- RGB는 밝기와 색상이 섞여있음
- LAB는 명도(L)와 색상(a,b)이 분리됨
- b-channel만으로 노란색/흰색 구분 가능

---

### [2] b-channel Threshold (line 34-41)

**목적**: b<138인 픽셀을 흰색(구멍)으로 판단

```python
b_thresh = 138  # 고정값
white_mask = (b < b_thresh).astype(np.uint8) * 255
```

**결과**: 이진 마스크 (binary mask)
- 255 (흰색): b<138인 픽셀 = 구멍
- 0 (검은색): b≥138인 픽셀 = 종이

**예시**:
```
원본 이미지의 b값:
[120, 135, 138, 140, 145, 150, ...]

threshold b=138 적용:
[255, 255, 255,   0,   0,   0, ...]
 구멍  구멍  구멍  종이  종이  종이
```

---

### [3] Morphological Operations (line 214-217)

**목적**: 마스크를 깔끔하게 정리 (노이즈 제거 + 작은 구멍 채우기)

```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
mask_clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, kernel)
```

**적용되는 연산**:

#### (1) MORPH_CLOSE (닫기)
```
Before:  ██  ██    After:  ██████
         ██  ██            ██████

목적: 작은 구멍이나 틈을 메움
효과: 끊어진 영역을 연결
```

#### (2) MORPH_OPEN (열기)
```
Before:  ██████    After:  ██████
         ██  ██            ██████
          ██

목적: 작은 점 노이즈 제거
효과: 튀어나온 작은 점들 제거
```

**커널 크기**: 3x3 타원형
- 작은 크기 → 미세한 조정만
- 큰 크기 → 더 많이 변형

**현재 설정**: 3x3 (보수적)

---

### [4] Contour Detection (line 230)

**목적**: 흰색 영역(구멍)의 윤곽선 찾기

```python
contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

**파라미터**:
- `RETR_EXTERNAL`: 외곽 윤곽선만 (구멍 안의 구멍은 무시)
- `CHAIN_APPROX_SIMPLE`: 윤곽선 단순화 (메모리 절약)

**결과**: 각 구멍의 윤곽선 좌표 리스트

---

### [5] Size Filtering (line 237-241)

**목적**: 너무 작거나 큰 구멍 제외

```python
area = cv2.contourArea(cnt)
if area < min_area or area > max_area:
    excluded += 1
    continue
```

**현재 설정**:
- `min_area = 10` pixels (10픽셀 미만 제외)
- `max_area = 100000` pixels (10만 픽셀 초과 제외)

**예시**:
```
구멍 면적: [5, 15, 50, 100, 200, 150000]
min=10, max=100000 적용:
제외     ✅   ✅   ✅   ✅    제외
```

---

### [6] 개별 구멍 추출 (line 252-265)

**목적**: 각 구멍을 개별 이미지로 추출

```python
# Bounding box 계산
x, y, bw, bh = cv2.boundingRect(cnt)

# 해당 영역 추출
hole_region = image[y:y+bh, x:x+bw].copy()

# 마스크 적용 (배경을 흰색으로)
hole_extracted = hole_region.copy()
hole_extracted[hole_mask_small == 0] = [255, 255, 255]
```

**처리 과정**:
1. 구멍의 bounding box 계산 (x, y, width, height)
2. 원본 이미지에서 해당 영역만 잘라냄
3. 구멍 부분만 남기고 배경은 흰색으로 채움

**결과**: 각 구멍의 개별 이미지

---

### [7] y좌표 역순 정렬 (line 366-370)

**목적**: 일관된 ID 부여 (아래→위 순서)

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

**왜?**: 원본 lab_hsv_test_small과 동일한 방식

---

## 사용되지 않는 옵션들

### Border Margin (line 246-250)
```python
if border_margin > 0:  # 현재 0 → 사용 안 함
    # 이미지 가장자리 근처 구멍 제외
```
**현재**: 사용 안 함 (border_margin=0)

### Enhance Holes (line 220-228)
```python
if enhance_holes:  # 현재 False → 사용 안 함
    # Dilation으로 구멍 확장
    # Closing으로 내부 점 제거
```
**현재**: 사용 안 함 (enhance_holes=False)

---

## 현재 명령어 분석

```bash
python extract_whiteness_based.py \
  --method lab_b \
  --s-threshold 138 \
  --min-area 10
```

**적용되는 로직**:
- ✅ LAB 변환
- ✅ b<138 threshold
- ✅ Morphology (CLOSE + OPEN, 3x3)
- ✅ Contour 검출
- ✅ Size filter (10~100000 pixels)
- ✅ 개별 구멍 추출
- ✅ y좌표 역순 정렬

**적용 안 되는 로직**:
- ❌ Border margin (가장자리 필터)
- ❌ Enhance holes (구멍 강조)

---

## 각 단계의 파라미터

### 조정 가능한 파라미터

| 파라미터 | 현재 값 | 설명 | 영향 |
|----------|---------|------|------|
| **s-threshold** | 138 | b-channel 임계값 | ⭐ 가장 중요 |
| **min-area** | 10 | 최소 구멍 크기 | 작은 노이즈 제거 |
| **max-area** | 100000 | 최대 구멍 크기 | 큰 영역 제외 |
| **morphology kernel** | 3x3 | 정리 정도 | 코드 수정 필요 |
| **enhance-holes** | False | 구멍 강조 | 사용 안 함 |
| **border-margin** | 0 | 가장자리 제외 | 사용 안 함 |

### 고정된 로직

| 로직 | 값/방법 | 설명 |
|------|---------|------|
| 색공간 | LAB | 코드에 고정 |
| Morphology | CLOSE + OPEN | 코드에 고정 |
| Contour 방식 | RETR_EXTERNAL | 코드에 고정 |
| 정렬 | y좌표 역순 | 코드에 추가됨 |

---

## 조정 가능한 부분

### 1. b threshold 변경
```bash
--s-threshold 135  # 더 엄격 (적게 검출)
--s-threshold 138  # 현재 ⭐
--s-threshold 140  # 더 관대 (많이 검출)
```

### 2. 최소 크기 변경
```bash
--min-area 5   # 더 작은 구멍도 포함
--min-area 10  # 현재 ⭐
--min-area 20  # 작은 노이즈 더 제거
```

### 3. 가장자리 제외 (필요시)
```bash
--border-margin 10  # 가장자리 10px 이내 제외
```

### 4. 구멍 강조 (필요시)
```bash
--enhance-holes  # 구멍 확장 + 내부 정리
```

---

## 코드 수정이 필요한 부분

### Morphology 커널 크기 변경

**현재** (line 215):
```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
```

**더 강하게 정리하려면**:
```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
```

**효과**:
- 3x3: 미세한 정리 (현재)
- 5x5: 더 많이 정리 (큰 노이즈 제거)
- 7x7: 매우 강하게 (구멍 모양 변형 가능)

---

## 요약

### 핵심 로직 (순서대로)

1. **LAB 변환** → b-channel 추출
2. **Threshold b<138** → 이진 마스크 생성
3. **Morphology** → 노이즈 정리 (3x3 CLOSE+OPEN)
4. **Contour 검출** → 각 구멍 윤곽선 찾기
5. **Size 필터** → 10~100000 pixels만
6. **개별 추출** → 각 구멍 이미지 생성
7. **y좌표 정렬** → 아래에서 위로 ID 부여

### 가장 중요한 파라미터

**b=138** ⭐⭐⭐
- 전체 파이프라인의 시작점
- 이 값으로 구멍/종이를 구분
- 나머지는 모두 후처리

### 추가 조정 가능

- min-area: 더 작은/큰 값으로
- border-margin: 가장자리 제외
- enhance-holes: 구멍 강조
- morphology 커널: 코드 수정 필요
