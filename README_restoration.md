# 조선시대 문서 복원 자동화 시스템
## Automated Restoration System for Korean Heritage Documents

문화재 복원 연구원을 위한 손상 부위 자동 검출 및 복원 가이드 생성 시스템

---

## Quick Start (빠른 시작)

### 1. 기본 사용법

```bash
python restoration_workflow.py --input 문서이미지.tif --output-dir results/문서명
```

**15초 안에 완료됩니다!**

### 2. 결과물

```
results/문서명/
├── detection/
│   ├── comparison.png          # 검출된 구멍 확인
│   └── svg_vectors/            # 레이저 커터용 개별 SVG 파일들
├── cutting_layout/
│   └── cutting_layout_page_*.svg  # 레이저 커터에 사용할 배치도
└── restoration_guide/
    ├── restoration_guide.png   # 복원 가이드 (어디에 붙일지 표시)
    └── piece_locations.csv     # 조각 위치 데이터
```

### 3. 워크플로우

1. **`cutting_layout_page_*.svg`** 파일을 레이저 커터로 출력
2. 종이를 커팅하고 인쇄
3. **`restoration_guide.png`** 파일을 보면서 번호에 맞춰 조각 붙이기

---

## 기능

### ✓ 자동 구멍 검출
- LAB 색공간 분석으로 손상 부위 자동 검출
- 타일 이미지 경계 자동 인식
- SVG 벡터 파일 생성 (레이저 커터 호환)

### ✓ 레이저 커팅 레이아웃
- A4/A3 용지에 자동 배치 (bin packing 알고리즘)
- 각 조각에 번호 자동 부여
- 여러 페이지 자동 생성

### ✓ 복원 가이드
- 원본 이미지에 번호 오버레이
- 어떤 조각을 어디에 붙일지 명확하게 표시
- CSV 좌표 데이터 제공

---

## 명령어 옵션

### 기본 옵션
```bash
--input           입력 이미지 파일 (필수)
--output-dir      결과 저장 폴더 (필수)
```

### 검출 파라미터
```bash
--threshold 138   LAB b-채널 임계값 (기본: 138)
--min-area 50     최소 구멍 크기 (기본: 50 픽셀)
--max-area 2500000  최대 구멍 크기 (기본: 2500000 픽셀)
```

### 레이아웃 옵션
```bash
--paper-size A4   용지 크기 (A4 또는 A3, 기본: A4)
```

### 단계 건너뛰기
```bash
--skip-detection  검출 단계 건너뛰기 (기존 결과 사용)
--skip-layout     레이아웃 생성 건너뛰기
--skip-guide      가이드 생성 건너뛰기
```

---

## 사용 예시

### 예시 1: 기본 처리
```bash
python restoration_workflow.py \
  --input "datasets/1첩/w_0001.tif" \
  --output-dir "results/w_0001"
```

### 예시 2: A3 용지 사용
```bash
python restoration_workflow.py \
  --input "datasets/1첩/w_0001.tif" \
  --output-dir "results/w_0001" \
  --paper-size A3
```

### 예시 3: 작은 구멍 무시하기
```bash
python restoration_workflow.py \
  --input "datasets/1첩/w_0001.tif" \
  --output-dir "results/w_0001" \
  --min-area 100
```

### 예시 4: 가이드만 다시 생성
```bash
python restoration_workflow.py \
  --input "datasets/1첩/w_0001.tif" \
  --output-dir "results/w_0001" \
  --skip-detection \
  --skip-layout
```

---

## 개별 스크립트 사용

필요한 단계만 따로 실행할 수도 있습니다:

### 1. 구멍 검출만
```bash
python extract_whiteness_based.py \
  --input "문서.tif" \
  --method lab_b \
  --s-threshold 138 \
  --export-svg \
  --svg-individual \
  --output-dir "results/detection"
```

### 2. 레이저 커팅 레이아웃만
```bash
python create_cutting_layout.py \
  --svg-dir "results/detection/svg_vectors" \
  --output-dir "results/cutting_layout" \
  --paper-size A4
```

### 3. 복원 가이드만
```bash
python create_restoration_guide.py \
  --image "문서.tif" \
  --svg-dir "results/detection/svg_vectors" \
  --output-dir "results/restoration_guide"
```

---

## 처리 시간

- 소형 이미지 (1-2MP): < 2초
- 중형 이미지 (5-10MP): 5-10초
- 대형 이미지 (30-40MP): 15-20초

**예시:** 7216x5412 픽셀 (39MP) 이미지, 297개 구멍 → **15.3초**

---

## 기존 방식과 비교

### 기존 수작업 방식 (3-5시간)
1. 스캔
2. Photoshop에서 일일이 구멍 따기 (2-3시간)
3. Illustrator에서 종이에 배치 (1-2시간)
4. 레이저 커터로 자르기
5. 인쇄하고 붙이기
6. **어디에 붙일지 까먹음**

### 자동화 방식 (15초)
1. 스캔
2. **`python restoration_workflow.py --input 문서.tif --output-dir results/문서`**
3. 레이저 커터로 자르기
4. **가이드 이미지 보면서 번호에 맞춰 붙이기**

**시간 절감: 99.9%**

---

## 필요한 프로그램

- Python 3.x
- OpenCV (`pip install opencv-python`)
- NumPy (`pip install numpy`)

---

## 문제 해결

### Q: "No SVG files found" 에러가 나요
**A:** `--svg-individual` 옵션이 빠졌거나, 검출된 구멍이 없을 수 있습니다. `comparison.png` 파일을 확인해보세요.

### Q: 구멍이 너무 많이/적게 검출되요
**A:** `--threshold` 값을 조정하세요:
- 구멍이 너무 많으면: 값을 **낮추기** (예: 135)
- 구멍이 너무 적으면: 값을 **높이기** (예: 140)

### Q: 작은 점들이 구멍으로 인식되요
**A:** `--min-area` 값을 높이세요 (예: `--min-area 100`)

### Q: 레이아웃에서 조각이 너무 작게 보여요
**A:** 개별 SVG 파일(`svg_vectors/` 폴더)을 직접 확인하세요. 각 파일은 구멍 중심으로 자동 확대되어 있습니다.

---

## 참고 문서

- **상세 기술 문서:** `worklog/2025-10-30_restoration_workflow_automation.md`
- **SVG 최적화 작업 기록:** `worklog/2025-10-30_svg_optimization_and_visualization.md`
- **배포 계획:** `plan/2025-10-30_next_steps_deployment.md`
- **복원 워크플로우 계획:** `plan/2025-10-30_restoration_workflow.md`

---

## Contact

문제가 있거나 개선 제안이 있으시면 연락 주세요.

**제작:** Claude Code Assistant
**날짜:** 2025-10-30
**버전:** 1.0
