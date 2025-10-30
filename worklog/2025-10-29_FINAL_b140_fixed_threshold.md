# 최종 파라미터: 고정 b=140

**작성일**: 2025-10-29
**최종 결정**: 자동 threshold 대신 **고정 b=140** 사용

---

## 최종 권장 파라미터

```bash
python extract_whiteness_based.py \
  --method lab_b \
  --s-threshold 140 \
  --min-area 10
```

### 핵심 설정
- **method**: `lab_b` (LAB b-channel 단독)
- **s-threshold**: `140` (고정값, percentile 사용 안 함)
- **min-area**: `10` (최소 구멍 크기)
- **정렬**: y좌표 역순 (아래→위)

---

## 결과 비교 (b=140 고정값)

### test_small.jpg (1443 x 1082)

**출력**: `results/test_small_fixed_b140/`

**통계**:
- **b threshold**: < 140 (absolute, 고정)
- **White coverage**: 32.91%
- **총 윤곽선**: 267개
- **검출 구멍**: 258개
- **제외됨**: 9개
- **면적 범위**: 10 - 2,694 pixels
- **평균 면적**: 106.9 pixels
- **중간값 면적**: 62.2 pixels
- **총 손상**: 27,580 pixels (1.77%)

---

### w_0005.tif (7216 x 5412)

**출력**: `results/w_0005_fixed_b140/`

**통계**:
- **b threshold**: < 140 (absolute, 고정)
- **White coverage**: 16.20%
- **총 윤곽선**: 2,304개
- **검출 구멍**: 877개
- **제외됨**: 1,427개
- **면적 범위**: 10 - 18,569 pixels
- **평균 면적**: 338.7 pixels
- **중간값 면적**: 24.5 pixels
- **총 손상**: 297,018 pixels (0.76%)

---

## 자동 vs 고정 비교

### test_small.jpg

| Threshold | 구멍 개수 | Coverage | 판정 |
|-----------|----------|----------|------|
| 자동 (p33→b=140) | 258개 | 32.91% | - |
| **고정 b=140** | **258개** | **32.91%** | ✅ **동일** |

### w_0005.tif

| Threshold | 구멍 개수 | Coverage | 판정 |
|-----------|----------|----------|------|
| 자동 (p33→b=144) | 18,920개 | 26.64% | ⚠️ 너무 많음 |
| **고정 b=140** | **877개** | **16.20%** | ✅ **훨씬 좋음** |

**결론**: w_0005에서 자동 threshold가 18,920개를 검출했지만,
**고정 b=140으로 877개만 검출하는 것이 실제 구멍에 훨씬 가까움**.

---

## b=140의 물리적 의미

### LAB b-channel 기준
- **b < 128**: 파란색 계열
- **b = 128**: 중립 (회색)
- **b > 128**: 노란색 계열

### b=140 threshold
```
b < 140: 흰색 ~ 약간 노란 정도 → 구멍으로 판단
b ≥ 140: 노란색 (베이지) → 종이 얼룩으로 판단
```

**의미**:
- 진짜 구멍 (흰색/약간 노란색)만 검출
- 종이 얼룩 (베이지색)은 제외
- **엄격한 기준으로 정확한 구멍만 추출**

---

## 왜 고정 b=140이 더 좋은가?

### 1. 일관성
- 모든 이미지에 **동일한 기준** 적용
- 이미지가 달라져도 threshold는 항상 140

### 2. 재현성
- 언제 실행해도 **같은 결과**
- 다른 사람이 실행해도 동일

### 3. 물리적 의미 명확
- "b=140 미만은 구멍"이라는 **명확한 정의**
- percentile은 이미지마다 의미가 달라짐

### 4. 과검출 방지
- 자동 threshold는 이미지 색상에 따라 너무 많이 검출할 수 있음
- w_0005: 18,920개(자동) → 877개(고정) = **21배 감소**

### 5. 실제 구멍에 더 가까움
- 얼룩지고 변색된 부분을 구멍으로 오판하지 않음
- **진짜 구멍 (흰색)만 정확히 검출**

---

## 사용 예시

### 단일 이미지 처리
```bash
python extract_whiteness_based.py \
  --input "datasets/test_small.jpg" \
  --output-dir results/output \
  --method lab_b \
  --s-threshold 140 \
  --min-area 10
```

### 배치 처리 (여러 이미지)
```bash
# 모든 .tif 파일에 동일한 기준 적용
for img in datasets/1첩/*.tif; do
    name=$(basename "$img" .tif)
    python extract_whiteness_based.py \
      --input "$img" \
      --output-dir "results/${name}_b140" \
      --method lab_b \
      --s-threshold 140 \
      --min-area 10
done
```

---

## 파라미터 변경이 필요한 경우

### 더 많이 검출하고 싶다면 (해진 부분도 포함)
```bash
--s-threshold 145  # 또는 150
```
- b=145: 약간 더 노란 부분까지 포함
- b=150: 베이지색에 가까운 부분도 포함

### 더 적게 검출하고 싶다면 (진짜 구멍만)
```bash
--s-threshold 135  # 또는 130
```
- b=135: 거의 순백색만
- b=130: 완전 흰색만

### 권장 범위
```
b=130~145
```
- 130: 매우 엄격 (순백색만)
- 140: **권장값** (흰색~약간 노란색)
- 145: 관대함 (노란색까지)

---

## 최종 출력 위치

### test_small.jpg
```
results/test_small_fixed_b140/
├── comparison.png          # 258개 구멍 표시
├── white_mask.png          # 32.91% coverage
└── individual_holes/       # 258개 개별 이미지
```

### w_0005.tif
```
results/w_0005_fixed_b140/
├── comparison.png          # 877개 구멍 표시
├── white_mask.png          # 16.20% coverage
└── individual_holes/       # 877개 개별 이미지
```

---

## 핵심 개선 사항

### 1. extract_whiteness_based.py 수정
**Line 366-370**: y좌표 역순 정렬 추가
```python
# y좌표 역순 정렬 (아래→위)
holes = sorted(holes, key=lambda h: h['bbox'][1], reverse=True)
# ID 재할당
for i, hole in enumerate(holes):
    hole['id'] = i
```

### 2. 고정 threshold 사용
```python
# 자동 (사용 안 함)
--s-percentile 33

# 고정 (최종 권장)
--s-threshold 140
```

---

## 결론

**최종 권장 파라미터**:
```bash
--method lab_b --s-threshold 140 --min-area 10
```

**장점**:
- ✅ 일관성: 모든 이미지에 동일한 기준
- ✅ 재현성: 항상 같은 결과
- ✅ 정확성: 진짜 구멍만 검출 (과검출 방지)
- ✅ 명확성: 물리적 의미가 명확 (b<140=흰색)
- ✅ 실용성: 877개 (w_0005) vs 18,920개 (자동) = 21배 감소

**이 파라미터로 모든 문서를 일관되게 처리할 수 있습니다.** 🎯
