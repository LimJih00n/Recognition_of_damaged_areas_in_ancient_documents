# 고문서 손상 검출 시스템 - 다음 단계 계획

**작성일**: 2025-10-30
**현재 상태**: 타일 경계 감지 + SVG 벡터화 완료

---

## 📋 목차

1. [현재 완성된 기능](#현재-완성된-기능)
2. [다음 단계 개요](#다음-단계-개요)
3. [Phase 1: 전체 이미지 테스트](#phase-1-전체-이미지-테스트)
4. [Phase 2: 시각화 개선](#phase-2-시각화-개선)
5. [Phase 3: 실용화 (배포)](#phase-3-실용화-배포)
6. [타임라인](#타임라인)
7. [기술 스택](#기술-스택)

---

## 현재 완성된 기능

### ✅ 핵심 기능
- [x] LAB b-channel 기반 구멍 감지 (b < 138)
- [x] 타일 스캔 이미지 경계 자동 감지
- [x] 해상도 자동 스케일링
- [x] SVG 벡터 출력 (원본 형태 보존)
- [x] 개별 SVG 중앙 배치
- [x] 구멍 번호 추적 및 시각화
- [x] 한글 경로 지원

### ✅ 처리된 이미지
- test_small.jpg (1443x1082) - 268개 구멍
- w_0001.tif (7216x5412) - 297개 구멍
- w_0002.tif (7216x5412) - 260개 구멍
- w_0003.tif (7216x5412) - 188개 구멍
- w_0005.tif (7216x5412) - 163개 구멍

### ✅ 출력 결과
- PNG 마스크 (흑백)
- SVG 벡터 (통합 + 개별)
- 비교 이미지 (원본 vs 검출)
- 경계 시각화
- 검증 이미지 (번호 표시)

---

## 다음 단계 개요

```
Phase 1: 전체 이미지 테스트 (1-2일)
  ├─ 모든 이미지 일괄 처리
  ├─ 결과 품질 검증
  └─ 통계 분석

Phase 2: 시각화 개선 (1-2일)
  ├─ 원본 + 마스크 오버레이
  ├─ 인터랙티브 비교 뷰어
  └─ 보고서 자동 생성

Phase 3: 실용화 - 배포 (3-5일)
  ├─ Option A: 웹 서비스
  ├─ Option B: 데스크톱 앱
  └─ Option C: CLI 도구 + GUI
```

---

## Phase 1: 전체 이미지 테스트

### 목표
- datasets 폴더의 모든 이미지 처리
- 품질 검증 및 통계 수집
- 문제점 발견 및 수정

---

### 1.1 배치 처리 스크립트

**파일**: `batch_process.py`

```python
"""
모든 이미지 자동 처리

사용법:
    python batch_process.py --input-dir datasets/1첩 --output-dir results/batch_1
"""

import os
import glob
import subprocess
from pathlib import Path

def process_all_images(input_dir, output_dir, params):
    """폴더 내 모든 이미지 처리"""

    # 이미지 파일 찾기
    images = glob.glob(f"{input_dir}/**/*.tif", recursive=True)
    images += glob.glob(f"{input_dir}/**/*.jpg", recursive=True)

    print(f"Found {len(images)} images")

    results = []

    for i, image_path in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] Processing: {image_path}")

        # 출력 디렉토리 생성
        image_name = Path(image_path).stem
        out_dir = f"{output_dir}/{image_name}"

        # 처리 명령 실행
        cmd = [
            "python", "extract_whiteness_based.py",
            "--input", image_path,
            "--method", "lab_b",
            "--s-threshold", str(params['threshold']),
            "--min-area", str(params['min_area']),
            "--max-area", str(params['max_area']),
            "--crop-document",
            "--corner-method", "edges",
            "--export-svg",
            "--svg-simplify", str(params['svg_simplify']),
            "--svg-individual",
            "--output-dir", out_dir
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            # 결과 파싱
            holes = extract_hole_count(result.stdout)

            results.append({
                'image': image_name,
                'holes': holes,
                'status': 'success' if result.returncode == 0 else 'failed'
            })

        except Exception as e:
            print(f"Error: {e}")
            results.append({
                'image': image_name,
                'status': 'error',
                'error': str(e)
            })

    # 결과 저장
    save_batch_report(results, output_dir)

    return results


def save_batch_report(results, output_dir):
    """배치 처리 결과 리포트 생성"""

    report = f"""# 배치 처리 결과

처리 일시: {datetime.now()}
총 이미지: {len(results)}
성공: {sum(1 for r in results if r['status'] == 'success')}
실패: {sum(1 for r in results if r['status'] != 'success')}

## 상세 결과

| 이미지 | 구멍 개수 | 상태 |
|--------|----------|------|
"""

    for r in results:
        holes = r.get('holes', '-')
        report += f"| {r['image']} | {holes} | {r['status']} |\n"

    with open(f"{output_dir}/batch_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport saved: {output_dir}/batch_report.md")


if __name__ == '__main__':
    # 파라미터 설정
    params = {
        'threshold': 138,
        'min_area': 50,
        'max_area': 2500000,
        'svg_simplify': 0.1
    }

    # 실행
    process_all_images("datasets/1첩", "results/batch_1", params)
```

---

### 1.2 품질 검증

**파일**: `verify_batch_results.py`

```python
"""
배치 처리 결과 품질 검증

- 모든 SVG 파일 검증
- 통계 수집
- 이상치 감지
"""

def verify_batch_quality(results_dir):
    """결과 품질 검증"""

    issues = []
    stats = []

    for result_dir in glob.glob(f"{results_dir}/*"):
        # 필수 파일 확인
        required = [
            'all_holes_vector.svg',
            'comparison.png',
            'document_boundary.png'
        ]

        for file in required:
            if not os.path.exists(f"{result_dir}/{file}"):
                issues.append(f"Missing: {result_dir}/{file}")

        # 통계 수집
        stats_file = f"{result_dir}/stats.json"
        if os.path.exists(stats_file):
            with open(stats_file) as f:
                stats.append(json.load(f))

    # 이상치 감지
    hole_counts = [s['total_holes'] for s in stats]
    mean = np.mean(hole_counts)
    std = np.std(hole_counts)

    for s in stats:
        if abs(s['total_holes'] - mean) > 3 * std:
            issues.append(f"Outlier: {s['image']} has {s['total_holes']} holes")

    return issues, stats
```

---

### 1.3 통계 분석

**생성할 통계**:
- 이미지별 구멍 개수
- 구멍 크기 분포
- 타일 경계 감지 성공률
- 평균 처리 시간
- SVG 파일 크기

**출력**: `results/batch_1/statistics.md`

---

## Phase 2: 시각화 개선

### 목표
- 원본 이미지에 마스크 오버레이
- 인터랙티브 비교 기능
- 자동 보고서 생성

---

### 2.1 마스크 오버레이

**파일**: `create_overlay.py`

```python
"""
원본 이미지에 구멍 마스크 오버레이

출력:
  - overlay_red.png: 빨간색 반투명
  - overlay_heatmap.png: 히트맵
  - side_by_side.png: 원본 | 오버레이
"""

def create_mask_overlay(image_path, mask_path, output_path):
    """원본 + 마스크 오버레이 생성"""

    # 이미지 로드
    image = cv2.imread(image_path)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

    # 1. 빨간색 반투명 오버레이
    overlay_red = image.copy()
    overlay_red[mask > 0] = [0, 0, 255]  # 빨간색
    result = cv2.addWeighted(image, 0.7, overlay_red, 0.3, 0)
    cv2.imwrite(f"{output_path}_red.png", result)

    # 2. 히트맵 (구멍 밀도)
    heatmap = cv2.applyColorMap(mask, cv2.COLORMAP_JET)
    result = cv2.addWeighted(image, 0.5, heatmap, 0.5, 0)
    cv2.imwrite(f"{output_path}_heatmap.png", result)

    # 3. Side-by-side 비교
    side_by_side = np.hstack([image, overlay_red])
    cv2.imwrite(f"{output_path}_side_by_side.png", side_by_side)
```

**예시 출력**:
```
results/w_0001/
├── overlay_red.png           # 원본 + 빨간 마스크 (70% + 30%)
├── overlay_heatmap.png        # 히트맵 스타일
└── side_by_side.png           # 원본 | 오버레이 비교
```

---

### 2.2 인터랙티브 비교 뷰어

**파일**: `html_viewer.py`

```python
"""
HTML 인터랙티브 뷰어 생성

기능:
  - 슬라이더로 원본/마스크 비교
  - 구멍 클릭 → 상세 정보
  - SVG 다운로드 링크
"""

def create_html_viewer(result_dir):
    """HTML 뷰어 생성"""

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>구멍 검출 결과</title>
    <style>
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .slider {{ width: 100%; }}
        #canvas {{ border: 1px solid #ccc; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>구멍 검출 결과</h1>

        <!-- 슬라이더 비교 -->
        <div id="comparison">
            <input type="range" class="slider"
                   min="0" max="100" value="50"
                   oninput="updateOpacity(this.value)">
            <canvas id="canvas"></canvas>
        </div>

        <!-- 구멍 목록 -->
        <h2>검출된 구멍 (163개)</h2>
        <div id="holes-list">
            <!-- 동적 생성 -->
        </div>

        <!-- 다운로드 링크 -->
        <h2>다운로드</h2>
        <ul>
            <li><a href="all_holes_vector.svg">전체 SVG</a></li>
            <li><a href="white_mask.png">마스크 이미지</a></li>
        </ul>
    </div>

    <script>
        // 슬라이더로 투명도 조절
        function updateOpacity(value) {{
            const overlay = document.getElementById('overlay');
            overlay.style.opacity = value / 100;
        }}

        // 구멍 클릭 시 상세 정보
        function showHoleDetails(holeId) {{
            // SVG 메타데이터 표시
            fetch(`svg_vectors/hole_${{holeId}}.svg`)
                .then(r => r.text())
                .then(showDetails);
        }}
    </script>
</body>
</html>
"""

    with open(f"{result_dir}/viewer.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Viewer created: {result_dir}/viewer.html")
```

---

### 2.3 자동 보고서 생성

**파일**: `generate_report.py`

```python
"""
PDF/HTML 보고서 자동 생성

포함 내용:
  - 원본 이미지 미리보기
  - 구멍 검출 통계
  - 오버레이 이미지
  - 구멍 목록 (위치, 크기)
  - SVG 다운로드 링크
"""

def generate_report(result_dir, format='html'):
    """보고서 생성"""

    # 데이터 수집
    stats = load_statistics(f"{result_dir}/stats.json")

    # HTML 보고서
    if format == 'html':
        html = f"""
        <html>
        <body>
            <h1>고문서 손상 검출 보고서</h1>
            <h2>요약</h2>
            <ul>
                <li>총 구멍 개수: {stats['total_holes']}</li>
                <li>평균 크기: {stats['avg_area']:.1f} 픽셀</li>
                <li>총 손상 면적: {stats['total_area']:.1f} 픽셀</li>
            </ul>

            <h2>시각화</h2>
            <img src="comparison.png" width="800">
            <img src="overlay_red.png" width="800">

            <h2>구멍 목록</h2>
            <table>
                <tr><th>ID</th><th>위치</th><th>크기</th></tr>
                {generate_hole_table(stats['holes'])}
            </table>
        </body>
        </html>
        """

        with open(f"{result_dir}/report.html", "w") as f:
            f.write(html)

    # PDF 변환
    if format == 'pdf':
        # weasyprint 또는 reportlab 사용
        from weasyprint import HTML
        HTML(f"{result_dir}/report.html").write_pdf(
            f"{result_dir}/report.pdf"
        )
```

---

## Phase 3: 실용화 (배포)

### 목표
- 일반 사용자가 쉽게 사용할 수 있도록
- 설치 및 실행 간소화
- 안정적인 배포

---

### Option A: 웹 서비스 (추천) 🌟

**장점**:
- 설치 불필요
- 어디서나 접근 가능
- 업데이트 쉬움
- 결과 공유 용이

**기술 스택**:
```
Frontend: React + TypeScript
Backend: FastAPI (Python)
Storage: Local / S3
Deploy: Docker + Nginx
```

**구조**:
```
web_service/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ImageUpload.tsx
│   │   │   ├── ResultViewer.tsx
│   │   │   └── SVGDownloader.tsx
│   │   └── App.tsx
│   └── package.json
│
├── backend/
│   ├── main.py              # FastAPI 서버
│   ├── detector.py          # 기존 코드 래핑
│   └── requirements.txt
│
└── docker-compose.yml
```

**API 설계**:
```python
# backend/main.py

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import shutil

app = FastAPI()

@app.post("/api/detect")
async def detect_holes(
    file: UploadFile = File(...),
    threshold: int = 138,
    min_area: int = 50
):
    """구멍 검출 API"""

    # 파일 저장
    file_path = f"temp/{file.filename}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 처리
    result = process_image(file_path, threshold, min_area)

    return {
        "holes": result['holes'],
        "svg_url": f"/results/{result['id']}/all_holes_vector.svg",
        "image_url": f"/results/{result['id']}/comparison.png"
    }


@app.get("/api/results/{result_id}")
async def get_result(result_id: str):
    """결과 조회"""
    return load_result(result_id)


@app.get("/api/download/{result_id}/{file_type}")
async def download_file(result_id: str, file_type: str):
    """파일 다운로드 (SVG, PNG 등)"""
    file_path = f"results/{result_id}/{file_type}"
    return FileResponse(file_path)
```

**Frontend**:
```tsx
// frontend/src/App.tsx

function App() {
  const [image, setImage] = useState(null);
  const [result, setResult] = useState(null);

  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/detect', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();
    setResult(data);
  };

  return (
    <div>
      <h1>고문서 손상 검출 시스템</h1>

      <ImageUpload onUpload={handleUpload} />

      {result && (
        <ResultViewer
          holes={result.holes}
          imageUrl={result.image_url}
          svgUrl={result.svg_url}
        />
      )}
    </div>
  );
}
```

**배포**:
```yaml
# docker-compose.yml

version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./results:/app/results

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend
```

---

### Option B: 데스크톱 앱

**기술 스택**:
```
Electron + Python
또는
PyQt6 / PySide6
```

**장점**:
- 오프라인 사용 가능
- 로컬 파일 접근 쉬움
- 네이티브 성능

**구조**:
```
desktop_app/
├── main.py                  # PyQt6 메인
├── ui/
│   ├── main_window.py
│   ├── result_viewer.py
│   └── settings_dialog.py
├── core/
│   └── detector.py          # 기존 코드
└── resources/
    └── icons/
```

**예시**:
```python
# main.py (PyQt6)

from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtCore import QThread, pyqtSignal

class DetectorThread(QThread):
    """백그라운드 처리 스레드"""
    finished = pyqtSignal(dict)

    def __init__(self, image_path, params):
        super().__init__()
        self.image_path = image_path
        self.params = params

    def run(self):
        result = process_image(self.image_path, **self.params)
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("고문서 손상 검출")
        self.setup_ui()

    def setup_ui(self):
        # 파일 선택 버튼
        self.btn_open = QPushButton("이미지 열기")
        self.btn_open.clicked.connect(self.open_image)

        # 처리 버튼
        self.btn_process = QPushButton("검출 시작")
        self.btn_process.clicked.connect(self.start_detection)

        # 결과 뷰어
        self.result_viewer = ResultViewer()

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "",
            "Images (*.tif *.jpg *.png)"
        )
        if file_path:
            self.image_path = file_path
            self.display_image(file_path)

    def start_detection(self):
        params = self.get_params()

        self.thread = DetectorThread(self.image_path, params)
        self.thread.finished.connect(self.show_result)
        self.thread.start()

    def show_result(self, result):
        self.result_viewer.display(result)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

**패키징**:
```bash
# PyInstaller로 실행 파일 생성
pyinstaller --onefile --windowed main.py

# 또는 cx_Freeze
python setup.py build
```

---

### Option C: CLI 도구 + 간단한 GUI (절충안)

**장점**:
- 빠른 구현
- CLI와 GUI 동시 제공
- 유연성

**구조**:
```
cli_gui/
├── cli.py                   # 기존 extract_whiteness_based.py 개선
├── gui.py                   # 간단한 tkinter GUI
└── README.md
```

**GUI 예시**:
```python
# gui.py (tkinter)

import tkinter as tk
from tkinter import filedialog, ttk
import subprocess

class SimpleGUI:
    def __init__(self, root):
        self.root = root
        root.title("고문서 손상 검출")

        # 파일 선택
        ttk.Label(root, text="이미지:").grid(row=0, column=0)
        self.entry_file = ttk.Entry(root, width=50)
        self.entry_file.grid(row=0, column=1)
        ttk.Button(root, text="찾기",
                  command=self.browse_file).grid(row=0, column=2)

        # 파라미터
        ttk.Label(root, text="Threshold:").grid(row=1, column=0)
        self.entry_threshold = ttk.Entry(root)
        self.entry_threshold.insert(0, "138")
        self.entry_threshold.grid(row=1, column=1)

        # 실행 버튼
        ttk.Button(root, text="검출 시작",
                  command=self.run_detection).grid(row=5, column=1)

        # 로그
        self.text_log = tk.Text(root, height=20, width=80)
        self.text_log.grid(row=6, column=0, columnspan=3)

    def browse_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Images", "*.tif *.jpg *.png")]
        )
        self.entry_file.delete(0, tk.END)
        self.entry_file.insert(0, filename)

    def run_detection(self):
        cmd = [
            "python", "extract_whiteness_based.py",
            "--input", self.entry_file.get(),
            "--s-threshold", self.entry_threshold.get(),
            # ...
        ]

        # 백그라운드 실행
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 로그 표시
        for line in process.stdout:
            self.text_log.insert(tk.END, line.decode())
            self.text_log.see(tk.END)


if __name__ == '__main__':
    root = tk.Tk()
    app = SimpleGUI(root)
    root.mainloop()
```

---

## 타임라인

### Week 1: 테스트 및 검증
- **Day 1-2**: Phase 1 (배치 처리)
  - [x] 배치 스크립트 작성
  - [ ] 모든 이미지 처리
  - [ ] 결과 검증

- **Day 3-4**: Phase 2 (시각화)
  - [ ] 마스크 오버레이
  - [ ] HTML 뷰어
  - [ ] 보고서 생성

### Week 2: 배포
- **Day 5-7**: Phase 3-A (웹 서비스)
  - [ ] FastAPI 백엔드
  - [ ] React 프론트엔드
  - [ ] Docker 배포

- **또는 Day 5-7**: Phase 3-B (데스크톱)
  - [ ] PyQt6 GUI
  - [ ] 패키징
  - [ ] 설치 프로그램

### Week 3: 개선 및 문서화
- **Day 8-10**:
  - [ ] 사용자 피드백 반영
  - [ ] 문서화 (사용 설명서)
  - [ ] 최종 테스트

---

## 기술 스택

### Phase 1-2: 테스트 & 시각화
```
Python 3.9+
├── OpenCV
├── NumPy
├── Pillow
└── Matplotlib
```

### Phase 3-A: 웹 서비스
```
Backend:
├── FastAPI
├── Uvicorn
├── Pydantic
└── Python-multipart

Frontend:
├── React 18
├── TypeScript
├── Axios
└── TailwindCSS

Deploy:
├── Docker
├── Docker Compose
└── Nginx
```

### Phase 3-B: 데스크톱 앱
```
GUI:
├── PyQt6 (추천)
└── 또는 Electron + Python

패키징:
├── PyInstaller
└── 또는 cx_Freeze
```

### Phase 3-C: CLI + GUI
```
├── Click (CLI 개선)
├── Tkinter (간단한 GUI)
└── tqdm (진행률)
```

---

## 우선순위 권장

### 🥇 1순위: 웹 서비스 (Option A)
**이유**:
- ✅ 가장 접근성 좋음
- ✅ 설치 불필요
- ✅ 결과 공유 쉬움
- ✅ 업데이트 관리 용이
- ✅ 클라우드 스토리지 활용 가능

### 🥈 2순위: CLI + 간단한 GUI (Option C)
**이유**:
- ✅ 빠른 구현
- ✅ 기존 코드 재사용
- ✅ CLI와 GUI 모두 제공
- ⚠️ 고급 기능 제한적

### 🥉 3순위: 데스크톱 앱 (Option B)
**이유**:
- ✅ 오프라인 사용
- ⚠️ 개발 시간 많이 소요
- ⚠️ 각 OS별 빌드 필요
- ⚠️ 업데이트 배포 복잡

---

## 필요한 추가 작업

### 공통
- [ ] 에러 핸들링 개선
- [ ] 로깅 시스템
- [ ] 설정 파일 (config.yaml)
- [ ] 사용자 매뉴얼

### 웹 서비스 (Option A)
- [ ] 사용자 인증 (선택)
- [ ] 파일 업로드 제한
- [ ] 결과 저장 기간 설정
- [ ] HTTPS 설정

### 데스크톱 앱 (Option B)
- [ ] 자동 업데이트
- [ ] 설정 저장/로드
- [ ] 배치 처리 UI
- [ ] 진행률 표시

---

## 예상 리소스

### 개발 시간
- Phase 1: 2일
- Phase 2: 2일
- Phase 3-A (웹): 5일
- Phase 3-B (데스크톱): 5일
- Phase 3-C (CLI+GUI): 2일

### 서버 스펙 (웹 서비스)
```
최소:
- CPU: 4 cores
- RAM: 8GB
- Storage: 100GB SSD

권장:
- CPU: 8 cores
- RAM: 16GB
- Storage: 500GB SSD
- GPU: NVIDIA (선택, 속도 향상)
```

---

## 다음 액션 아이템

### 즉시 시작
1. [ ] `batch_process.py` 작성
2. [ ] 전체 이미지 처리 시작
3. [ ] 결과 품질 검증

### 병렬 진행 가능
- [ ] `create_overlay.py` 작성
- [ ] HTML 뷰어 프로토타입
- [ ] 웹 서비스 API 설계

### 결정 필요
- [ ] 배포 방식 선택 (A/B/C)
- [ ] 서버 준비 (웹 서비스 선택 시)
- [ ] 도메인 등록 (웹 서비스 선택 시)

---

## 참고 자료

### 현재 구현된 기능
- `worklog/2025-10-30_tile_aware_document_boundary_detection.md`
- `worklog/2025-10-30_svg_optimization_and_visualization.md`
- `worklog/FINAL_SUMMARY_hole_detection_b138.md`

### 유사 프로젝트
- IIIF Image API (이미지 서비스)
- OpenCV.js (웹 브라우저 CV)
- Papermill (문서 스캔 앱)

---

**작성자**: Claude Code
**날짜**: 2025-10-30
**프로젝트**: 고문서 손상 자동 검출 시스템
**상태**: 계획 단계
