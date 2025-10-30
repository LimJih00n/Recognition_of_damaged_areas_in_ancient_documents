# ✅ 설치 완료 상태 및 실행 가이드

작성일: 2025-10-28
프로젝트: 문화재 손상 부위 Edge Detection

---

## 📦 설치 완료 상태

### ✅ 1. PiDiNet - 즉시 사용 가능
```
상태: ✅ 완료
모델: pidinet/trained_models/table5_pidinet.pth (있음)
의존성: ✅ PyTorch 2.9.0, OpenCV, NumPy
VRAM: 0GB (CPU 가능), 권장 2GB
성능: ODS 0.807, 100-200 FPS
```

**즉시 실행 가능**:
```bash
source venv/bin/activate
./run_detection.sh
```

---

### ✅ 2. DexiNed - 준비 완료
```
상태: ✅ 완료
체크포인트: DexiNed/checkpoints/BIPED/10/10_model.pth (135MB)
의존성: ✅ PyTorch, OpenCV, Kornia
VRAM: 2-4GB
성능: ODS 0.859 (PiDiNet보다 +5.2%)
```

**실행 방법**:
```bash
source venv/bin/activate
cd DexiNed
python main.py --choose_test_data=-1
```

---

### ⏳ 3. EdgeNAT - 가중치 다운로드 중
```
상태: ⏳ 가중치 다운로드 중 (4/5 완료)
다운로드 완료:
  ✅ dinat_mini_in1k_224.pth (76MB)
  ✅ dinat_tiny_in1k_224.pth (107MB)
  ✅ dinat_small_in1k_224.pth (194MB)
  ✅ dinat_base_in1k_224.pth (343MB)
  ⏳ dinat_large_in22k_224.pth (다운로드 중...)

의존성: ❌ NATTEN, MMCV, MMSEG 설치 필요
VRAM: 8-12GB (로컬 4GB로는 부족)
성능: ODS 0.860 (SOTA)
```

**주의**: EdgeNAT는 별도 가상환경 권장
- PyTorch 1.11.0 + CUDA 11.3 필요
- 현재 venv는 PyTorch 2.9.0 설치됨
- Colab (14GB VRAM) 사용 권장

---

## 🚀 빠른 시작 가이드

### 방법 1: PiDiNet 단독 실행 (초고속, CPU 가능)
```bash
source venv/bin/activate
./run_detection.sh
```

**결과 확인**:
- `results/pidinet/w_0001_edges.png` - Edge map
- `results/pidinet/w_0001_visualization.png` - 시각화

---

### 방법 2: PiDiNet vs DexiNed 비교 (권장)
```bash
source venv/bin/activate
./run_comparison.sh
```

**결과 확인**:
- `results/comparison/w_0001_comparison.png` - 나란히 비교
- `results/comparison/w_0001_PiDiNet.png` - PiDiNet 결과
- `results/comparison/w_0001_DexiNed.png` - DexiNed 결과

**성능 비교** (처리 시간도 함께 출력):
```
PiDiNet:  ~0.01초 (100 FPS) - 초고속
DexiNed:  ~0.5초 (2 FPS)    - 정확도 +5.2%
```

---

### 방법 3: 커스텀 이미지 실행
```bash
source venv/bin/activate

# PiDiNet 단독
python high_res_edge_detection.py \
    --image "datasets/1첩/w_0002.tif" \
    --model "pidinet/trained_models/table5_pidinet.pth" \
    --output-dir "results/pidinet"

# 2개 모델 비교
python compare_models.py \
    --image "datasets/1첩/w_0002.tif" \
    --output-dir "results/comparison" \
    --device cpu  # 또는 cuda
```

---

## 📊 모델 성능 비교 요약

| 항목 | PiDiNet | DexiNed | EdgeNAT |
|------|---------|---------|---------|
| **BSDS500 ODS** | 0.807 | 0.859 | **0.860** |
| **속도** | **100-200 FPS** | ~2 FPS | ~20 FPS |
| **모델 크기** | **<1MB** | ~50MB | ~200MB |
| **VRAM 요구** | **0GB (CPU 가능)** | 2-4GB | 8-12GB |
| **로컬 4GB VRAM** | ✅ 완벽 | ✅ 충분 | ❌ 부족 |
| **설치 난이도** | ✅ 쉬움 | ✅ 쉬움 | ❌ 어려움 |
| **현재 상태** | ✅ 사용 가능 | ✅ 사용 가능 | ⏳ 준비 중 |

---

## 💡 권장 사용 전략

### 1단계: PiDiNet으로 빠른 프로토타입 ⭐
```bash
./run_detection.sh
```
- **장점**: 초고속, CPU만으로 가능, 즉시 실행
- **결과**: 인간 성능(0.803) 이상의 정확도
- **용도**: 빠른 테스트, 전체 19개 이미지 일괄 처리

---

### 2단계: DexiNed로 정확도 업그레이드 ⭐⭐
```bash
./run_comparison.sh
```
- **장점**: +5.2% 높은 정확도 (0.859)
- **비교**: PiDiNet과 나란히 비교 가능
- **용도**: 최종 결과물, 논문/보고서용

---

### 3단계: EdgeNAT로 최고 정확도 (선택적)
```bash
# Colab에서 실행 권장
```
- **장점**: SOTA 정확도 (0.860)
- **단점**: 복잡한 설치, 높은 VRAM 요구
- **용도**: 연구 목적, 최고 성능 필요 시

---

## 📝 다음 작업

현재 상태에서 **즉시 가능한 작업**:

### ✅ 1. PiDiNet 테스트 (지금 바로)
```bash
source venv/bin/activate
./run_detection.sh
```

### ✅ 2. PiDiNet vs DexiNed 비교 (지금 바로)
```bash
source venv/bin/activate
./run_comparison.sh
```

### 🔜 3. 전체 19개 이미지 일괄 처리
```bash
# 스크립트 작성 필요
for img in datasets/1첩/*.tif; do
    python compare_models.py --image "$img"
done
```

### 🔜 4. Edge Map → SVG 변환 파이프라인
```python
# pypotrace 사용
# 1. Edge map 이진화
# 2. 윤곽선 추출
# 3. SVG 변환
# 4. 원본 좌표 매핑
```

### 🔜 5. EdgeNAT 설치 (선택적, Colab 권장)
```bash
# 별도 가상환경
python3 -m venv venv_edgenat
source venv_edgenat/bin/activate
cd EdgeNAT
pip install -r requirements-base.txt
pip install -r requirements.txt
```

---

## 🎯 핵심 성과

1. ✅ **3개 최신 Edge Detection 모델 조사 완료**
   - PiDiNet (2024.02 업데이트)
   - DexiNed (2022, ODS 0.859)
   - EdgeNAT (2024.08, SOTA 0.860)

2. ✅ **PiDiNet 즉시 사용 가능**
   - 사전학습 모델 포함
   - 고해상도 타일 처리 구현
   - CPU만으로 초고속 처리

3. ✅ **DexiNed 설치 완료**
   - 체크포인트 다운로드 완료 (135MB)
   - 비교 스크립트 작성 완료

4. ⏳ **EdgeNAT 가중치 다운로드 중**
   - 5개 중 4개 완료
   - 추가 의존성 설치 필요

5. ✅ **비교 시스템 구축 완료**
   - `compare_models.py` - 2개 모델 자동 비교
   - 처리 시간 측정 포함
   - 시각화 자동 생성

---

## 📁 프로젝트 파일 구조

```
riwum/
├── datasets/                       # 원본 TIFF 이미지
│   └── 1첩/                       # 19개 문화재 이미지
│
├── pidinet/                        # ✅ PiDiNet 모델
│   └── trained_models/            # 사전학습 모델 (9개)
│       └── table5_pidinet.pth     # 기본 모델
│
├── DexiNed/                        # ✅ DexiNed 모델
│   └── checkpoints/BIPED/10/      # 체크포인트
│       └── 10_model.pth           # 135MB
│
├── EdgeNAT/                        # ⏳ EdgeNAT 모델
│   └── pretrained/                # DiNAT 가중치 (4/5 완료)
│       ├── dinat_mini_in1k_224.pth   ✅
│       ├── dinat_tiny_in1k_224.pth   ✅
│       ├── dinat_small_in1k_224.pth  ✅
│       ├── dinat_base_in1k_224.pth   ✅
│       └── dinat_large_in22k_224.pth ⏳
│
├── results/                        # 결과물
│   ├── opencv/                    # OpenCV 테스트 결과
│   ├── pidinet/                   # PiDiNet 결과
│   └── comparison/                # 모델 비교 결과
│
├── venv/                           # Python 가상환경
│   └── ...                        # PyTorch 2.9.0 설치됨
│
├── high_res_edge_detection.py     # PiDiNet 고해상도 처리
├── compare_models.py               # 모델 비교 스크립트
├── run_detection.sh                # PiDiNet 실행
├── run_comparison.sh               # 비교 실행
├── download_dexined_checkpoint.sh  # DexiNed 다운로드
├── download_edgenat_weights.sh     # EdgeNAT 다운로드
│
├── MODEL_COMPARISON.md             # 모델 상세 비교
├── MODEL_SETUP_GUIDE.md            # 설치 가이드
├── SUMMARY.md                      # 프로젝트 요약
├── README.md                       # 사용 가이드
└── SETUP_COMPLETE.md               # 이 파일
```

---

## 💻 시스템 요구사항

**현재 시스템**:
- OS: Linux (WSL2)
- VRAM: 4GB
- Python: 3.12
- PyTorch: 2.9.0 + CUDA 12.8

**모델별 호환성**:
- PiDiNet: ✅ 완벽 (CPU만으로도 가능)
- DexiNed: ✅ 충분 (4GB VRAM으로 가능)
- EdgeNAT: ⚠️ 부족 (8-12GB VRAM 필요)

---

## 🔗 참고 링크

- **PiDiNet**: https://github.com/hellozhuo/pidinet
- **DexiNed**: https://github.com/xavysp/DexiNed
- **EdgeNAT**: https://github.com/jhjie/EdgeNAT
- **BSDS500 Benchmark**: https://paperswithcode.com/sota/edge-detection-on-bsds500-1

---

## ⚡ 즉시 실행 명령어

```bash
# PiDiNet 단독 실행 (초고속)
source venv/bin/activate && ./run_detection.sh

# PiDiNet vs DexiNed 비교 (권장)
source venv/bin/activate && ./run_comparison.sh

# 결과 확인
ls -lh results/comparison/
```

---

**상태**: 2개 모델(PiDiNet, DexiNed) 즉시 사용 가능 ✅
**다음**: EdgeNAT 가중치 다운로드 완료 대기 중 ⏳
