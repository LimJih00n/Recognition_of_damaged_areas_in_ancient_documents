# 문화재 복원 전용 워크플로우 시스템

**작성일**: 2025-10-30
**대상 사용자**: 문화재 복원 연구원
**목적**: 손상 부위 검출 → 레이저 커팅 → 복원 작업 자동화

---

## 📋 목차

1. [현재 수작업 프로세스](#현재-수작업-프로세스)
2. [문제점 분석](#문제점-분석)
3. [자동화 솔루션](#자동화-솔루션)
4. [Phase 1: 레이저 커팅 준비](#phase-1-레이저-커팅-준비)
5. [Phase 2: 복원 가이드 생성](#phase-2-복원-가이드-생성)
6. [Phase 3: 통합 시스템](#phase-3-통합-시스템)
7. [최종 워크플로우](#최종-워크플로우)

---

## 현재 수작업 프로세스

### Step 1: 스캔
```
고해상도 스캐너로 손상된 고문서 촬영
→ 7216x5412 픽셀 TIFF 파일
```

### Step 2: 손상 부위 따기 (⏰ 시간 소모)
```
포토샵에서:
1. 매직 완드 또는 펜 툴로 손상 부위 선택
2. 레이어로 분리
3. 각 조각을 개별 파일로 저장
4. 수백 개 조각 → 몇 시간 소요 ❌
```

### Step 3: 인쇄 레이아웃 (⏰ 시간 소모)
```
Illustrator 또는 InDesign에서:
1. A4/A3 용지 템플릿 생성
2. 각 조각을 하나씩 배치
3. 조각마다 번호 표시 (수동)
4. 레이저 커팅 선 추가
```

### Step 4: 레이저 커팅
```
레이저 커터에 종이 넣고 실행
→ 조각들이 잘려서 나옴
```

### Step 5: 인쇄
```
잘라낸 조각 위에 인쇄
(또는 인쇄 후 레이저 커팅)
```

### Step 6: 복원 (❌ 문제 발생)
```
문제점:
- 조각이 200-300개
- 각 조각을 어디에 붙여야 하는지 모름
- 위치를 일일이 기억하거나 메모해야 함
- 실수로 잘못된 위치에 붙임
```

---

## 문제점 분석

### 1. 시간 소모
- **손상 부위 따기**: 포토샵으로 수 시간
- **레이아웃 배치**: Illustrator로 수 시간
- **번호 매기기**: 수동으로 일일이 입력

### 2. 위치 정보 손실
- **조각을 어디에 붙여야 하는지 모름**
- 메모를 해도 번호와 위치 매칭 어려움
- 실수 위험

### 3. 재현성 부족
- 다른 문서 작업 시 처음부터 다시
- 노하우 공유 어려움

---

## 자동화 솔루션

### 우리 시스템이 제공할 것

```
┌─────────────────────────────────────────┐
│  입력: 스캔 이미지 (w_0001.tif)         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  자동 처리 (클릭 한 번)                  │
│  - 손상 부위 자동 검출                   │
│  - SVG 벡터 생성                        │
│  - 레이저 커팅 레이아웃 생성             │
│  - 복원 가이드 생성                      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  출력:                                   │
│  1. 레이저 커팅용 PDF (A4 여러 장)       │
│  2. 복원 가이드 (번호 + 위치 표시)       │
│  3. 조각 목록 (번호, 좌표, 크기)         │
└─────────────────────────────────────────┘
```

---

## Phase 1: 레이저 커팅 준비

### 목표
- A4/A3 용지에 자동으로 조각 배치
- 각 조각에 번호 표시
- 레이저 커팅 가능한 형식 출력

---

### 1.1 자동 레이아웃 생성기

**파일**: `create_cutting_layout.py`

```python
"""
레이저 커팅용 레이아웃 자동 생성

출력:
  - cutting_layout_01.pdf (A4, 1페이지)
  - cutting_layout_02.pdf (A4, 2페이지)
  - ...
  - cutting_layout_all.pdf (전체 통합)
"""

import svgwrite
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3

def create_cutting_layout(svg_dir, output_dir, paper_size='A4'):
    """레이저 커팅 레이아웃 생성"""

    # 용지 크기
    if paper_size == 'A4':
        width_mm, height_mm = 210, 297
    elif paper_size == 'A3':
        width_mm, height_mm = 297, 420

    # 여백
    margin_mm = 10
    spacing_mm = 5

    # SVG 파일 로드
    svg_files = sorted(glob.glob(f"{svg_dir}/*.svg"))

    # 배치 알고리즘 (bin packing)
    pages = pack_pieces_into_pages(
        svg_files,
        width_mm - margin_mm * 2,
        height_mm - margin_mm * 2,
        spacing_mm
    )

    # 각 페이지별 PDF 생성
    for page_num, pieces in enumerate(pages, 1):
        pdf_path = f"{output_dir}/cutting_layout_{page_num:02d}.pdf"
        create_page_pdf(pieces, pdf_path, paper_size)

    # 전체 통합 PDF
    merge_pdfs(output_dir, "cutting_layout_all.pdf")

    print(f"Created {len(pages)} pages")
    return pages


def pack_pieces_into_pages(svg_files, page_w, page_h, spacing):
    """2D bin packing: 조각들을 용지에 효율적으로 배치"""

    pieces = []

    # 각 SVG의 크기 계산
    for svg_file in svg_files:
        width, height = get_svg_size(svg_file)
        pieces.append({
            'file': svg_file,
            'width': width,
            'height': height,
            'id': extract_hole_id(svg_file)
        })

    # 크기 순 정렬 (큰 것부터)
    pieces.sort(key=lambda p: p['width'] * p['height'], reverse=True)

    # Bin packing 알고리즘
    pages = []
    current_page = []
    current_y = 0
    current_x = 0
    row_height = 0

    for piece in pieces:
        # 현재 행에 들어갈 수 있는지 확인
        if current_x + piece['width'] > page_w:
            # 다음 행으로
            current_x = 0
            current_y += row_height + spacing
            row_height = 0

        # 페이지를 넘어가는지 확인
        if current_y + piece['height'] > page_h:
            # 새 페이지
            pages.append(current_page)
            current_page = []
            current_x = 0
            current_y = 0
            row_height = 0

        # 조각 배치
        piece['x'] = current_x
        piece['y'] = current_y
        current_page.append(piece)

        current_x += piece['width'] + spacing
        row_height = max(row_height, piece['height'])

    # 마지막 페이지 추가
    if current_page:
        pages.append(current_page)

    return pages


def create_page_pdf(pieces, output_path, paper_size):
    """PDF 페이지 생성 (레이저 커팅용)"""

    c = canvas.Canvas(output_path, pagesize=A4 if paper_size=='A4' else A3)

    for piece in pieces:
        # SVG 임베드
        x_mm = piece['x'] + 10  # 여백
        y_mm = piece['y'] + 10

        # mm → points (1mm = 2.834645669 pt)
        x_pt = x_mm * 2.834645669
        y_pt = y_mm * 2.834645669

        # SVG를 PDF에 그리기
        embed_svg(c, piece['file'], x_pt, y_pt)

        # 번호 표시
        hole_id = piece['id']
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x_pt, y_pt - 10, f"#{hole_id}")

        # 커팅 선 (옵션)
        if SHOW_CUTTING_LINES:
            c.setStrokeColorRGB(1, 0, 0)  # 빨간색
            c.setLineWidth(0.5)
            c.rect(x_pt, y_pt, piece['width']*2.83, piece['height']*2.83)

    c.save()
    print(f"Created: {output_path}")


def embed_svg(canvas, svg_path, x, y):
    """SVG를 PDF에 임베드"""
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF

    drawing = svg2rlg(svg_path)
    drawing.drawOn(canvas, x, y)
```

**출력 예시**:
```
results/w_0001_cutting/
├── cutting_layout_01.pdf    # A4, 첫 페이지 (조각 #1-50)
├── cutting_layout_02.pdf    # A4, 2페이지 (조각 #51-100)
├── cutting_layout_03.pdf    # A4, 3페이지 (조각 #101-150)
└── cutting_layout_all.pdf   # 전체 통합 (3페이지)
```

**페이지 레이아웃**:
```
┌────────────────────────────────────┐
│  A4 용지 (210 x 297 mm)            │
│  ┌──────┐                          │
│  │ #1   │  ┌──┐  ┌────┐           │
│  │      │  │#2│  │ #3 │           │
│  └──────┘  └──┘  └────┘           │
│                                    │
│  ┌───┐  ┌──────────┐              │
│  │#4 │  │   #5     │  ┌─┐        │
│  └───┘  └──────────┘  │6│        │
│                        └─┘        │
│  ...                               │
└────────────────────────────────────┘
```

---

### 1.2 레이저 커터 호환 형식

**지원 형식**:
```python
def export_for_laser_cutter(svg_dir, output_dir, format='pdf'):
    """레이저 커터 호환 형식으로 출력"""

    if format == 'pdf':
        # PDF (가장 범용적)
        create_cutting_layout(svg_dir, output_dir)

    elif format == 'dxf':
        # DXF (AutoCAD 호환)
        convert_svg_to_dxf(svg_dir, output_dir)

    elif format == 'ai':
        # Adobe Illustrator
        convert_svg_to_ai(svg_dir, output_dir)

    elif format == 'eps':
        # EPS (PostScript)
        convert_svg_to_eps(svg_dir, output_dir)
```

---

## Phase 2: 복원 가이드 생성

### 목표
- **각 조각을 어디에 붙여야 하는지 명확히 표시**
- 원본 이미지 + 번호 오버레이
- 번호별 좌표 리스트

---

### 2.1 복원 가이드 이미지

**파일**: `create_restoration_guide.py`

```python
"""
복원 가이드 생성

출력:
  1. restoration_guide.png - 원본 + 번호 오버레이
  2. restoration_map.pdf - 인쇄 가능한 가이드
  3. piece_locations.csv - 번호별 위치 데이터
"""

def create_restoration_guide(image_path, holes_data, output_dir):
    """복원 가이드 생성"""

    # 원본 이미지 로드
    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    # 1. 번호 오버레이 이미지
    guide = image.copy()

    for hole in holes_data:
        hole_id = hole['id']
        x, y, hw, hh = hole['bbox']

        # 중심점 계산
        cx = x + hw // 2
        cy = y + hh // 2

        # 구멍 윤곽선 (녹색)
        cv2.rectangle(guide, (x, y), (x+hw, y+hh), (0, 255, 0), 2)

        # 번호 표시 (크게)
        font_scale = max(0.8, min(hw, hh) / 50)
        thickness = max(2, int(font_scale * 2))

        # 배경 원 (가독성)
        text_size = cv2.getTextSize(str(hole_id), cv2.FONT_HERSHEY_BOLD,
                                    font_scale, thickness)[0]
        radius = max(text_size[0], text_size[1]) // 2 + 10

        cv2.circle(guide, (cx, cy), radius, (255, 255, 255), -1)
        cv2.circle(guide, (cx, cy), radius, (0, 0, 0), 2)

        # 번호 텍스트
        cv2.putText(guide, str(hole_id),
                   (cx - text_size[0]//2, cy + text_size[1]//2),
                   cv2.FONT_HERSHEY_BOLD, font_scale, (0, 0, 255), thickness)

    cv2.imwrite(f"{output_dir}/restoration_guide.png", guide)

    # 2. 인쇄 가능한 PDF
    create_printable_guide(image_path, holes_data, output_dir)

    # 3. 좌표 CSV
    save_piece_locations(holes_data, output_dir)

    print("Restoration guide created!")


def create_printable_guide(image_path, holes_data, output_dir):
    """인쇄 가능한 A4 복원 가이드"""

    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Image, Table, PageBreak

    pdf_path = f"{output_dir}/restoration_map.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []

    # 페이지 1: 전체 이미지 + 번호
    guide_img = Image(f"{output_dir}/restoration_guide.png",
                     width=190*mm, height=None)
    elements.append(guide_img)
    elements.append(PageBreak())

    # 페이지 2: 조각 목록 테이블
    table_data = [["번호", "위치 (x, y)", "크기 (w, h)", "면적"]]

    for hole in holes_data:
        x, y, w, h = hole['bbox']
        table_data.append([
            f"#{hole['id']}",
            f"({x}, {y})",
            f"{w} × {h}",
            f"{hole['area']} px²"
        ])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)

    doc.build(elements)
    print(f"Created: {pdf_path}")


def save_piece_locations(holes_data, output_dir):
    """번호별 위치 정보 CSV 저장"""

    import csv

    csv_path = f"{output_dir}/piece_locations.csv"

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['번호', 'X좌표', 'Y좌표', '너비', '높이', '면적(픽셀)', '면적(mm²)'])

        for hole in holes_data:
            x, y, w, h = hole['bbox']
            writer.writerow([
                hole['id'],
                x, y, w, h,
                hole['area_px'],
                hole['area_mm2']
            ])

    print(f"Created: {csv_path}")
```

**출력 예시**:

**restoration_guide.png**:
```
┌─────────────────────────────────┐
│  [원본 문서 이미지]              │
│                                 │
│     ①  ②   ③                   │
│                                 │
│        ④      ⑤               │
│   ⑥                            │
│              ⑦  ⑧             │
│                                 │
└─────────────────────────────────┘
```

**piece_locations.csv**:
```csv
번호,X좌표,Y좌표,너비,높이,면적(픽셀),면적(mm²)
1,961,2534,827,2878,1028962,7376.06
2,1183,5385,145,198,1308,9.38
3,1349,5381,112,156,940,6.74
...
```

---

### 2.2 Interactive 복원 가이드 (웹)

**HTML + JavaScript**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>복원 가이드</title>
    <style>
        #canvas { border: 1px solid #ccc; cursor: crosshair; }
        .piece-info { padding: 20px; border: 1px solid #ddd; }
        .highlight { background: yellow; }
    </style>
</head>
<body>
    <h1>복원 가이드</h1>

    <div style="display: flex;">
        <!-- 이미지 + 번호 -->
        <div>
            <canvas id="canvas"></canvas>
        </div>

        <!-- 조각 정보 -->
        <div class="piece-info">
            <h2>조각 정보</h2>
            <div id="selected-piece">
                <p>조각을 클릭하세요</p>
            </div>

            <!-- 조각 목록 -->
            <h3>전체 조각 (297개)</h3>
            <div id="piece-list" style="height: 400px; overflow-y: scroll;">
                <!-- 동적 생성 -->
            </div>
        </div>
    </div>

    <script>
        // 데이터 로드
        fetch('piece_locations.json')
            .then(r => r.json())
            .then(data => {
                initCanvas(data);
                createPieceList(data);
            });

        // 캔버스 초기화
        function initCanvas(pieces) {
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');

            // 원본 이미지 그리기
            const img = new Image();
            img.src = 'original.jpg';
            img.onload = () => {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);

                // 번호 그리기
                pieces.forEach(piece => {
                    drawPiece(ctx, piece);
                });
            };

            // 클릭 이벤트
            canvas.addEventListener('click', (e) => {
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                // 클릭한 위치의 조각 찾기
                const piece = findPieceAt(pieces, x, y);
                if (piece) {
                    showPieceDetails(piece);
                    highlightPiece(piece.id);
                }
            });
        }

        // 조각 그리기
        function drawPiece(ctx, piece) {
            const { id, x, y, w, h } = piece;
            const cx = x + w/2;
            const cy = y + h/2;

            // 윤곽선
            ctx.strokeStyle = 'lime';
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, w, h);

            // 번호 배경
            ctx.fillStyle = 'white';
            ctx.beginPath();
            ctx.arc(cx, cy, 20, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = 'black';
            ctx.stroke();

            // 번호 텍스트
            ctx.fillStyle = 'red';
            ctx.font = 'bold 16px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(id, cx, cy);
        }

        // 조각 상세 정보 표시
        function showPieceDetails(piece) {
            const html = `
                <h3>조각 #${piece.id}</h3>
                <p><strong>위치:</strong> (${piece.x}, ${piece.y})</p>
                <p><strong>크기:</strong> ${piece.w} × ${piece.h} px</p>
                <p><strong>면적:</strong> ${piece.area} px² (${piece.area_mm2} mm²)</p>
                <img src="svg_vectors/hole_${piece.id}.svg" width="200">
                <p>
                    <a href="svg_vectors/hole_${piece.id}.svg" download>
                        SVG 다운로드
                    </a>
                </p>
            `;
            document.getElementById('selected-piece').innerHTML = html;
        }

        // 조각 목록 생성
        function createPieceList(pieces) {
            const list = document.getElementById('piece-list');

            pieces.forEach(piece => {
                const item = document.createElement('div');
                item.id = `piece-item-${piece.id}`;
                item.style.padding = '10px';
                item.style.cursor = 'pointer';
                item.innerHTML = `
                    #${piece.id}: (${piece.x}, ${piece.y}) - ${piece.area} px²
                `;

                item.addEventListener('click', () => {
                    showPieceDetails(piece);
                    highlightPiece(piece.id);

                    // 캔버스에서 해당 위치로 스크롤
                    scrollToPosition(piece.x, piece.y);
                });

                list.appendChild(item);
            });
        }

        // 조각 하이라이트
        function highlightPiece(id) {
            // 기존 하이라이트 제거
            document.querySelectorAll('.highlight').forEach(el => {
                el.classList.remove('highlight');
            });

            // 새 하이라이트
            const item = document.getElementById(`piece-item-${id}`);
            if (item) {
                item.classList.add('highlight');
                item.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    </script>
</body>
</html>
```

---

## Phase 3: 통합 시스템

### 3.1 원스톱 처리

**파일**: `restoration_workflow.py`

```python
"""
통합 복원 워크플로우

사용법:
    python restoration_workflow.py --input w_0001.tif

출력:
    results/w_0001_restoration/
    ├── 1_detection/         # 검출 결과
    ├── 2_cutting_layout/    # 레이저 커팅 레이아웃
    ├── 3_restoration_guide/ # 복원 가이드
    └── report.pdf           # 통합 보고서
"""

def full_restoration_workflow(image_path, output_dir):
    """전체 워크플로우 실행"""

    print("=" * 60)
    print("문화재 복원 자동화 시스템")
    print("=" * 60)

    # Step 1: 손상 부위 검출
    print("\n[1/4] 손상 부위 검출 중...")
    detection_dir = f"{output_dir}/1_detection"
    result = detect_holes(image_path, detection_dir)
    print(f"✓ {result['total_holes']}개 구멍 검출 완료")

    # Step 2: SVG 벡터 생성
    print("\n[2/4] SVG 벡터 생성 중...")
    svg_dir = f"{detection_dir}/svg_vectors"
    print(f"✓ {len(os.listdir(svg_dir))}개 SVG 파일 생성")

    # Step 3: 레이저 커팅 레이아웃
    print("\n[3/4] 레이저 커팅 레이아웃 생성 중...")
    cutting_dir = f"{output_dir}/2_cutting_layout"
    pages = create_cutting_layout(svg_dir, cutting_dir, paper_size='A4')
    print(f"✓ {len(pages)}페이지 레이아웃 생성")
    print(f"  → {cutting_dir}/cutting_layout_all.pdf")

    # Step 4: 복원 가이드
    print("\n[4/4] 복원 가이드 생성 중...")
    guide_dir = f"{output_dir}/3_restoration_guide"
    create_restoration_guide(image_path, result['holes'], guide_dir)
    print(f"✓ 복원 가이드 생성 완료")
    print(f"  → {guide_dir}/restoration_guide.png")
    print(f"  → {guide_dir}/restoration_map.pdf")
    print(f"  → {guide_dir}/piece_locations.csv")

    # Step 5: 통합 보고서
    print("\n[5/5] 통합 보고서 생성 중...")
    generate_final_report(image_path, result, output_dir)
    print(f"✓ 보고서 생성 완료")
    print(f"  → {output_dir}/report.pdf")

    print("\n" + "=" * 60)
    print("✓ 모든 작업 완료!")
    print("=" * 60)
    print(f"\n결과 위치: {output_dir}")

    return {
        'holes': result['total_holes'],
        'pages': len(pages),
        'output_dir': output_dir
    }
```

---

### 3.2 GUI 도구

**PyQt6 기반 데스크톱 앱**:

```python
# main_gui.py

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *

class RestorationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("문화재 복원 자동화 시스템")
        self.setGeometry(100, 100, 1200, 800)
        self.setup_ui()

    def setup_ui(self):
        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 상단: 파일 선택
        file_group = QGroupBox("1. 이미지 선택")
        file_layout = QHBoxLayout()

        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("TIFF 또는 JPG 파일 선택...")

        btn_browse = QPushButton("찾아보기")
        btn_browse.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_input)
        file_layout.addWidget(btn_browse)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # 중간: 설정
        settings_group = QGroupBox("2. 설정")
        settings_layout = QFormLayout()

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setValue(138)
        self.threshold_spin.setRange(120, 150)

        self.min_area_spin = QSpinBox()
        self.min_area_spin.setValue(50)
        self.min_area_spin.setRange(10, 1000)

        self.paper_combo = QComboBox()
        self.paper_combo.addItems(['A4', 'A3'])

        settings_layout.addRow("색상 Threshold:", self.threshold_spin)
        settings_layout.addRow("최소 크기 (픽셀):", self.min_area_spin)
        settings_layout.addRow("용지 크기:", self.paper_combo)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # 실행 버튼
        btn_run = QPushButton("🚀 처리 시작")
        btn_run.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_run.clicked.connect(self.run_workflow)
        layout.addWidget(btn_run)

        # 진행률
        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        # 로그
        log_group = QGroupBox("3. 처리 로그")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 결과 버튼
        btn_layout = QHBoxLayout()

        btn_open_result = QPushButton("📁 결과 폴더 열기")
        btn_open_result.clicked.connect(self.open_result_folder)
        btn_open_result.setEnabled(False)
        self.btn_open_result = btn_open_result

        btn_view_guide = QPushButton("📋 복원 가이드 보기")
        btn_view_guide.clicked.connect(self.view_guide)
        btn_view_guide.setEnabled(False)
        self.btn_view_guide = btn_view_guide

        btn_layout.addWidget(btn_open_result)
        btn_layout.addWidget(btn_view_guide)
        layout.addLayout(btn_layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "이미지 선택",
            "",
            "Images (*.tif *.tiff *.jpg *.jpeg *.png)"
        )
        if file_path:
            self.file_input.setText(file_path)

    def run_workflow(self):
        """워크플로우 실행"""
        image_path = self.file_input.text()

        if not image_path:
            QMessageBox.warning(self, "경고", "이미지를 선택해주세요.")
            return

        # 백그라운드 스레드로 실행
        self.thread = WorkflowThread(
            image_path,
            self.threshold_spin.value(),
            self.min_area_spin.value(),
            self.paper_combo.currentText()
        )

        self.thread.progress.connect(self.update_progress)
        self.thread.log.connect(self.append_log)
        self.thread.finished_signal.connect(self.workflow_finished)

        self.thread.start()

    def update_progress(self, value):
        self.progress.setValue(value)

    def append_log(self, text):
        self.log_text.append(text)

    def workflow_finished(self, result):
        self.btn_open_result.setEnabled(True)
        self.btn_view_guide.setEnabled(True)
        self.result_dir = result['output_dir']

        QMessageBox.information(
            self,
            "완료",
            f"처리가 완료되었습니다!\n\n"
            f"검출된 구멍: {result['holes']}개\n"
            f"레이아웃 페이지: {result['pages']}장"
        )

    def open_result_folder(self):
        import subprocess
        subprocess.Popen(['explorer', self.result_dir])

    def view_guide(self):
        guide_path = f"{self.result_dir}/3_restoration_guide/restoration_guide.png"
        os.startfile(guide_path)


class WorkflowThread(QThread):
    """백그라운드 처리 스레드"""
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)

    def __init__(self, image_path, threshold, min_area, paper_size):
        super().__init__()
        self.image_path = image_path
        self.threshold = threshold
        self.min_area = min_area
        self.paper_size = paper_size

    def run(self):
        try:
            self.log.emit("처리 시작...")
            self.progress.emit(10)

            # 출력 디렉토리
            image_name = Path(self.image_path).stem
            output_dir = f"results/{image_name}_restoration"

            # 워크플로우 실행
            result = full_restoration_workflow(
                self.image_path,
                output_dir
            )

            self.progress.emit(100)
            self.finished_signal.emit(result)

        except Exception as e:
            self.log.emit(f"오류 발생: {e}")
            QMessageBox.critical(None, "오류", str(e))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RestorationApp()
    window.show()
    sys.exit(app.exec())
```

---

## 최종 워크플로우

### 연구원의 작업 절차 (개선 후)

```
┌─────────────────────────────────────────────┐
│ Step 1: 고문서 스캔                          │
│  → TIFF 파일 (7216x5412)                    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Step 2: 프로그램 실행 (클릭 1번!)            │
│  1. 이미지 선택                              │
│  2. "처리 시작" 클릭                         │
│  3. 커피 마시며 대기 ☕ (1-2분)              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Step 3: 레이저 커팅                          │
│  → cutting_layout_all.pdf 출력              │
│  → 레이저 커터에 넣고 실행                   │
│  → 조각들이 잘려서 나옴 (번호 표시됨!)       │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Step 4: 복원 작업                            │
│  → restoration_guide.png 보면서             │
│  → 각 조각을 번호에 맞춰 붙이기              │
│  → 위치를 까먹을 일 없음! ✅                │
└─────────────────────────────────────────────┘
```

### 시간 절감 효과

| 작업 | 이전 (수작업) | 이후 (자동화) | 절감 |
|------|-------------|-------------|------|
| 손상 부위 따기 | 2-3시간 | 1-2분 | **99%** ⚡ |
| 레이아웃 배치 | 1-2시간 | 자동 | **100%** ⚡ |
| 번호 매기기 | 30분 | 자동 | **100%** ⚡ |
| 위치 찾기 | 매번 혼란 | 즉시 확인 | **매우 편리** ✅ |

---

## 출력 파일 구조

```
results/w_0001_restoration/
│
├── 1_detection/                         # 검출 결과
│   ├── white_mask.png                   # 마스크 이미지
│   ├── comparison.png                   # 비교 이미지
│   ├── document_boundary.png            # 경계
│   ├── all_holes_vector.svg             # 통합 SVG
│   └── svg_vectors/                     # 개별 SVG (297개)
│       ├── hole_0001_x961_y2534_a1028962.svg
│       └── ...
│
├── 2_cutting_layout/                    # 🔥 레이저 커팅용
│   ├── cutting_layout_01.pdf            # A4, 1페이지
│   ├── cutting_layout_02.pdf            # A4, 2페이지
│   ├── cutting_layout_03.pdf            # A4, 3페이지
│   ├── cutting_layout_04.pdf            # A4, 4페이지
│   └── cutting_layout_all.pdf           # ⭐ 전체 통합 (인쇄용)
│
├── 3_restoration_guide/                 # 🔥 복원 가이드
│   ├── restoration_guide.png            # ⭐ 번호 오버레이 이미지
│   ├── restoration_map.pdf              # ⭐ 인쇄 가능한 가이드
│   ├── piece_locations.csv              # 번호별 좌표
│   └── viewer.html                      # 인터랙티브 뷰어
│
└── report.pdf                           # 📄 통합 보고서
```

---

## 다음 단계 우선순위

### 🥇 최우선
1. [ ] **레이저 커팅 레이아웃 생성기** (`create_cutting_layout.py`)
   - Bin packing 알고리즘
   - PDF 출력
   - 번호 표시

2. [ ] **복원 가이드 생성** (`create_restoration_guide.py`)
   - 번호 오버레이 이미지
   - 인쇄 가능한 PDF
   - CSV 좌표 리스트

### 🥈 2순위
3. [ ] **통합 워크플로우** (`restoration_workflow.py`)
   - 원스톱 처리
   - 진행률 표시

4. [ ] **GUI 도구** (PyQt6)
   - 파일 선택
   - 설정 조정
   - 결과 확인

### 🥉 3순위
5. [ ] **인터랙티브 뷰어** (HTML)
   - 조각 클릭 → 상세 정보
   - 위치 검색

6. [ ] **배치 처리**
   - 여러 문서 동시 처리

---

## 필요한 추가 라이브러리

```bash
pip install reportlab      # PDF 생성
pip install svglib         # SVG → PDF 변환
pip install PyQt6          # GUI (선택)
pip install Pillow         # 이미지 처리
```

---

**작성자**: Claude Code
**날짜**: 2025-10-30
**프로젝트**: 문화재 복원 자동화 시스템
**대상**: 문화재 복원 연구원
