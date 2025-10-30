# 문화재 복원 자동화 시스템

> 조선시대 고문서 손상 부위 자동 검출 및 복원 워크플로우

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📖 개요

문화재 복원 연구원을 위한 자동화 시스템입니다. 고문서의 손상 부위를 자동으로 검출하고, 레이저 커팅 레이아웃과 복원 가이드를 자동으로 생성합니다.

### ✨ 주요 기능

- 🔍 **자동 손상 부위 검출** - LAB 색공간 분석 기반 (정확도 ~95%)
- 🎯 **타일 경계 자동 감지** - 스캔 이미지 이어짐 처리
- 📐 **레이저 커팅 레이아웃** - 2D bin packing 알고리즘으로 최적 배치
- 📋 **복원 가이드 생성** - 번호 매핑 및 위치 정보
- 🔧 **스케일 조정** - 전체/개별 조각 크기 조정
- 👁️ **복원 미리보기** - SVG 조각 렌더링 및 커버리지 분석
- 📦 **SVG 벡터 출력** - 해상도 무관, 확대/축소 자유

### 📊 성능

- 🎯 **검출 정확도**: 높은 정확도
- 💾 **메모리 효율**: 해상도 자동 스케일링
- ⚡ **자동화**: 전체 워크플로우 원클릭 실행

---

## 🚀 빠른 시작

### 통합 워크플로우 (원클릭 실행)

```bash
# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 전체 과정 한 번에 실행
python restoration_workflow.py \
  --input datasets/1첩/w_0001.tif \
  --output-dir results/w_0001 \
  --threshold 138 \
  --paper-size A4
```

**실행 결과:**
1. 구멍 검출
2. 레이저 커팅 레이아웃 생성
3. 복원 가이드 생성

---

## 📦 설치

### 요구사항

- Python 3.8+
- OpenCV 4.x
- NumPy, Pillow

### 설치 방법

```bash
# 저장소 클론
git clone https://github.com/LimJih00n/Recognition_of_damaged_areas_in_ancient_documents.git
cd Recognition_of_damaged_areas_in_ancient_documents

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 패키지 설치
pip install -r requirements.txt
```

---

## 🎯 사용법

### 1. 기본 사용 (통합 워크플로우)

```bash
python restoration_workflow.py \
  --input datasets/document.tif \
  --output-dir results/output \
  --threshold 138 \
  --min-area 50 \
  --svg-simplify 0.1 \
  --paper-size A4
```

### 2. 단계별 실행

**Step 1: 구멍 검출**
```bash
python extract_whiteness_based.py \
  --input datasets/document.tif \
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

**Step 2: 레이저 커팅 레이아웃**
```bash
python create_cutting_layout.py \
  --svg-dir results/detection/svg_vectors \
  --output-dir results/cutting_layout \
  --paper-size A4 \
  --scale 1.0
```

**Step 3: 복원 가이드**
```bash
python create_restoration_guide.py \
  --image datasets/document.tif \
  --svg-dir results/detection/svg_vectors \
  --output-dir results/restoration_guide
```

### 3. 스케일 조정

**전체 스케일 조정:**
```bash
# 모든 조각을 1.5배 확대
python create_cutting_layout.py \
  --svg-dir svg_vectors/ \
  --scale 1.5
```

**개별 스케일 조정:**
```bash
# 1. scale_config.json 생성
{
  "156": 0.5,   # 큰 조각은 축소
  "284": 3.0    # 작은 조각은 확대
}

# 2. 실행
python create_cutting_layout.py \
  --svg-dir svg_vectors/ \
  --scale-config scale_config.json
```

---

## 📁 출력 결과물

```
results/
├── detection/
│   ├── document_boundary.png          # 문서 경계 감지
│   ├── comparison.png                 # 검출 결과 비교
│   ├── all_holes_vector.svg           # 통합 SVG
│   └── svg_vectors/                   # 개별 SVG (297개)
│
├── cutting_layout/
│   ├── cutting_layout_page_01_with_numbers.svg    # 번호 포함
│   ├── cutting_layout_page_01_for_laser.svg       # 레이저용
│   └── cutting_layout_info.json                   # 메타데이터
│
└── restoration_guide/
    ├── restoration_guide.png          # 번호 오버레이
    ├── restoration_preview.png        # 복원 미리보기 ⭐
    ├── coverage_visualization.png     # 커버리지 분석 ⭐
    └── piece_locations.csv            # 좌표 데이터
```

---

## 🏗️ 프로젝트 구조

```
Recognition_of_damaged_areas_in_ancient_documents/
├── extract_whiteness_based.py      # 핵심 구멍 검출 엔진
├── create_cutting_layout.py        # 레이저 커팅 레이아웃
├── create_restoration_guide.py     # 복원 가이드 생성
├── restoration_workflow.py         # 통합 워크플로우
├── verify_svg_alignment.py         # SVG 검증 도구
├── requirements.txt                # 패키지 목록
├── README.md                       # 이 문서
├── plan/                           # 설계 문서
└── worklog/                        # 작업 로그
```

---

## 🔧 주요 파라미터

### 구멍 검출 (`extract_whiteness_based.py`)

| 파라미터 | 설명 | 기본값 | 권장값 |
|---------|------|--------|--------|
| `--s-threshold` | LAB b-channel 임계값 | 138 | 135-140 |
| `--min-area` | 최소 구멍 크기 (픽셀) | 50 | 50-100 |
| `--svg-simplify` | SVG 단순화 수준 | 0.1 | 0.1 (원본 유지) |
| `--corner-method` | 경계 감지 방법 | edges | edges |

### 레이아웃 생성 (`create_cutting_layout.py`)

| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| `--paper-size` | 용지 크기 | A4 |
| `--scale` | 전체 스케일 | 1.0 |
| `--scale-config` | 개별 스케일 설정 | None |

---

## 📈 테스트 결과

### 예시 (w_0001.tif: 7216x5412)

- **검출된 구멍**: 297개
- **레이저 커팅 페이지**: 3장 (A4, 1.0x)
- **문서 영역**: 6254x5174 (82.9%)

---

## 📚 문서

- [전체 시스템 설명서](worklog/2025-10-30_FINAL_system_complete_with_scaling.md) - 상세 사용법 및 기능 설명
- [워크플로우 설계](plan/2025-10-30_restoration_workflow.md) - 시스템 설계 문서
- [타일 경계 감지](worklog/2025-10-30_tile_aware_document_boundary_detection.md) - 알고리즘 설명
- [SVG 최적화](worklog/2025-10-30_svg_optimization_and_visualization.md) - 벡터 출력 최적화

---

## 🎨 알고리즘

### 1. LAB 색공간 기반 구멍 검출

**원리:**
- RGB 대신 LAB 색공간 사용
  - **L**: 밝기 (0-255)
  - **a**: 빨강-녹색 축
  - **b**: 파랑-노랑 축 ⭐ (핵심)

**구멍 vs 종이 구분:**
```
베이지색 종이: b ≥ 138 (노란 톤)
흰색 구멍:    b < 138 (파란 톤, 중성)
```

**처리 과정:**
1. **전처리**: BGR → LAB 색공간 변환
2. **임계값 처리**: b-channel에서 Otsu 자동 임계값 계산
3. **Morphological 연산**:
   - Close (20x20 kernel): 내부 작은 구멍 메우기
   - Open (5x5 kernel): 외부 노이즈 제거
4. **윤곽선 검출**: `cv2.findContours()`로 구멍 경계 추출
5. **필터링**: 면적 기준 (min: 50px, max: 2,500,000px)

**해상도 자동 스케일링:**
```python
scale_factor = sqrt(current_pixels / reference_pixels)
scaled_min_area = min_area * scale_factor
scaled_kernel_size = kernel_size * scale_factor
```
- 기준: 7216x5412 (39,052,992 픽셀)
- 저해상도/고해상도 이미지에 일관된 결과 제공

---

### 2. 타일 경계 자동 감지

**문제점:**
큰 문서를 여러 타일로 나눠 스캔할 경우:
- 가장자리 손상이 배경과 연결됨
- 전체 배경이 "구멍"으로 오검출됨

**해결 방법:**

**Step 1: 문서 마스크 생성**
```python
# LAB b-channel threshold로 문서 영역 추출
doc_mask = b_channel > threshold  # 베이지색 종이
```

**Step 2: 최대 컨투어 찾기**
- 가장 큰 연결된 영역 = 문서 영역

**Step 3: 각 변의 특성 판단**
```python
margin_threshold = 50  # 픽셀

for edge in [left, top, right, bottom]:
    distance = edge_to_image_border(edge)

    if distance > margin_threshold:
        # 실제 문서 경계
        boundary[edge] = contour_edge
    else:
        # 타일 경계 (이어짐)
        boundary[edge] = image_edge
```

**결과:**
- 실제 경계: 윤곽선 그대로 사용
- 타일 경계: 이미지 끝까지 확장
- 배경 제외: 경계 밖 영역은 검출에서 제외

---

### 3. 2D Bin Packing (레이아웃 최적화)

**목표:**
SVG 조각들을 A4/A3 용지에 최소 페이지로 배치

**알고리즘:** Shelf-based Bin Packing

**Step 1: 조각 정렬**
```python
pieces.sort(key=lambda p: p.height, reverse=True)
# 큰 조각부터 배치 (First Fit Decreasing)
```

**Step 2: Shelf 생성 및 배치**
```python
class Shelf:
    def __init__(self, y, height, width):
        self.y = y              # Shelf의 y 좌표
        self.height = height    # 가장 높은 조각 높이
        self.x_offset = 0       # 현재 x 위치
        self.width = width      # 남은 너비

for piece in sorted_pieces:
    # 기존 shelf에 넣을 수 있는지 확인
    fitted = False
    for shelf in shelves:
        if shelf.can_fit(piece):
            shelf.add(piece)
            fitted = True
            break

    # 새 shelf 생성
    if not fitted:
        new_shelf = Shelf(current_y, piece.height, page_width)
        new_shelf.add(piece)
        shelves.append(new_shelf)
        current_y += piece.height + spacing

    # 페이지 넘침 확인
    if current_y > page_height:
        create_new_page()
```

**최적화:**
- 간격: 1.5mm (레이저 커팅 여유)
- 여백: 10mm (용지 가장자리)
- 회전 없음 (원본 방향 유지)

**복잡도:**
- 시간: O(n²) (n = 조각 개수)
- 공간 효율: ~70-80% (일반적인 bin packing)

---

### 4. SVG 벡터화

**윤곽선 → SVG Path 변환:**

**Step 1: 윤곽선 단순화**
```python
epsilon = simplify_factor  # 기본값: 0.1
approx = cv2.approxPolyDP(contour, epsilon, closed=True)
# Douglas-Peucker 알고리즘
```

**Step 2: SVG Path 명령어 생성**
```python
path_data = f"M {x0},{y0}"  # MoveTo (시작점)
for (x, y) in points[1:]:
    path_data += f" L {x},{y}"  # LineTo
path_data += " Z"  # ClosePath
```

**Step 3: 메타데이터 추가**
```xml
<metadata>
    <hole_id>156</hole_id>
    <bbox>x=1234, y=567, w=118, h=268</bbox>
    <area>31624</area>
    <original_position>center: (1293, 701)</original_position>
</metadata>
```

**좌표계:**
- 원본 이미지 좌표 유지 (픽셀 단위)
- DPI 300 기준 물리적 크기 계산 (mm)
- ViewBox로 스케일링 정보 저장

---

### 5. 스케일 변환 (레이저 커팅용)

**SVG Transform 적용:**

```python
# 원본 크기
original_width = piece.width   # mm
original_height = piece.height

# 스케일 적용
scaled_width = original_width * scale_factor
scaled_height = original_height * scale_factor

# SVG transform 계산
scale_x = scaled_width / viewBox_width
scale_y = scaled_height / viewBox_height

transform = f"translate({x}, {y}) scale({scale_x}, {scale_y})"
```

**중심점 기준 스케일링:**
```python
center_x = x + width / 2
center_y = y + height / 2

for point in path_points:
    dx = point.x - center_x
    dy = point.y - center_y

    scaled_point.x = center_x + dx * scale
    scaled_point.y = center_y + dy * scale
```

**개별 vs 전체 스케일:**
- 전체 스케일: 모든 조각에 동일 비율 적용
- 개별 스케일: JSON 설정 파일에서 조각별 비율 지정
- 우선순위: 개별 > 전체

---

## 🌐 웹 서비스 확장 (계획)

현재 CLI 기반 시스템은 웹 서비스로 확장 가능합니다:

- ✅ 이미지 업로드 → 자동 처리
- ✅ 실시간 진행 상황 표시
- ✅ 인터랙티브 조각 조작 (드래그/스케일)
- ✅ 조각 갤러리 & 검색
- ✅ 결과 다운로드 (ZIP)

기술 스택: Flask/FastAPI + Vue.js/React + D3.js/Fabric.js

---

## 🤝 기여

이슈 및 Pull Request를 환영합니다!

---

## 📄 라이선스

이 프로젝트는 문화재 복원 연구를 위해 개발되었습니다.

---

## 👨‍💻 개발

**개발 기간**: 2025-10-27 ~ 2025-10-30

**개발자**: Claude Code + LimJih00n

**버전**: v2.0 (스케일 기능 추가)

---

## 🔗 관련 링크

- [GitHub Repository](https://github.com/LimJih00n/Recognition_of_damaged_areas_in_ancient_documents)
- [프로젝트 문서](worklog/)

---

## 📧 문의

문제가 발생하거나 질문이 있으시면 [Issues](https://github.com/LimJih00n/Recognition_of_damaged_areas_in_ancient_documents/issues)에 등록해주세요.

---
