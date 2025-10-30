# 작업 로그 - 2025-10-28 색상 단순화 시도들

**작성 시간**: 2025-10-28 오후

## 목표
`results/svg/holes_improved_mask.png` (깨끗한 마스크)를 얻었으나, 놓친 작은 손상 부위들을 포함시키고 싶음.

## 문제점
- **holes_improved_mask.png**: Edge 기반이라 작은 점 군집을 놓침
- **simple threshold**: 모든 점을 감지하지만 문서에 퍼진 노이즈도 포함

## 시도한 방법들 (모두 실패)

### 1. 단순 임계값 + 색상 시각화 ❌

**파일**: `simple_threshold.py`

**접근**:
- L_enhanced에서 threshold=200으로 밝은 점 감지
- 문서=초록, 손상=흰색으로 색상 구분

**문제**:
- 문서 영역 전체에 노이즈 점들이 포함됨
- 결과: `results/simple/test_small_overlay.png`
- 평가: **모든 손상은 감지했으나 노이즈가 너무 많음**

```bash
python simple_threshold.py --input datasets/test_small.jpg --threshold 200
```

---

### 2. 면적 필터링 ❌

**파일**: `simple_threshold.py` (min-area 추가)

**접근**:
- 작은 영역(min-area < 100) 제거
- Contour 기반 필터링

**결과**:
- `results/simple_v3/`: 85개 영역 (min-area=100)
- `results/simple_v4/`: 85개 영역

**문제**:
- 작은 손상 군집도 제거됨
- 평가: **너무 많이 제거**

---

### 3. 밀집도(Density) 필터링 ❌

**파일**: `simple_threshold.py` (min-density 추가)

**접근**:
```python
density = area / bounding_box_area
if density >= min_density:
    valid
```

**시도한 값들**:
- `min-density=0.15`: 4.59%, 1,468개 영역 (results/simple_v11)
- `min-density=0.2`: 4.12% (results/simple_v9)
- `min-density=0.25`: 중간값 시도
- `min-density=0.3`: 1.69%, 394개 영역 (results/simple_v12) - **너무 많이 제거**

**문제**:
- 개별 contour의 밀집도만 봄
- 주변에 다른 점이 많은지는 판단 못함
- 평가: **실제 손상도 제거됨**

```bash
python simple_threshold.py --threshold 200 --min-area 1 --min-density 0.2
```

---

### 4. 공간적 밀집도 (KDTree + 이웃 개수) ❌

**파일**: `spatial_density_filter.py`

**접근**:
- 각 contour 중심점 계산
- KDTree로 반경 내 이웃 개수 카운트
- 이웃이 많으면 군집, 적으면 고립

**시도**:
- `radius=50, min-neighbors=50`: 13,218개 영역, 10.70% (results/spatial_v2)

**문제**:
- 평균 이웃 개수가 79.9개로 너무 높음
- 문서 영역도 충분히 밀집되어 있어서 구분 불가능
- 평가: **여전히 문서 영역에 노이즈 많음**

```bash
python spatial_density_filter.py --threshold 200 --radius 50 --min-neighbors 50
```

---

### 5. 큰 손상 주변 확장 ❌

**파일**: `extract_all_damage.py`

**접근**:
1. Edge 기반으로 큰 손상 찾기 (extract_holes_with_edges 방법)
2. 큰 손상 주변 N픽셀 확장
3. 확장된 영역 내의 모든 밝은 점 포함

**시도**:
- `expansion-radius=100`: 43개 큰 손상, 최종 6.11% (results/all_damage)

**문제**:
- 큰 손상에서 멀리 떨어진 작은 군집을 놓침
- **가운데 고립된 손상 영역**을 감지 못함
- 평가: **여전히 놓친 부분 많음**

```bash
python extract_all_damage.py --expansion-radius 100
```

---

### 6. DBSCAN 클러스터링 ❌

**파일**: `dbscan_damage.py`

**접근 1 - 픽셀 단위**:
- 모든 밝은 픽셀에 DBSCAN
- 밀집된 픽셀 클러스터만 남김

**문제**:
- `eps=30`: 1개 클러스터 (모두 연결됨)
- `eps=10`: 4개 클러스터 (여전히 거의 전부 연결)
- 픽셀들이 거의 연속적으로 분포되어 있어서 하나로 연결됨

**접근 2 - Contour 중심점 단위**:
- Contour 추출 → 중심점 계산 → DBSCAN
- 밀집된 contour 그룹만 남김

**시도**:
- `eps=50, min-samples=3`: 1개 클러스터 (results/dbscan_v3)
- `eps=50, min-samples=20`: 여전히 1개 클러스터 (results/dbscan_v4)

**문제**:
- 점들이 너무 고르게 분포되어 있어서 대부분이 하나의 클러스터로 연결
- 평가: **DBSCAN은 이 문제에 부적합**

```bash
python dbscan_damage.py --eps 50 --min-samples 3
```

---

## 결론

### ✅ 가장 좋은 방법

**extract_holes_with_edges.py** (`holes_improved_mask.png` 생성)

**장점**:
- 깨끗한 결과
- Edge 노이즈 0.19%
- 큰 손상 정확히 감지

**단점**:
- 작은 손상 군집 놓침 (특히 edge가 약한 것)

**알고리즘**:
1. CLAHE 전처리
2. Bilateral Filter (노이즈 제거 + edge 보존)
3. Canny Edge Detection
4. **이중 검증**:
   - Edge coverage ≥ 15%
   - 내부 평균 밝기 ≥ 170

**명령어**:
```bash
python extract_holes_with_edges.py \
  --input datasets/test_small.jpg \
  --output results/svg/holes_improved.svg \
  --threshold 210 \
  --edge-strength 40 \
  --simplify 0.5 \
  --min-area 50
```

**결과**:
- 파일: `results/svg/holes_improved_mask.png`
- 파일: `results/svg/holes_improved_preview.png`
- Edge 노이즈: 0.19%
- 구멍: 276개

---

## 왜 다른 방법들이 실패했나?

### 근본 원인
이 문제는 **손상 vs 노이즈**를 구분하기가 매우 어렵습니다:
- 밝기만으로는 불가능 (둘 다 밝음)
- 크기만으로도 불가능 (작은 손상 vs 작은 노이즈)
- 밀집도로도 불가능 (문서 전체에 점이 퍼져 있음)
- 공간 클러스터링도 불가능 (점들이 고르게 분포)

### Edge 기반 방법이 유일하게 작동하는 이유
**실제 손상**은 **명확한 경계(구멍)**가 있지만, **노이즈**는 경계가 불분명함.

---

## 다음 시도 방향

### 1. holes_improved 조건 완화
```python
# 기존 (엄격)
if edge_coverage > 0.15 or mean_brightness > 170:

# 개선 (관대)
if edge_coverage > 0.05 or mean_brightness > 190:
```

파라미터를 조정 가능하게 수정:
```bash
python extract_holes_with_edges.py \
  --edge-coverage 0.05 \
  --brightness-threshold 190 \
  --min-area 10
```

### 2. 두 마스크 결합
```python
# holes_improved (깨끗) + simple (모든 점) 결합
mask_final = holes_improved_mask | (simple_mask & damage_zone_mask)
```

### 3. 다른 edge detection 시도
- LoG (Laplacian of Gaussian)
- DoG (Difference of Gaussian)
- Sobel edge detection

---

## 생성된 결과물들

```
results/
├── simple/                      # 단순 threshold
│   └── test_small_overlay.png   # 모든 점 감지 (노이즈 많음)
├── simple_v3-v12/               # 면적/밀집도 필터링 시도들
├── spatial_v2/                  # KDTree 이웃 개수
├── all_damage/                  # 큰 손상 주변 확장
├── dbscan/                      # DBSCAN 시도들
└── svg/
    ├── holes_improved_mask.png     # ✅ 최고 결과
    └── holes_improved_preview.png
```

---

## 배운 점

1. **단순 threshold의 한계**: 밝기만으로는 손상/노이즈 구분 불가능
2. **밀집도의 한계**: 문서 전체에 점이 퍼져 있어서 밀집도로도 구분 어려움
3. **클러스터링의 한계**: 점들이 고르게 분포되어 있어서 DBSCAN 무용
4. **Edge detection이 핵심**: 실제 손상은 명확한 경계가 있음
5. **Trade-off**: 깨끗함 vs 완전성 (모든 손상 감지)

---

## 타임라인

- 14:00-15:00: 단순 threshold 시도 (`simple_threshold.py`)
- 15:00-16:00: 면적/밀집도 필터링 시도 (simple_v3-v12)
- 16:00-17:00: 공간적 밀집도 시도 (`spatial_density_filter.py`)
- 17:00-18:00: 큰 손상 주변 확장 (`extract_all_damage.py`)
- 18:00-19:00: DBSCAN 시도 (`dbscan_damage.py`)
- 19:00: 결론 - `holes_improved` 방법이 여전히 최고

---

## 참고

- 원본 worklog: `worklog/2025-10-28_hole_extraction.md`
- 최고 결과: `results/svg/holes_improved_mask.png`
- 원본 알고리즘: `extract_holes_with_edges.py`
