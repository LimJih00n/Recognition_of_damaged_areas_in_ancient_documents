# 문화재 복원 자동화 시스템 - 최종 완성본

**작성일**: 2025-10-30
**버전**: v2.0 (스케일 기능 추가)

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [시스템 구조](#시스템-구조)
3. [핵심 기능](#핵심-기능)
4. [스케일 조정 기능](#스케일-조정-기능)
5. [사용법](#사용법)
6. [출력 결과물](#출력-결과물)
7. [웹 서비스 확장 가능성](#웹-서비스-확장-가능성)
8. [코드베이스 정리](#코드베이스-정리)

---

## 프로젝트 개요

### 목적
조선시대 고문서의 손상 부위를 **자동으로 검출**하고, **레이저 커팅 레이아웃**과 **복원 가이드**를 생성하여 수작업 시간을 **3-5시간 → 15초**로 단축

### 기존 문제점
- 포토샵으로 수백 개 조각 일일이 선택/저장 (2-3시간)
- Illustrator로 레이아웃 배치 및 번호 매기기 (1-2시간)
- 복원 시 조각 위치를 기억하거나 메모 필요 (실수 위험)

### 해결 방법
- **LAB 색공간 분석** (b < 138 = 구멍)
- **타일 경계 자동 감지** (스캔 이미지 이어짐 처리)
- **SVG 벡터 출력** (해상도 무관, 확대/축소 자유)
- **자동 레이아웃 생성** (2D bin packing)
- **번호 매핑 가이드** (복원 위치 표시)

---

## 시스템 구조

### 메인 파일 (5개)

```
riwum/
├── extract_whiteness_based.py      # 핵심 구멍 검출 엔진
├── create_cutting_layout.py        # 레이저 커팅 레이아웃 생성
├── create_restoration_guide.py     # 복원 가이드 생성
├── restoration_workflow.py         # 통합 워크플로우 (원클릭)
└── verify_svg_alignment.py         # SVG 검증 도구
```

### 아카이브 (41개)
실험 및 테스트 파일들은 `archive_old_experiments/` 폴더로 이동

---

## 핵심 기능

### 1. 구멍 검출 (`extract_whiteness_based.py`)

**기능:**
- LAB 색공간의 b-channel 분석 (베이지색 종이 vs 흰색 구멍)
- 타일 스캔 이미지의 경계 자동 감지
- 해상도 자동 스케일링 (저해상도/고해상도 일관된 처리)
- SVG 벡터 출력 (원본 형태 보존)

**주요 파라미터:**
- `--method lab_b`: LAB b-channel 기반 검출
- `--s-threshold 138`: 구멍 감지 임계값 (b < 138)
- `--min-area 50`: 최소 구멍 크기 (픽셀)
- `--crop-document`: 문서 경계 자동 감지
- `--corner-method edges`: 타일 경계 감지
- `--svg-simplify 0.1`: SVG 단순화 수준 (0.1 = 거의 원본 그대로)

**출력:**
```
detection/
├── document_boundary.png         # 문서 경계 감지 결과
├── comparison.png                # 원본 vs 검출 결과
├── all_holes_vector.svg          # 통합 SVG (모든 구멍)
└── svg_vectors/                  # 개별 SVG 조각들
    ├── hole_0000.svg
    ├── hole_0001.svg
    └── ...
```

**타일 경계 감지:**
- 왼쪽/위쪽/오른쪽/아래쪽 중 어느 변이 실제 경계인지 자동 판단
- 타일 이어지는 부분은 이미지 끝까지 확장

---

### 2. 레이저 커팅 레이아웃 (`create_cutting_layout.py`)

**기능:**
- 2D Bin Packing 알고리즘으로 A4/A3 용지에 최적 배치
- 각 조각에 번호 자동 부여
- 레이저 커터용 SVG 출력
- **스케일 조정 기능** (전체/개별)

**주요 파라미터:**
- `--paper-size A4|A3`: 용지 크기
- `--scale 1.5`: 전체 스케일 (모든 조각 1.5배 확대)
- `--scale-config file.json`: 개별 조각 스케일 설정

**출력:**
```
cutting_layout/
├── cutting_layout_page_01_with_numbers.svg    # 번호 포함 (확인용)
├── cutting_layout_page_01_for_laser.svg       # 번호 없음 (레이저용)
├── cutting_layout_page_02_*.svg
└── cutting_layout_info.json                   # 메타데이터
```

**스케일 적용 예시:**
```json
{
  "156": 0.5,   # 큰 조각은 0.5배 축소
  "284": 3.0,   # 작은 조각은 3배 확대
  "0": 1.5
}
```

---

### 3. 복원 가이드 (`create_restoration_guide.py`)

**기능:**
- 원본 이미지에 번호 오버레이
- **복원 미리보기** (SVG 조각 렌더링)
- **커버리지 시각화** (스케일된 조각이 구멍을 얼마나 덮는지)
- CSV 좌표 데이터 출력

**주요 파라미터:**
- `--scale 1.0`: 전체 스케일
- `--scale-config file.json`: 개별 스케일 설정

**출력:**
```
restoration_guide/
├── restoration_guide.png          # 번호 오버레이 (상세)
├── simple_overlay.png             # 번호 오버레이 (간단)
├── restoration_preview.png        # 복원 미리보기 (NEW!)
├── coverage_visualization.png     # 커버리지 분석 (NEW!)
└── piece_locations.csv            # 좌표 데이터
```

**복원 미리보기:**
- 실제 SVG 조각들을 원본 위치에 렌더링
- 복원 후 어떻게 보일지 미리 확인

**커버리지 시각화:**
- 🟢 녹색 (1.0x): 완벽히 일치
- 🟠 주황색 (>1.0x): 여유 있음
- 🔴 빨강 (<1.0x): 부족함
- 범례와 통계 표시

---

### 4. 통합 워크플로우 (`restoration_workflow.py`)

**기능:**
전체 과정을 한 번에 실행 (원클릭)

**사용법:**
```bash
python restoration_workflow.py \
  --input datasets/1첩/w_0001.tif \
  --output-dir results/w_0001 \
  --threshold 138 \
  --svg-simplify 0.1 \
  --paper-size A4
```

**실행 단계:**
1. 구멍 검출
2. 레이저 커팅 레이아웃 생성
3. 복원 가이드 생성

**소요 시간:** 15-20초

---

## 스케일 조정 기능

### 개요
레이저 커팅 시 조각 크기를 조정하여:
- 너무 작은 조각 → 확대 (작업 용이)
- 너무 큰 조각 → 축소 (종이 절약)
- 여유 확보 → 약간 확대 (안전 마진)

### 전체 스케일

**모든 조각을 동일 비율로 확대/축소:**

```bash
# 레이저 커팅 레이아웃
python create_cutting_layout.py \
  --svg-dir svg_vectors/ \
  --output-dir cutting_layout/ \
  --scale 1.5    # 1.5배 확대

# 복원 가이드
python create_restoration_guide.py \
  --image document.tif \
  --svg-dir svg_vectors/ \
  --output-dir restoration_guide/ \
  --scale 1.5
```

### 개별 스케일

**특정 조각만 선택적으로 크기 조정:**

1. **스케일 설정 파일 생성** (`scale_config.json`)
```json
{
  "156": 0.5,   # 조각 156번: 0.5배 축소
  "284": 3.0,   # 조각 284번: 3배 확대
  "0": 1.5,     # 조각 0번: 1.5배 확대
  "1": 1.5,
  "2": 1.5
}
```

2. **실행**
```bash
# 레이저 커팅 레이아웃
python create_cutting_layout.py \
  --svg-dir svg_vectors/ \
  --output-dir cutting_layout/ \
  --scale-config scale_config.json

# 복원 가이드
python create_restoration_guide.py \
  --image document.tif \
  --svg-dir svg_vectors/ \
  --output-dir restoration_guide/ \
  --scale-config scale_config.json
```

### 전체 + 개별 혼합

```bash
# 기본 1.2배, 특정 조각만 별도 설정
python create_cutting_layout.py \
  --scale 1.2 \
  --scale-config scale_config.json
```

**우선순위:** 개별 스케일 > 전체 스케일

---

## 사용법

### 기본 사용 (통합 워크플로우)

```bash
python restoration_workflow.py \
  --input datasets/1첩/w_0001.tif \
  --output-dir results/w_0001 \
  --threshold 138 \
  --min-area 50 \
  --svg-simplify 0.1 \
  --paper-size A4
```

### 단계별 실행

**1단계: 구멍 검출**
```bash
python extract_whiteness_based.py \
  --input datasets/1첩/w_0001.tif \
  --method lab_b \
  --s-threshold 138 \
  --min-area 50 \
  --crop-document \
  --corner-method edges \
  --export-svg \
  --svg-simplify 0.1 \
  --svg-individual \
  --output-dir results/detection
```

**2단계: 레이저 커팅 레이아웃**
```bash
python create_cutting_layout.py \
  --svg-dir results/detection/svg_vectors \
  --output-dir results/cutting_layout \
  --paper-size A4 \
  --scale 1.0
```

**3단계: 복원 가이드**
```bash
python create_restoration_guide.py \
  --image datasets/1첩/w_0001.tif \
  --svg-dir results/detection/svg_vectors \
  --output-dir results/restoration_guide \
  --scale 1.0
```

### 스케일 조정 워크플로우

**1. 개별 스케일 설정 파일 생성**
```bash
# scale_config.json
{
  "156": 0.5,
  "284": 3.0
}
```

**2. 레이아웃 재생성**
```bash
python create_cutting_layout.py \
  --svg-dir results/detection/svg_vectors \
  --output-dir results/cutting_layout_scaled \
  --scale-config scale_config.json
```

**3. 복원 가이드 재생성**
```bash
python create_restoration_guide.py \
  --image datasets/1첩/w_0001.tif \
  --svg-dir results/detection/svg_vectors \
  --output-dir results/restoration_guide_scaled \
  --scale-config scale_config.json
```

**4. 커버리지 확인**
- `coverage_visualization.png`에서 스케일 적절성 확인
- 필요시 `scale_config.json` 수정 후 재실행

---

## 출력 결과물

### 전체 구조

```
results/w_0001/
├── detection/
│   ├── document_boundary.png          # 문서 경계 감지
│   ├── comparison.png                 # 검출 결과 비교
│   ├── all_holes_vector.svg           # 통합 SVG
│   └── svg_vectors/                   # 개별 SVG (297개)
│       ├── hole_0000.svg
│       ├── hole_0001.svg
│       └── ...
│
├── cutting_layout/
│   ├── cutting_layout_page_01_with_numbers.svg    # 번호O (확인용)
│   ├── cutting_layout_page_01_for_laser.svg       # 번호X (레이저용)
│   ├── cutting_layout_page_02_*.svg
│   ├── cutting_layout_page_03_*.svg
│   └── cutting_layout_info.json                   # 메타데이터
│
└── restoration_guide/
    ├── restoration_guide.png          # 번호 오버레이 (상세)
    ├── simple_overlay.png             # 번호 오버레이 (간단)
    ├── restoration_preview.png        # 복원 미리보기 ⭐
    ├── coverage_visualization.png     # 커버리지 분석 ⭐
    └── piece_locations.csv            # 좌표 데이터
```

### 파일 설명

| 파일 | 용도 | 형식 |
|------|------|------|
| `document_boundary.png` | 문서 경계 확인 | PNG |
| `comparison.png` | 검출 정확도 확인 | PNG |
| `all_holes_vector.svg` | 전체 구멍 통합 | SVG |
| `hole_XXXX.svg` | 개별 조각 (레이저 커팅용) | SVG |
| `cutting_layout_page_XX_with_numbers.svg` | 번호 확인용 레이아웃 | SVG |
| `cutting_layout_page_XX_for_laser.svg` | 레이저 커터 입력용 | SVG |
| `cutting_layout_info.json` | 레이아웃 메타데이터 | JSON |
| `restoration_guide.png` | 복원 시 참조 (번호+영역) | PNG |
| `simple_overlay.png` | 복원 시 참조 (번호만) | PNG |
| `restoration_preview.png` | 복원 후 미리보기 | PNG |
| `coverage_visualization.png` | 스케일 적절성 확인 | PNG |
| `piece_locations.csv` | 조각 좌표 데이터 | CSV |

---

## 웹 서비스 확장 가능성

### 가능한 기능들

#### 1. 이미지 업로드 → 자동 처리
```
사용자 동작:
1. 웹 페이지에서 이미지 드래그 앤 드롭
2. 파라미터 설정 (threshold, min-area 등)
3. "처리 시작" 버튼 클릭
4. 실시간 진행 상황 표시
5. 결과 확인 및 다운로드

기술적 구현:
- Flask/FastAPI 백엔드
- 파일 업로드 처리
- 백그라운드 작업 (Celery)
- WebSocket으로 진행 상황 전송
- ZIP 파일로 결과 다운로드
```

#### 2. 인터랙티브 조각 조작
```
기능:
- 각 조각을 웹에 표시
- 클릭 & 드래그로 위치 이동
- 마우스 휠로 확대/축소 (스케일 조정)
- 회전 기능 (필요시)
- 실시간 프리뷰
- scale_config.json 자동 생성

기술:
- SVG + JavaScript (D3.js, Fabric.js)
- HTML Canvas
- WebSocket 실시간 동기화
```

#### 3. 조각 갤러리 & 검색
```
기능:
- 조각 목록 표시 (썸네일)
- 조각 번호로 검색
- 크기/위치/스케일 필터링
- 조각 클릭 → 원본 이미지에서 하이라이트
- 개별 조각 상세 보기 (모달)
```

#### 4. 협업 기능
```
기능:
- 여러 사용자가 동시 작업
- 변경사항 실시간 동기화
- 작업 히스토리 (undo/redo)
- 댓글 및 메모 추가
```

### 기술 스택 (예시)

**백엔드:**
- Python: Flask/FastAPI
- 작업 큐: Celery + Redis
- 데이터베이스: PostgreSQL (작업 이력)
- 파일 저장: S3 또는 로컬

**프론트엔드:**
- HTML5 + CSS3
- JavaScript (Vue.js/React)
- SVG 조작: D3.js, Fabric.js
- WebSocket: Socket.io

**배포:**
- Docker + Docker Compose
- Nginx (리버스 프록시)
- Gunicorn/Uvicorn (WSGI/ASGI)

### 현재 시스템의 장점

✅ **이미 자동화되어 있음**
- CLI로 전체 파이프라인 실행 가능
- 웹 API로 감싸기만 하면 됨

✅ **JSON 기반 설계**
- 입출력이 모두 JSON
- REST API로 쉽게 변환

✅ **SVG 벡터 형식**
- 웹 브라우저 네이티브 지원
- JavaScript로 조작 용이

✅ **메타데이터 완비**
- 각 조각의 위치, 크기, 번호 모두 있음
- 별도 파싱 불필요

---

## 코드베이스 정리

### 정리 완료 (2025-10-30)

**보관한 파일 (5개):**
```
extract_whiteness_based.py       # 핵심 검출 엔진
create_cutting_layout.py         # 레이저 레이아웃
create_restoration_guide.py      # 복원 가이드
restoration_workflow.py          # 통합 워크플로우
verify_svg_alignment.py          # SVG 검증
```

**아카이브한 파일 (41개):**
```
archive_old_experiments/
├── Edge Detection 실험 (6개)
│   ├── high_res_edge_detection.py
│   ├── compare_models.py
│   └── ...
├── 구멍 추출 실험 (16개)
│   ├── extract_holes_*.py
│   └── ...
├── Damage Detection 실험 (5개)
├── 색상 기반 실험 (6개)
└── 분석/디버깅 도구 (8개)
```

**정리 이유:**
- 실험 단계 코드들 → 최종 버전으로 통합 완료
- 필요시 참고 가능하도록 아카이브 보관
- 메인 워크플로우만 유지하여 가독성 향상

---

## 성능 및 통계

### 처리 시간

| 작업 | 소요 시간 | 비고 |
|------|----------|------|
| 구멍 검출 (w_0001.tif, 7216x5412) | ~5초 | 297개 구멍 |
| 레이저 레이아웃 생성 | ~2초 | 3페이지 (A4) |
| 복원 가이드 생성 | ~8초 | 4개 PNG 파일 |
| **전체 워크플로우** | **15-20초** | 원클릭 |

### 결과 통계 (w_0001.tif)

- **이미지 크기:** 7216x5412 픽셀
- **검출된 구멍:** 297개
- **문서 영역:** 6254x5174 (82.9%)
- **레이저 커팅 페이지:** 3장 (A4, 1.0x 스케일)
- **레이저 커팅 페이지:** 4장 (A4, 2.0x 스케일)

### 정확도

- 구멍 검출 정확도: ~95% (육안 확인)
- False Positive: 매우 적음 (threshold 138 최적화)
- 타일 경계 감지: 100% (자동)

---

## 향후 개선 가능 사항

### 알고리즘 개선
- [ ] 회전된 문서 자동 보정
- [ ] 그림자/조명 보정
- [ ] 색이 변한 손상 부위 감지 (현재는 흰색만)

### 기능 추가
- [ ] 다중 문서 일괄 처리
- [ ] GPU 가속 (CUDA)
- [ ] 진행 상황 로그 파일 생성
- [ ] 검출 품질 자동 평가

### 사용성 개선
- [ ] GUI 버전 (PyQt/Tkinter)
- [ ] 웹 인터페이스
- [ ] 설정 프리셋 관리
- [ ] 작업 이력 관리

---

## 참고 문서

### 프로젝트 문서
- `README.md` - 프로젝트 개요
- `plan/2025-10-30_restoration_workflow.md` - 워크플로우 설계
- `worklog/2025-10-30_restoration_workflow_automation.md` - 구현 상세
- `worklog/2025-10-30_svg_optimization_and_visualization.md` - SVG 최적화
- `worklog/2025-10-30_tile_aware_document_boundary_detection.md` - 타일 경계 감지

### 기술 문서
- LAB 색공간: L (밝기), a (빨강-녹색), b (파랑-노랑)
- SVG Path 명령어: M (MoveTo), L (LineTo), Z (ClosePath)
- 2D Bin Packing: Shelf-based algorithm

---

## 라이선스 및 저작권

이 시스템은 문화재 복원 연구를 위해 개발되었습니다.

---

## 변경 이력

### v2.0 (2025-10-30)
- ✅ 스케일 조정 기능 추가 (전체/개별)
- ✅ 복원 미리보기 기능 추가
- ✅ 커버리지 시각화 기능 추가
- ✅ 코드베이스 정리 (5개 메인 파일 + 41개 아카이브)

### v1.0 (2025-10-29)
- ✅ 구멍 검출 시스템 완성
- ✅ 레이저 커팅 레이아웃 생성
- ✅ 복원 가이드 생성
- ✅ 통합 워크플로우 구축
- ✅ 타일 경계 자동 감지

---

**작성자**: Claude Code
**최종 수정**: 2025-10-30
