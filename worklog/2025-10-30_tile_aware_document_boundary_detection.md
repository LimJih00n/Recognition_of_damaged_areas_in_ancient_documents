# 타일 스캔 이미지를 위한 문서 경계 감지

**작성일**: 2025-10-30

---

## 목차
1. [프로젝트 배경](#프로젝트-배경)
2. [문제 정의](#문제-정의)
3. [해결 과정](#해결-과정)
4. [구현된 기능](#구현된-기능)
5. [최종 결과](#최종-결과)
6. [코드 설명](#코드-설명)
7. [사용법](#사용법)

---

## 프로젝트 배경

### 기존 시스템
- **목적**: 고문서(조선시대 문서)의 구멍/손상 자동 감지
- **방법**: LAB 색공간의 b-channel을 사용하여 흰색 구멍 감지
  - 구멍(손상): b < 138 (흰색, 파란 톤)
  - 종이(정상): b ≥ 138 (베이지색, 노란 톤)

### 새로운 요구사항
고해상도 스캔 시 발생하는 문제들:
1. **스캔 배경 포함**: 이미지에 문서 외부의 흰색 배경 포함
2. **가장자리 손상**: 문서 가장자리가 찢어지거나 손상됨
3. **배경 연결 문제**: 손상된 가장자리가 배경과 연결되어 전체 배경이 "구멍"으로 감지됨
4. **타일 스캔**: 큰 문서를 여러 개의 타일 이미지로 분할해서 스캔

→ **해결책 필요**: 자동으로 문서 경계를 감지하여 배경을 제외하고, 타일 이어지는 부분도 처리

---

## 문제 정의

### 문제 1: 스캔 배경 포함
```
[배경(흰색)]  [문서(베이지)]  [배경(흰색)]
     ↓              ↓              ↓
  b < 138      b ≥ 138         b < 138
   (구멍?)       (종이)          (구멍?)
```
- 배경도 b < 138이므로 "구멍"으로 잘못 감지됨

### 문제 2: 가장자리 손상 + 배경 연결
```
[배경] ← [손상된 가장자리] ← [문서]
         (연결되어 있음!)
```
- 가장자리 손상이 배경과 연결되어 있으면
- 전체 배경이 하나의 거대한 "구멍"으로 감지됨

### 문제 3: 타일 스캔
```
┌─────────┬─────────┬─────────┐
│ Tile 1  │ Tile 2  │ Tile 3  │  ← 하나의 큰 문서를
├─────────┼─────────┼─────────┤     여러 타일로 분할
│ Tile 4  │ Tile 5  │ Tile 6  │
└─────────┴─────────┴─────────┘
```

**예시: test_small.jpg**
```
[배경] [문서 왼쪽(손상)] [문서 중앙] → [계속됨]
                                      ↓
        타일 경계선                    다음 타일로 이어짐
```

**각 변의 특성:**
- **왼쪽/위쪽**: 실제 문서 가장자리 (손상됨) → 정확히 감지 필요
- **오른쪽/아래쪽**: 다른 타일과 이어지는 부분 → 이미지 끝까지 확장 필요

---

## 해결 과정

### 시도 1: L-channel (밝기) 기반 감지 ❌

**방법**:
```python
# L-channel으로 문서 감지
L_channel = LAB[:,:,0]
threshold = Otsu(L_channel)
```

**문제**:
- 스캔 배경도 밝고 (L ≈ 230)
- 문서 종이도 밝아서 (L ≈ 210)
- 구분이 안됨
- 바운더리를 너무 크게 잡음

**사용자 피드백**:
> "바운더리를 너무 크게 잡았고... 베이지색을 기준으로 봐야할 듯 한디"

---

### 시도 2: b-channel (노란색) 기반 감지 ✓

**방법**:
```python
# b-channel으로 문서 감지 ⭐
b_channel = LAB[:,:,2]
threshold, mask = cv2.threshold(b_channel, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
```

**원리**:
```
배경(흰색):   b ≈ 128 (중립, 무채색)
문서(베이지): b ≈ 140+ (노란색, 베이지색)

→ Otsu threshold ≈ 139
→ b > 139인 영역 = 문서
```

**결과**: ✅ 문서와 배경 구분 성공!

---

### 시도 3: 4-코너 사각형 방식 ❌

**방법**:
```python
# Convex hull로 4개 코너 찾기
hull = cv2.convexHull(contour)
approx = cv2.approxPolyDP(hull, epsilon, True)
# 4개 점으로 사각형 생성
```

**문제**:
- 문서 가장자리가 불규칙하게 손상됨
- 4개 코너로 단순화하면 손상 부분을 제대로 포착 못함

**사용자 피드백**:
> "정사각이 아니라 상하좌우 측정해서 봐야한다"

---

### 시도 4: 독립적 변 감지 (percentile) ✓

**방법**:
```python
def find_edge_boundaries(contour, image_shape, percentile=2.0):
    points = contour.reshape(-1, 2)
    x_coords = points[:, 0]
    y_coords = points[:, 1]

    # 왼쪽 변: x좌표가 작은 5% 영역에서 percentile 계산
    left_candidates = x_coords[x_coords <= np.percentile(x_coords, 5)]
    x_min = int(np.percentile(left_candidates, percentile))

    # 오른쪽 변: x좌표가 큰 5% 영역에서 percentile 계산
    right_candidates = x_coords[x_coords >= np.percentile(x_coords, 95)]
    x_max = int(np.percentile(right_candidates, 100 - percentile))

    # 상단/하단도 동일하게
    ...
```

**원리**:
- 각 변(상하좌우)을 독립적으로 찾음
- percentile=2.0으로 작은 노이즈 무시
- 불규칙한 가장자리도 잘 포착

**결과**: ✅ 손상된 가장자리 정확히 감지!

---

### 시도 5: Morphology 커널 크기 조정

**초기 설정**:
```python
kernel_size = max(50, int(min(w, h) * 0.01))  # 이미지의 1%
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
doc_mask = cv2.morphologyEx(doc_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
doc_mask = cv2.morphologyEx(doc_mask, cv2.MORPH_OPEN, kernel, iterations=1)
```

**문제**:
- 커널이 너무 커서 경계가 안쪽으로 침식됨
- test_small: 50x50 → 가장자리 208px부터 시작 (너무 안쪽)

**사용자 피드백**:
> "가장자리를 측정할때 아주 작은 노이즈도 인식을 한거 같아"
> "약간 가장자리를 짜르고 있어"

**해결책**:
```python
# Close는 크게 (내부 구멍 메우기)
kernel_close = max(20, int(min(w, h) * 0.005))  # 0.5%
# Open은 작게 (경계 보존)
kernel_open = max(5, int(min(w, h) * 0.001))    # 0.1%

kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_close, kernel_close))
doc_mask = cv2.morphologyEx(doc_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_open, kernel_open))
doc_mask = cv2.morphologyEx(doc_mask, cv2.MORPH_OPEN, kernel, iterations=1)
```

**결과**:
- test_small: 193px부터 시작 (15px 더 바깥쪽)
- 가장자리 보존하면서 내부 구멍은 메움 ✅

---

### 시도 6: 타일 경계 감지 ⭐

**핵심 아이디어**:
```
타일 이미지는 4개 변 중:
- 일부는 "실제 문서 가장자리" (손상됨)
- 일부는 "다른 타일과 이어지는 부분"

이어지는 부분 = 이미지 끝까지 확장!
```

**구현 1: `detect_tiled_edges()`**
```python
def detect_tiled_edges(image, contour, margin_threshold=50):
    """타일 스캔에서 이어지는 변 vs 실제 가장자리 구분

    Returns:
        (is_left_edge, is_top_edge, is_right_edge, is_bottom_edge)
        True = 실제 가장자리, False = 이어지는 부분
    """
    h, w = image.shape[:2]
    points = contour.reshape(-1, 2)

    x_min = points[:, 0].min()
    x_max = points[:, 0].max()
    y_min = points[:, 1].min()
    y_max = points[:, 1].max()

    # 이미지 끝에서 margin 안에 있으면 "이어지는 부분"
    is_left_edge = x_min > margin_threshold
    is_top_edge = y_min > margin_threshold
    is_right_edge = (w - x_max) > margin_threshold
    is_bottom_edge = (h - y_max) > margin_threshold

    return is_left_edge, is_top_edge, is_right_edge, is_bottom_edge
```

**원리**:
```
실제 가장자리: 이미지 끝에서 멀리 떨어져 있음 (> 50px)
이어지는 부분: 이미지 끝에 바로 붙어있음 (< 50px)
```

**구현 2: 타일 경계 확장**
```python
def find_edge_boundaries(contour, image_shape, percentile=0.5, tile_edges=None):
    # ... 기본 경계 계산 ...

    # 타일 경계 정보가 있으면 확장
    if tile_edges is not None:
        is_left, is_top, is_right, is_bottom = tile_edges

        # 이어지는 부분은 이미지 끝까지 확장
        if not is_left:      # False = 이어지는 부분
            x_min = 0
        if not is_top:
            y_min = 0
        if not is_right:
            x_max = w - 1
        if not is_bottom:
            y_max = h - 1

    return (x_min, y_min, x_max - x_min, y_max - y_min)
```

**사용자 피드백**:
> "그 이어지는 곳은 완벽하게 측정했어"

**결과**: ✅ 타일 경계 완벽 처리!

---

### 시도 7: 바운더리 선 두께 조정

**초기 설정**:
```python
cv2.rectangle(vis_img, (x, y), (x+w, y+h), (255, 0, 0), 3)  # 두께 3px
```

**문제**: 선이 너무 두꺼워서 문서가 잘 안보임

**사용자 피드백**:
> "그 바운더리 선의 굵기만 낮춰주라!"

**해결책**:
```python
cv2.rectangle(vis_img, (x, y), (x+w, y+h), (255, 0, 0), 1)  # 두께 1px
```

**결과**: ✅ 얇은 선으로 문서 잘 보임!

---

## 구현된 기능

### 1. b-channel 기반 문서 감지
```python
def detect_document_boundary(image, method='brightness', corner_method='edges'):
    # LAB 색공간 변환
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    L, a, b_channel = cv2.split(lab)

    # Otsu threshold로 자동 임계값 계산
    b_thresh, doc_mask = cv2.threshold(
        b_channel, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Morphology 연산
    kernel_close = max(20, int(min(w, h) * 0.005))
    kernel_open = max(5, int(min(w, h) * 0.001))

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_close, kernel_close))
    doc_mask = cv2.morphologyEx(doc_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_open, kernel_open))
    doc_mask = cv2.morphologyEx(doc_mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # 가장 큰 contour 찾기
    contours, _ = cv2.findContours(doc_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_contour = max(contours, key=cv2.contourArea)

    # 사각형 경계 찾기
    boundary = find_robust_rectangle_from_contour(
        largest_contour, (h, w), corner_method, image=image
    )

    return boundary
```

### 2. 타일 경계 감지
```python
def detect_tiled_edges(image, contour, margin_threshold=50):
    """이미지 끝에서의 거리로 타일 경계 판단"""
    h, w = image.shape[:2]
    points = contour.reshape(-1, 2)

    x_min = points[:, 0].min()
    x_max = points[:, 0].max()
    y_min = points[:, 1].min()
    y_max = points[:, 1].max()

    is_left_edge = x_min > margin_threshold       # True = 실제 가장자리
    is_top_edge = y_min > margin_threshold
    is_right_edge = (w - x_max) > margin_threshold
    is_bottom_edge = (h - y_max) > margin_threshold

    return is_left_edge, is_top_edge, is_right_edge, is_bottom_edge
```

### 3. 독립적 변 감지 + 타일 확장
```python
def find_edge_boundaries(contour, image_shape, percentile=0.5, tile_edges=None):
    """각 변을 독립적으로 찾고, 타일 경계는 확장"""
    h, w = image_shape[:2]
    points = contour.reshape(-1, 2)
    x_coords = points[:, 0]
    y_coords = points[:, 1]

    # 왼쪽 변
    left_candidates = x_coords[x_coords <= np.percentile(x_coords, 5)]
    x_min = int(np.percentile(left_candidates, percentile))

    # 오른쪽 변
    right_candidates = x_coords[x_coords >= np.percentile(x_coords, 95)]
    x_max = int(np.percentile(right_candidates, 100 - percentile))

    # 상단 변
    top_candidates = y_coords[y_coords <= np.percentile(y_coords, 5)]
    y_min = int(np.percentile(top_candidates, percentile))

    # 하단 변
    bottom_candidates = y_coords[y_coords >= np.percentile(y_coords, 95)]
    y_max = int(np.percentile(bottom_candidates, 100 - percentile))

    # 타일 경계 정보가 있으면 확장
    if tile_edges is not None:
        is_left, is_top, is_right, is_bottom = tile_edges

        if not is_left:
            x_min = 0
        if not is_top:
            y_min = 0
        if not is_right:
            x_max = w - 1
        if not is_bottom:
            y_max = h - 1

    return (x_min, y_min, x_max - x_min, y_max - y_min)
```

### 4. 통합 파이프라인
```python
def find_robust_rectangle_from_contour(contour, image_shape, corner_method='edges', image=None):
    """Contour에서 사각형 경계 찾기"""
    h, w = image_shape[:2]

    if corner_method == 'edges':
        # 타일 경계 감지
        tile_edges = None
        if image is not None:
            tile_edges = detect_tiled_edges(image, contour, margin_threshold=50)
            is_left, is_top, is_right, is_bottom = tile_edges
            print(f"  Tile edge detection: left={is_left}, top={is_top}, "
                  f"right={is_right}, bottom={is_bottom}")

        # 변 감지 (타일 정보 전달)
        return find_edge_boundaries(contour, image_shape,
                                    percentile=0.5, tile_edges=tile_edges)
```

---

## 최종 결과

### test_small.jpg (1443x1082)

**타일 경계 감지**:
```
Left: real edge (dist from border: 193)
Right: continues to next tile (dist from border: 1)
Top: real edge (dist from border: 55)
Bottom: continues to next tile (dist from border: 1)
```

**경계 결과**:
```
Left:   x=193     (실제 가장자리 정확히 감지)
Right:  x=1442    (이미지 끝까지 확장 ✓)
Top:    y=55      (실제 가장자리 정확히 감지)
Bottom: y=1081    (이미지 끝까지 확장 ✓)
```

**구멍 감지**:
- 268개 구멍 검출
- 왼쪽 배경 제거 ✓
- 문서 내부 구멍만 정확히 검출 ✓

---

### w_0005.tif (7216x5412)

**타일 경계 감지**:
```
Left: real edge (dist from border: 762)
Right: continues to next tile (dist from border: 1)
Top: continues to next tile (dist from border: 0)
Bottom: continues to next tile (dist from border: 1)
```

**경계 결과**:
```
Left:   x=762     (실제 가장자리 정확히 감지)
Right:  x=7215    (이미지 끝까지 확장 ✓)
Top:    y=0       (이미지 끝까지 확장 ✓)
Bottom: y=5411    (이미지 끝까지 확장 ✓)
```

**구멍 감지** (최적 파라미터):
```bash
--min-area 50 --max-area 2500000
```
- 163개 구멍 검출
- 작은 노이즈(< 50px) 제거 ✓
- 큰 손상 영역(< 2.5M px) 포함 ✓
- 평균 크기: 12,619 pixels
- 중앙값: 1,131 pixels

---

## 코드 설명

### 파일 구조
```
extract_whiteness_based.py
├── detect_tiled_edges()              # 타일 경계 감지 (Line 326-361)
├── find_edge_boundaries()            # 독립적 변 감지 + 타일 확장 (Line 364-429)
├── find_robust_rectangle_from_contour()  # 사각형 찾기 (Line 432-520)
└── detect_document_boundary()        # 문서 경계 감지 (Line 643-734)
```

### 주요 함수

#### 1. `detect_tiled_edges(image, contour, margin_threshold=50)`
**목적**: 각 변이 실제 가장자리인지 타일 이어지는 부분인지 판단

**입력**:
- `image`: 원본 이미지
- `contour`: 문서 contour
- `margin_threshold`: 이미지 끝에서의 임계 거리 (기본 50px)

**출력**:
- `(is_left, is_top, is_right, is_bottom)`: 각각 True/False
  - `True`: 실제 가장자리 (이미지 끝에서 멀리 떨어짐)
  - `False`: 이어지는 부분 (이미지 끝에 붙어있음)

**로직**:
```python
# Contour의 최소/최대 좌표 찾기
x_min = contour의 최소 x좌표
x_max = contour의 최대 x좌표
y_min = contour의 최소 y좌표
y_max = contour의 최대 y좌표

# 이미지 끝에서의 거리 계산
left_dist = x_min - 0
right_dist = image_width - x_max
top_dist = y_min - 0
bottom_dist = image_height - y_max

# 거리가 threshold보다 크면 실제 가장자리
is_left_edge = (left_dist > margin_threshold)
...
```

---

#### 2. `find_edge_boundaries(contour, image_shape, percentile, tile_edges)`
**목적**: 각 변을 독립적으로 찾고, 타일 경계는 이미지 끝까지 확장

**입력**:
- `contour`: 문서 contour
- `image_shape`: (height, width)
- `percentile`: 노이즈 필터링 비율 (기본 0.5)
- `tile_edges`: 타일 경계 정보 (선택)

**출력**:
- `(x, y, w, h)`: 사각형 경계

**로직**:
```python
# 1단계: 각 변의 후보 점들 선택
left_candidates = x좌표가 작은 5% 영역의 점들
right_candidates = x좌표가 큰 5% 영역의 점들
top_candidates = y좌표가 작은 5% 영역의 점들
bottom_candidates = y좌표가 큰 5% 영역의 점들

# 2단계: Percentile로 노이즈 제거
x_min = left_candidates의 percentile 값
x_max = right_candidates의 (100-percentile) 값
y_min = top_candidates의 percentile 값
y_max = bottom_candidates의 (100-percentile) 값

# 3단계: 타일 경계 확장
if tile_edges is not None:
    if not is_left:   # 이어지는 부분
        x_min = 0
    if not is_right:
        x_max = width - 1
    if not is_top:
        y_min = 0
    if not is_bottom:
        y_max = height - 1
```

---

#### 3. `detect_document_boundary(image, method, corner_method)`
**목적**: b-channel 기반 문서 감지 및 경계 추출

**입력**:
- `image`: BGR 이미지
- `method`: 'brightness' (b-channel 사용)
- `corner_method`: 'edges' (독립적 변 감지)

**출력**:
- `(x, y, w, h)`: 문서 경계 사각형

**로직**:
```python
# 1. LAB 변환 및 b-channel 추출
lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
b_channel = lab[:,:,2]

# 2. Otsu threshold로 문서/배경 분리
threshold, mask = cv2.threshold(b_channel, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# 3. Morphology 연산
# Close (크게): 내부 구멍 메우기
kernel_close = 이미지 크기의 0.5%
mask = MORPH_CLOSE(mask, kernel_close)

# Open (작게): 노이즈 제거, 경계 보존
kernel_open = 이미지 크기의 0.1%
mask = MORPH_OPEN(mask, kernel_open)

# 4. 가장 큰 contour 찾기
contours = cv2.findContours(mask)
largest = max(contours, key=area)

# 5. 사각형 경계 추출 (타일 정보 포함)
boundary = find_robust_rectangle_from_contour(largest, image_shape,
                                              corner_method='edges',
                                              image=image)
```

---

### 파라미터 설명

#### 문서 경계 감지
- `--crop-document`: 문서 경계 감지 활성화
- `--corner-method edges`: 독립적 변 감지 방식 사용
- `--boundary-method brightness`: b-channel 기반 감지 (기본값)

#### Morphology 설정 (코드 내부)
- `kernel_close`: `max(20, min(w,h) * 0.005)` - 내부 구멍 메우기
- `kernel_open`: `max(5, min(w,h) * 0.001)` - 경계 보존
- `iterations`: 각 1회

#### 타일 감지 (코드 내부)
- `margin_threshold`: 50px - 이미지 끝에서의 거리 임계값
- `percentile`: 0.5 - 노이즈 필터링 비율

#### 구멍 감지
- `--method lab_b`: b-channel 기반 구멍 감지
- `--s-threshold 138`: b < 138인 픽셀을 구멍으로 판단
- `--min-area 50`: 50픽셀 미만 제거 (노이즈)
- `--max-area 2500000`: 2.5M 픽셀 이하만 포함 (초대형 제외)

---

## 사용법

### 기본 사용법
```bash
python extract_whiteness_based.py \
  --input datasets/test_small.jpg \
  --method lab_b \
  --s-threshold 138 \
  --min-area 50 \
  --max-area 2500000 \
  --crop-document \
  --corner-method edges \
  --output-dir results/output
```

### 고해상도 타일 이미지
```bash
python extract_whiteness_based.py \
  --input "datasets/1첩/w_0005.tif" \
  --method lab_b \
  --s-threshold 138 \
  --min-area 50 \
  --max-area 2500000 \
  --crop-document \
  --corner-method edges \
  --output-dir results/w_0005
```

### 출력 파일
- `document_boundary.png`: 문서 경계 시각화 (파란 선)
- `white_mask.png`: 구멍 마스크 (경계 적용 후)
- `white_mask_raw.png`: 구멍 마스크 (경계 적용 전)
- `comparison.png`: 원본 vs 구멍 검출 결과
- `individual_holes/`: 각 구멍별 이미지

---

## 핵심 개념 정리

### 1. LAB 색공간의 b-channel
```
b < 128: 파란색 계열
b = 128: 중립 (회색, 무채색)
b > 128: 노란색 계열

구멍(손상):  b < 138 (흰색, 약간 파란 톤)
종이(정상):  b ≥ 138 (베이지, 노란색)
```

### 2. 독립적 변 감지
```
전통적 방법: 4개 코너 찾기 → 사각형
  문제: 불규칙한 가장자리 못잡음

새 방법: 상하좌우 각 변을 독립적으로 찾기
  장점: 불규칙한 형태도 정확히 포착
```

### 3. Percentile 노이즈 필터링
```
percentile=0.5 의미:
  왼쪽 변 후보 100개 중 → 0.5번째 (최외곽)
  오른쪽 변 후보 100개 중 → 99.5번째 (최외곽)

효과: 1~2개 노이즈 점 무시, 실제 경계 정확히 포착
```

### 4. 타일 경계 확장
```
실제 가장자리:
  - 이미지 끝에서 50px 이상 떨어짐
  - percentile 방식으로 정확히 감지

이어지는 부분:
  - 이미지 끝에 바로 붙어있음 (< 50px)
  - 강제로 이미지 끝(0 또는 width-1)까지 확장
```

### 5. Morphology 전략
```
Close (큰 커널, 20x20):
  - 문서 내부의 작은 구멍 메우기
  - 문서 영역을 하나로 연결

Open (작은 커널, 5x5):
  - 외부 작은 노이즈 제거
  - 경계선은 최대한 보존
```

---

## 성능 비교

### test_small.jpg (1443x1082)

| 방법 | 구멍 개수 | 배경 제거 | 타일 처리 |
|-----|---------|---------|---------|
| 경계 없음 | 400+ | ❌ | ❌ |
| L-channel | 300+ | 부분적 | ❌ |
| b-channel + bbox | 277 | ✓ | ❌ |
| **b-channel + edges + tile** | **268** | **✓** | **✓** |

### w_0005.tif (7216x5412)

| 파라미터 | 구멍 개수 | 평균 크기 | 노이즈 |
|---------|---------|---------|--------|
| min=10, max=500k | 241 | 3,813 | 많음 |
| min=10, max=2.5M | 243 | 8,473 | 많음 |
| **min=50, max=2.5M** | **163** | **12,619** | **적음 ✓** |

---

## 문제 해결 요약

| 문제 | 해결책 | 결과 |
|-----|-------|------|
| 배경도 구멍으로 감지 | b-channel 기반 문서 감지 | ✅ 배경 제거 |
| 불규칙한 가장자리 | 독립적 변 감지 (percentile) | ✅ 정확한 경계 |
| 작은 노이즈 영향 | percentile=0.5, 작은 Open 커널 | ✅ 노이즈 필터링 |
| 타일 이어지는 부분 | 타일 경계 자동 감지 및 확장 | ✅ 완벽 처리 |
| 경계 안쪽으로 침식 | Close/Open 커널 크기 분리 | ✅ 경계 보존 |
| 바운더리 선 두꺼움 | 선 두께 3px → 1px | ✅ 가시성 향상 |

---

## 향후 개선 가능한 부분

1. **적응형 margin_threshold**
   - 현재: 고정 50px
   - 개선: 이미지 크기에 비례하여 자동 조정

2. **다중 문서 처리**
   - 현재: 가장 큰 contour 1개만 처리
   - 개선: 여러 문서 조각 모두 처리

3. **회전 보정**
   - 현재: axis-aligned rectangle만 지원
   - 개선: 회전된 문서 자동 보정

4. **파라미터 자동 튜닝**
   - 현재: min-area, max-area 수동 설정
   - 개선: 이미지 특성 기반 자동 추천

---

## 참고 자료

- **LAB 색공간**: `worklog/what_are_b_and_p.md`
- **구멍 검출 결과**: `worklog/FINAL_SUMMARY_hole_detection_b138.md`
- **해상도 스케일링**: `worklog/2025-10-30_resolution_scaling_and_svg_vector_export.md`

---

**작성자**: Claude Code
**날짜**: 2025-10-30
**프로젝트**: 고문서 손상 자동 검출 시스템
