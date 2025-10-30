# 방법 비교 - 2025-10-28

## 문제 인식의 변화

### 초기 이해 (잘못됨)
- "구멍"만 찾으면 됨
- 구멍 = 밝은 영역
- 절대 밝기 threshold 사용

### 올바른 이해
- **"손상 부위"** 전체를 찾아야 함
  - 완전히 뚫린 구멍
  - 찢어진 부분
  - 해진 부분
  - 변색/오염
- **배경색이 불균일** (왼쪽 상단 더 어두움)
- **절대 밝기가 아닌 상대적 특징** 필요

## 시도한 방법들

### 1. Edge + Brightness (improved)
**파일**: `extract_holes_with_edges.py`

**접근**:
- 배경 불균일도 보정 (Gaussian blur)
- CLAHE (대비 향상)
- 밝기 threshold (210)
- Canny edge detection (40)
- Edge coverage 필터링 (13%)

**결과**:
- **감지 개수**: 276개
- **처리 시간**: ~2분 (Bilateral filter)
- **노이즈 경계**: 63개 (22.8%)
- **놓친 구멍**: ~4개 (수동 검토 기준)

**장점**:
- ✓ 깨끗한 결과
- ✓ 노이즈 적음
- ✓ 대부분의 구멍 감지

**단점**:
- ✗ 배경 진한 영역 놓침
- ✗ Bilateral filter 매우 느림
- ✗ 절대 밝기 의존

### 2. Morphological Gradient
**파일**: `extract_holes_gradient.py`

**접근**:
- Top-hat / Bottom-hat 배경 보정
- CLAHE (대비 향상)
- **Morphological gradient** (경계 강도 직접 측정)
- Adaptive threshold
- Gradient threshold (30)

**결과**:
- **감지 개수**: 570개
- **처리 시간**: ~1분
- **노이즈 경계**: 83개 (14.5%)
- **놓친 구멍**: 50개 (자동 분석, 과다추정)

**장점**:
- ✓ 경계 중심 접근
- ✓ 많이 감지

**단점**:
- ✗ Gradient threshold 조정 어려움
- ✗ 큰 영역 놓침
- ✗ 과검출
- ✗ 여전히 절대 gradient 크기 의존

### 3. Local Contrast (NEW)
**파일**: `detect_damage_local.py`

**접근**:
- **Multi-scale local contrast** (주변과 비교)
  - 11x11, 21x21, 31x31, 51x51 이웃
- **질감 분석** (Laplacian variance)
- Contrast + Texture 결합
- 통계 기반 자동 threshold

**핵심 아이디어**:
```python
# 절대 밝기가 아님
local_mean = cv2.blur(gray, (scale, scale))
contrast = gray - local_mean  # 주변과의 차이

# 배경 밝기와 무관
# 배경 어두워도 "주변보다 밝으면" 감지
```

**결과**:
- **감지 개수**: 923개
- **처리 시간**: **~10초** (매우 빠름!)
- **노이즈 경계**: 483개 (52.3%)
- **놓친 구멍**: 50개 (자동 분석)

**장점**:
- ✓ **매우 빠름** (Bilateral 없음)
- ✓ **배경 밝기 무관**
- ✓ 많이 감지
- ✓ Multi-scale (작은/큰 손상 모두)

**단점**:
- ✗ 노이즈 많음 (52.3%)
- ✗ 과검출 (글씨 주변도 감지?)

## 정량적 비교

| 지표 | Improved | Gradient | Local Contrast |
|------|----------|----------|----------------|
| **감지 개수** | 276개 | 570개 | 923개 |
| **처리 시간** | ~2분 | ~1분 | **~10초** |
| **노이즈 경계 비율** | 22.8% | 14.5% | 52.3% |
| **매끄러운 경계** | 71.7% | 26% | 22.3% |
| **Edge 노이즈** | 0.19% | - | - |

## 근본적 문제 분석

### 왜 파라미터 늪에 빠졌나?

**1. 절대값 의존**
- 밝기 threshold: 210
- Edge strength: 40
- Gradient threshold: 30

→ 한 영역에 맞추면 다른 영역 틀림

**2. 배경 불균일**
- 왼쪽 상단: 배경 ~190
- 중앙: 배경 ~207
- 단일 threshold로 불가능

**3. 전역 vs 지역**
- 전역 threshold: 배경 불균일 처리 못함
- Adaptive threshold: 노이즈 많음

### Local Contrast가 왜 다른가?

**상대적 비교**:
```python
# Before (절대값)
if brightness > 210:  # 고정 기준
    hole = True

# After (상대값)
if brightness > local_mean + threshold:  # 주변 기준
    damage = True
```

**배경 밝기와 무관**:
- 배경 어두운 곳: local_mean 낮음 → 구멍도 상대적으로 낮아도 감지
- 배경 밝은 곳: local_mean 높음 → 구멍도 높아야 감지

## 비교 이미지

생성된 파일:
- `results/comparison_three_methods.png` - 3가지 방법 시각적 비교
- `results/svg/holes_improved_preview.png` - Improved (276개)
- `results/svg/holes_gradient_preview.png` - Gradient (570개)
- `results/svg/damage_local_preview.png` - Local Contrast (923개)

## 다음 단계

### Option 1: Local Contrast 개선
**문제**: 노이즈 많음 (52.3%)

**개선 방향**:
1. **Edge 정보 추가** - 경계 명확한 것만 선택
2. **크기 필터링 강화** - 너무 작거나 큰 것 제외
3. **형태 필터링** - 원형도, 압축률
4. **Threshold 조정** - mean + 1.5*std → mean + 2.0*std (더 엄격)

### Option 2: Hybrid 접근
- Local contrast (후보 생성)
- + Edge validation (필터링)
- + 형태 검증 (최종 선택)

### Option 3: 수동 조정
- Improved (276개) 결과 사용
- 놓친 ~4개는 수동 보정

## 기술적 교훈

### 1. 문제 정의의 중요성
- "구멍" vs "손상 부위" - 완전히 다른 문제
- 초기에 잘못 이해하면 → 파라미터 늪

### 2. 절대값 vs 상대값
- 절대 밝기 → 배경 불균일에 취약
- 상대 대비 → 배경 무관

### 3. 속도 vs 정확도
- Bilateral filter: 고품질, 매우 느림
- Median blur: 적당한 품질, 빠름
- 단순 blur: 낮은 품질, 매우 빠름

### 4. Multi-scale의 힘
- 단일 크기: 작은 것 OR 큰 것
- Multi-scale: 작은 것 AND 큰 것

### 5. 과검출 vs 놓침
- 과검출: 후처리로 제거 가능
- 놓침: 복구 불가능
- → 일단 많이 감지하고 필터링하는 게 나음

## 파일 구조

```
riwum/
├── extract_holes_with_edges.py      # Improved (276개)
├── extract_holes_gradient.py        # Gradient (570개)
├── detect_damage_local.py           # Local Contrast (923개) ✨ NEW
├── compare_three_methods.py         # 비교 시각화
├── results/
│   ├── comparison_three_methods.png # 3-way 비교
│   ├── svg/
│   │   ├── holes_improved.svg
│   │   ├── holes_gradient.svg
│   │   └── damage_local.svg
│   └── analysis_local/              # Local 분석 결과
└── worklog/
    ├── 2025-10-28_hole_extraction.md
    ├── 2025-10-28_quality_analysis.md
    └── 2025-10-28_method_comparison.md  # 이 파일
```

## 권장사항

**단기 (지금 바로)**:
1. `results/comparison_three_methods.png` 확인
2. 어떤 방법이 실제 손상을 잘 찾았는지 시각적 검토
3. Local contrast 결과가 마음에 들면 → 노이즈 필터링 추가

**중기 (개선)**:
1. Local contrast + Edge validation 하이브리드
2. 형태 기반 필터링 (원형도, 크기)
3. 파라미터 자동 조정

**장기 (완성)**:
1. 배치 처리 (19개 이미지)
2. 수동 검증 및 보정
3. 최종 SVG 생성

## 결론

**핵심 발견**:
- 절대 밝기 → **상대 대비**로 전환이 핵심
- Local contrast는 **배경 불균일 문제 해결**
- 속도도 **10배 이상 빠름**

**남은 문제**:
- 노이즈 많음 (52.3%) → 필터링 필요
- 과검출 → Edge/형태 검증 추가

**다음 작업**:
- 사용자 피드백 기반 방향 결정
- Local contrast 개선 OR Hybrid 접근
