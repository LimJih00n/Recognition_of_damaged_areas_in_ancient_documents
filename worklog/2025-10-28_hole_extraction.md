# 작업 로그 - 2025-10-28 구멍 추출 작업

## 작업 개요
한국 고문서 이미지에서 **물리적 손상 부분(구멍, 찢어진 부분)** 을 정확하게 감지하여 SVG 벡터 포맷으로 변환

## 초기 문제 - 잘못된 이해

### 첫 번째 시도: 어두운 영역 추출 (실패)
- **잘못된 가정**: 어두운 부분(글씨, 그림)을 추출하려고 시도
- **결과**: 완전히 반대 - 실제로는 밝은 부분(구멍)을 추출해야 함
- **사용자 피드백**: "완전 이상해.. 구멍을 정확하게 찾고 모양도 따와야하는 상황"

### 원본 이미지 분석
- 베이지색 종이 배경
- 흰색/밝은 영역 = 구멍 (배경이 비침)
- 작은 점부터 큰 찢어진 부분까지 다양한 크기
- 가장자리 손상 (왼쪽, 위쪽)

## 해결 과정

### 1단계: 단순 밝기 기반 추출
**파일**: `extract_holes_to_svg.py`

```bash
# 첫 번째 시도
--threshold 200  # 너무 낮음
결과: 61.18% 영역이 구멍으로 인식 (과도함)

# 두 번째 시도
--threshold 230  # 너무 높음
결과: 14.92% 영역, 3,028개 구멍 (구멍을 놓침)
```

**문제점**:
- ❌ 단순 밝기만으로는 해진 부분과 구멍을 구분 못함
- ❌ 경계가 명확한 구멍만 선택하지 못함

### 2단계: Edge Detection 결합
**파일**: `extract_holes_with_edges.py`

**핵심 아이디어**:
1. 밝은 영역 찾기 (brightness threshold)
2. Canny edge detection으로 명확한 경계 찾기
3. **밝은 영역 중 경계가 명확한 것만 선택**

```python
# 윤곽선의 일정 % 이상이 edge와 겹치면 구멍으로 인정
edge_coverage = np.sum(overlap == 255) / perimeter
if edge_coverage > 0.3:  # 30% 이상
    valid_contours.append(contour)
```

**결과**:
- 304개 구멍 감지
- 하지만 여전히 놓친 구멍들 있음

### 3단계: 파라미터 최적화
**문제**:
- 노이즈가 많은 edge detection
- 완전 흰색이 아닌 구멍 놓침

**해결**:
1. **더 민감한 edge detection**: edge-strength 50→30
2. **낮은 brightness threshold**: 220→215
3. **더 정밀한 윤곽선**: simplify 2.0→0.5

```bash
--threshold 215
--edge-strength 30
--simplify 0.5
결과: 466개 구멍 (53% 증가)
```

### 4단계: 전처리 강화 ⭐ 최종 해결
**문제**:
- Edge 노이즈 많음
- 어두운 구멍 못 잡음

**해결책**:

#### 1) CLAHE 전처리 - 대비 향상
```python
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16, 16))
enhanced = clahe.apply(gray)
# 평균 밝기: 206.8 → 183.0 (대비 향상)
```

#### 2) 강한 노이즈 제거
```python
# Gaussian blur (9x9) + Bilateral filter (11, 100, 100)
blurred = cv2.GaussianBlur(enhanced, (9, 9), 2.0)
bilateral = cv2.bilateralFilter(blurred, 11, 100, 100)
edges = cv2.Canny(bilateral, edge_strength, edge_strength * 2)
```

#### 3) 구멍 내부 검증
```python
# 구멍 내부 평균 밝기 확인
hole_region = enhanced[hole_mask == 255]
mean_brightness = np.mean(hole_region)

# 평균이 170 이상이거나 edge coverage가 35% 이상이면 구멍
if mean_brightness > 170 or edge_coverage > 0.35:
    valid_contours.append(contour)
```

## 최종 결과 비교

| 버전 | Threshold | Edge강도 | Edge노이즈 | 구멍개수 | 평가 |
|------|-----------|----------|-----------|---------|------|
| holes_edge_based | 220 | 50 | 0.19% | 304개 | 기본 |
| holes_precise | 215 | 30 | 7.40% | 466개 | 노이즈많음 |
| **holes_improved** | **210** | **40** | **0.19%** | **276개** | **✅ 최고** |
| holes_final | 205 | 40 | 0.33% | 302개 | 양호 |

### 최적 설정 (holes_improved)

```bash
python extract_holes_with_edges.py \
  --input "datasets/test_image.tif" \
  --output "results/svg/holes_improved.svg" \
  --threshold 210 \
  --edge-strength 40 \
  --simplify 0.5 \
  --min-area 50
```

**성능**:
- Edge 노이즈: 0.19% (매우 깨끗)
- 구멍 개수: 276개
- 윤곽선 정밀도: 포인트 30.5% 감소
- 경계가 명확한 구멍만 선택

## 핵심 기술 정리

### 1. 전처리 파이프라인
```
원본 이미지
  ↓
CLAHE (대비 향상)
  ↓
Brightness Threshold (밝은 영역)
  ↓
Morphological Closing (구멍 내부 균일화)
```

### 2. Edge Detection 파이프라인
```
CLAHE 결과
  ↓
Gaussian Blur (9x9, sigma=2.0)
  ↓
Bilateral Filter (11, 100, 100)
  ↓
Canny Edge Detection
  ↓
Dilation (edge 확장)
```

### 3. 필터링 기준
- **Edge Coverage**: 윤곽선의 15% 이상이 edge와 겹침
- **내부 밝기**: 평균 170 이상 (CLAHE 적용 후 기준)
- **최소 면적**: 50 픽셀 이상

### 4. 윤곽선 단순화
```python
# Douglas-Peucker algorithm
epsilon = 0.5  # 매우 정밀
simplified = cv2.approxPolyDP(contour, epsilon, True)
# 결과: 30.5% 포인트 감소
```

## 파일 구조

```
riwum/
├── extract_holes_to_svg.py          # 1단계: 단순 밝기 기반 (실패)
├── extract_holes_with_edges.py      # 최종: Edge + 밝기 결합 ✅
├── datasets/
│   ├── test_image.tif               # 테스트 이미지 (7216x5412)
│   └── 1첩/                         # 나머지 18개 이미지
└── results/
    └── svg/
        ├── holes_improved.svg           # ✅ 최고 결과
        ├── holes_improved_preview.png   # 원본 + 빨간 윤곽선
        └── holes_improved_mask.png      # 구멍만 표시
```

## 처리 시간

- **CLAHE**: ~0.5초
- **Bilateral Filter**: ~15초 (가장 오래 걸림)
- **Edge Detection**: ~1초
- **윤곽선 추출 및 필터링**: ~2초
- **SVG 생성**: ~0.5초
- **총 처리 시간**: ~20초/이미지

## 다음 단계

### 1. 배치 처리
- [ ] `datasets/1첩/` 폴더의 나머지 18개 이미지 처리
- [ ] 모든 이미지에 동일한 파라미터 적용 (holes_improved 설정)

### 2. 품질 검증
- [ ] 각 이미지의 구멍 감지율 확인
- [ ] 놓친 구멍이나 오검출 수동 확인
- [ ] 필요시 이미지별 파라미터 미세 조정

### 3. 최적화 (선택사항)
- [ ] Bilateral filter 대신 다른 빠른 필터 시도
- [ ] 타일 기반 처리로 메모리 효율 개선
- [ ] GPU 가속 가능 여부 검토

## 배운 점

1. **단순 threshold의 한계**
   - 밝기만으로는 해진 부분과 구멍을 구분 불가
   - 경계 정보(edge)가 필수

2. **전처리의 중요성**
   - CLAHE로 대비 향상 → 어두운 구멍도 감지
   - Bilateral filter → 노이즈 제거하면서 edge 보존

3. **다중 검증 기준**
   - Edge coverage (경계 명확도)
   - 내부 밝기 (구멍 여부)
   - 최소 면적 (노이즈 제거)

4. **파라미터 밸런스**
   - Threshold 너무 높으면 → 구멍 놓침
   - Threshold 너무 낮으면 → 해진 부분까지 포함
   - Edge strength 너무 낮으면 → 노이즈 많음
   - Edge strength 너무 높으면 → 경계 놓침

## 기술 스택

- **Python**: 3.x
- **OpenCV**: 이미지 처리, Edge detection, 윤곽선 추출
- **NumPy**: 배열 연산, 통계 계산
- **xml.etree.ElementTree**: SVG 생성
- **xml.dom.minidom**: Pretty print

## 주요 알고리즘

1. **CLAHE**: Contrast Limited Adaptive Histogram Equalization
2. **Bilateral Filter**: Edge-preserving smoothing
3. **Canny Edge Detection**: Multi-stage edge detection
4. **Douglas-Peucker**: Polyline simplification
5. **Morphological Operations**: Opening, Closing

## 최종 명령어

```bash
# 최적 설정으로 단일 이미지 처리
python extract_holes_with_edges.py \
  --input "datasets/test_image.tif" \
  --output "results/svg/holes_improved.svg" \
  --threshold 210 \
  --edge-strength 40 \
  --simplify 0.5 \
  --min-area 50
```

## 참고 사항

- 원본 이미지 크기: 7216x5412 픽셀 (~39 MP)
- SVG 파일 크기: ~200-700KB (구멍 개수에 따라)
- 메모리 사용량: ~2-3GB (Bilateral filter)
- 권장 시스템: 8GB RAM 이상
