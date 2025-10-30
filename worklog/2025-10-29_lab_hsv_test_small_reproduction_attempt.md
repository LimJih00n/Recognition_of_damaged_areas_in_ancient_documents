# lab_hsv_test_small 재현 시도 기록

**작성일**: 2025-10-29
**목표**: `results/goodcase/lab_hsv_test_small` 정확히 재현

---

## 원본 결과 분석

### 파일 생성 시간
- 생성 시각: **2025-10-29 16:20**
- extract_whiteness_based.py 수정 시각: **2025-10-29 16:19:53**
- → **코드 수정 직후 (1분 이내) 생성됨**

### 원본 특징
- **구멍 개수**: 229개
- **Coverage**: 32.63%
- **첫 구멍**: hole_0000_x422_y1078_w8_h4_a15.png
- **마지막 구멍**: hole_0228_x1427_y74_w13_h14_a120.png
- **정렬**: y좌표 내림차순 (아래→위, 1078 → 74)
- **마스크 특징**: 가장자리가 매우 깨끗함 (노이즈 없음)

---

## 재현 시도 과정

### 발견 1: 정렬 코드 누락
- 현재 코드에는 y좌표 정렬이 없음
- 원본은 y좌표 역순 정렬되어 있음
- **수정**: line 366-370에 정렬 코드 추가
```python
# y좌표 역순 정렬 (아래→위)
holes = sorted(holes, key=lambda h: h['bbox'][1], reverse=True)
# ID 재할당
for i, hole in enumerate(holes):
    hole['id'] = i
```

### 발견 2: 마스크 Coverage 불일치
- **lab_hsv method** (AND): 18.45% coverage → 원본보다 훨씬 적음
- **원본**: 32.63% coverage
- **결론**: lab_hsv (교집합)이 아닌 **다른 방법** 사용

### 발견 3: lab_b method + percentile 조정
다양한 percentile 테스트:

| Percentile | Coverage | 구멍 개수 | 비고 |
|-----------|----------|----------|------|
| p25 (기본값) | 18.45% | 232개 | 너무 적음 |
| p32 | 31.82% | 230개 | 개수 거의 일치 (+1) |
| **p33** | **32.91%** | **249개** | **Coverage 가장 근접** |
| p35 | 33.83% | 278개 | 너무 많음 |
| p40 | 37.57% | 424개 | 너무 많음 |

---

## 가장 근접한 파라미터: p33

### 실행 명령어
```bash
python extract_whiteness_based.py \
  --input "datasets/test_small.jpg" \
  --output-dir results/test_lab_b_p33 \
  --method lab_b \
  --s-percentile 33 \
  --min-area 15
```

### 결과
- **Coverage**: 32.91% (원본 32.63%, 차이 +0.28%)
- **구멍 개수**: 249개 (원본 229개, 차이 +20개)
- **b threshold**: < 140 (p33)
- **총 윤곽선**: 267개
- **제외됨 (크기)**: 18개
- **평균 면적**: 110.3 pixels
- **중간값 면적**: 64.5 pixels
- **총 손상 면적**: 27,466 pixels (1.76%)

### 비교
- ✅ **Coverage 매우 근접** (32.91% vs 32.63%)
- ⚠️ **개수 차이** (+20개)
- ❌ **첫 구멍 위치 다름** (확인 필요)

---

## 남은 문제

### 1. 구멍 개수 차이 (249 vs 229)
- 20개 차이 (약 8.7% 더 많음)
- min-area 조정으로 개수 맞출 수 있으나, 위치가 바뀔 수 있음

### 2. 첫 구멍 위치 불일치
- 원본: x422, y1078, area=15
- 재현 시도들: 모두 다른 위치부터 시작
- **마스크 자체가 미묘하게 다름**

### 3. 마스크 가장자리 노이즈
- 원본: 매우 깨끗한 가장자리 (큰 검은 영역)
- 재현: 가장자리 노이즈 많음
- **전처리나 후처리가 다를 가능성**

---

## 가능한 원인 가설

### 가설 1: 코드 변경
- 16:19 당시 코드와 현재 코드가 다름
- Morphology 파라미터나 로직 변경

### 가설 2: 다른 스크립트 사용
- extract_and_map_holes.py
- extract_holes_smart_filter.py
- 기타 스크립트

### 가설 3: 수동 편집
- 마스크를 수동으로 편집했을 가능성
- 후처리 필터링 추가

### 가설 4: 특수 파라미터 조합
- border-margin 사용
- enhance-holes 사용
- 기타 숨겨진 옵션

---

## 다음 단계

1. ✅ **정렬 코드 추가 완료**
2. ✅ **p33이 가장 근접한 파라미터 확인**
3. ⏳ **Codebase 전체 재검토 필요**
   - 모든 hole extraction 스크립트 확인
   - 유사한 출력 생성하는 스크립트 찾기
   - Morphology 파라미터 비교
4. ⏳ **마스크 생성 로직 상세 분석**
   - 전처리 과정
   - 후처리 과정
   - 경계 처리 방식

---

## 참고: 테스트한 모든 조합

### extract_whiteness_based.py 시도
1. lab_hsv + min-area=23: 232개 (18.45%)
2. lab_hsv + min-area=23 + max-area=8000: 229개 (18.45%) - 개수 일치하나 위치 다름
3. lab_hsv + enhance-holes: 291개 (18.45%)
4. lab_b + min-area=15: 319개 (18.45%)
5. lab_b + min-area=15 + p32: 230개 (31.82%)
6. **lab_b + min-area=15 + p33**: **249개 (32.91%)** ⭐ 가장 근접

### extract_and_map_holes.py 시도
1. min-area=23: 232개 (동일한 노이즈 패턴)
2. min-area=23 + exclude-border: 217개

### extract_holes_smart_filter.py 시도
1. min-area=23: 62개 (너무 적음)

---

## 핵심 발견

1. **lab_hsv가 아닌 lab_b method 사용**
2. **s-percentile=33 사용** (기본값 25가 아님)
3. **y좌표 역순 정렬 필요**
4. **마스크 생성 로직에 미묘한 차이 존재**

---

## 코드 수정 내역

### extract_whiteness_based.py
**Line 366-370 추가**:
```python
# y좌표 역순 정렬 (아래→위)
holes = sorted(holes, key=lambda h: h['bbox'][1], reverse=True)
# ID 재할당
for i, hole in enumerate(holes):
    hole['id'] = i
```

이 정렬 코드는 16:19 당시 코드에 있었으나 이후 제거되었을 가능성 높음.
