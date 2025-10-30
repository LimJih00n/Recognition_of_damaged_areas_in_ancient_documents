# 3개 Edge Detection 모델 설치 가이드

## 📦 모델별 요구사항 요약

### 1️⃣ PiDiNet ✅ 즉시 사용 가능

**상태**: 설치 완료, 사전학습 모델 포함
**경로**: `pidinet/trained_models/`

**요구사항**:
```
✅ PyTorch 2.9.0 (설치 완료)
✅ OpenCV (설치 완료)
✅ NumPy, Pillow (설치 완료)
```

**사전학습 모델** (이미 있음):
- `table5_pidinet.pth` - 기본 모델 (권장)
- `table5_pidinet-tiny.pth` - 경량 모델
- `table5_pidinet-small.pth` - 중간 모델
- `table5_pidinet-l.pth` - 대형 모델

**즉시 실행 가능**:
```bash
source venv/bin/activate
python high_res_edge_detection.py \
    --image "datasets/1첩/w_0001.tif" \
    --model "pidinet/trained_models/table5_pidinet.pth"
```

---

### 2️⃣ DexiNed ⚠️ 체크포인트 다운로드 필요

**상태**: 저장소 클론 완료, 체크포인트 다운로드 필요

**요구사항**:
```
✅ PyTorch >=1.4 (2.9.0 설치됨)
✅ OpenCV (설치 완료)
✅ Kornia (설치 완료)
✅ Matplotlib, NumPy, h5py, PIL (설치 완료)
```

**❌ 체크포인트 다운로드 필요**:

**방법 1: Google Drive에서 직접 다운로드** (권장)
1. 다운로드 링크: https://drive.google.com/file/d/1V56vGTsu7GYiQouCIKvTWl5UKCZ6yCNu/view
2. 브라우저에서 다운로드 → `10_model.pth` 파일 저장
3. 저장 위치:
   ```bash
   mkdir -p DexiNed/checkpoints/BIPED/10/
   # 다운로드한 파일을 DexiNed/checkpoints/BIPED/10/에 복사
   ```

**방법 2: gdown 사용** (터미널에서)
```bash
source venv/bin/activate
pip install gdown
mkdir -p DexiNed/checkpoints/BIPED/10/
cd DexiNed/checkpoints/BIPED/10/
gdown 1V56vGTsu7GYiQouCIKvTWl5UKCZ6yCNu
cd ../../../../
```

**사용법**:
```bash
cd DexiNed
python main.py --choose_test_data=-1
# main.py에서 is_testing=True 설정 필요
```

---

### 3️⃣ EdgeNAT ⚠️ 복잡한 설치 필요

**상태**: 저장소 클론 완료, 의존성 및 가중치 다운로드 필요

**요구사항** (매우 복잡):
```
❌ PyTorch 1.11.0 + CUDA 11.3 (현재 2.9.0 설치됨)
❌ NATTEN (Neighborhood Attention)
❌ MMCV 1.4.8
❌ MMSegmentation 0.20.2
❌ timm (pytorch-image-models)
❌ fvcore 0.1.5
```

**⚠️ 주의**: EdgeNAT는 특정 버전 요구사항이 매우 엄격합니다. 현재 설치된 PyTorch 2.9와 호환되지 않을 수 있습니다.

**설치 순서** (별도 가상환경 권장):
```bash
# EdgeNAT 전용 가상환경 생성
python3 -m venv venv_edgenat
source venv_edgenat/bin/activate

# EdgeNAT 요구사항 설치
cd EdgeNAT
pip install -r requirements-base.txt  # PyTorch 1.11.0+cu113
pip install -r requirements.txt       # NATTEN, MMCV, MMSEG
cd ..
```

**❌ DiNAT 사전학습 가중치 다운로드 필요** (5개 파일):

저장 위치: `EdgeNAT/pretrained/`

1. **DiNAT-Mini**:
   - URL: https://shi-labs.com/projects/dinat/checkpoints/imagenet1k/dinat_mini_in1k_224.pth
   - 크기: ~24MB

2. **DiNAT-Tiny**:
   - URL: https://shi-labs.com/projects/dinat/checkpoints/imagenet1k/dinat_tiny_in1k_224.pth
   - 크기: ~27MB

3. **DiNAT-Small**:
   - URL: https://shi-labs.com/projects/dinat/checkpoints/imagenet1k/dinat_small_in1k_224.pth
   - 크기: ~51MB

4. **DiNAT-Base**:
   - URL: https://shi-labs.com/projects/dinat/checkpoints/imagenet1k/dinat_base_in1k_224.pth
   - 크기: ~91MB

5. **DiNAT-Large**:
   - URL: https://shi-labs.com/projects/dinat/checkpoints/imagenet22k/dinat_large_in22k_224.pth
   - 크기: ~210MB

**다운로드 스크립트**:
```bash
mkdir -p EdgeNAT/pretrained
cd EdgeNAT/pretrained

# wget 또는 curl 사용
wget https://shi-labs.com/projects/dinat/checkpoints/imagenet1k/dinat_mini_in1k_224.pth
wget https://shi-labs.com/projects/dinat/checkpoints/imagenet1k/dinat_tiny_in1k_224.pth
wget https://shi-labs.com/projects/dinat/checkpoints/imagenet1k/dinat_small_in1k_224.pth
wget https://shi-labs.com/projects/dinat/checkpoints/imagenet1k/dinat_base_in1k_224.pth
wget https://shi-labs.com/projects/dinat/checkpoints/imagenet22k/dinat_large_in22k_224.pth

cd ../..
```

**사용법**:
```bash
cd EdgeNAT
./tools/dist_train.sh configs/bsds/edgenat_l_320x320_40k_bsds.py 1
```

---

## 🎯 권장 실행 순서

### 단계 1: PiDiNet으로 즉시 테스트 (지금 바로 가능)
```bash
source venv/bin/activate
./run_detection.sh
```

### 단계 2: DexiNed 설치 및 테스트 (간단)
```bash
# 1. 체크포인트 다운로드 (Google Drive)
mkdir -p DexiNed/checkpoints/BIPED/10/
# 브라우저에서 다운로드 후 파일 복사

# 2. 테스트 실행
cd DexiNed
python main.py --choose_test_data=-1
```

### 단계 3: EdgeNAT 설치 (복잡, 선택적)
```bash
# Colab 사용 권장 (14GB VRAM)
# 로컬에서는 별도 가상환경 필요
```

---

## 💻 VRAM 및 시스템 요구사항

| 모델 | 최소 VRAM | 권장 환경 | 현재 시스템 호환성 |
|------|-----------|-----------|-------------------|
| PiDiNet | 0GB (CPU 가능) | 2GB | ✅ 완벽 호환 |
| DexiNed | 2GB | 4GB | ✅ 4GB로 충분 |
| EdgeNAT | 8GB | 12GB+ | ⚠️ Colab 권장 |

**현재 시스템**: 4GB VRAM
- PiDiNet: ✅ 즉시 사용 가능
- DexiNed: ✅ 체크포인트만 다운로드하면 사용 가능
- EdgeNAT: ⚠️ 로컬에서는 메모리 부족할 수 있음 → Colab 14GB 사용 권장

---

## 📊 설치 우선순위

### 우선순위 1: PiDiNet ⭐
- **이유**: 이미 설치 완료, 즉시 사용 가능
- **작업**: 없음, 바로 실행

### 우선순위 2: DexiNed ⭐⭐
- **이유**: 높은 정확도 (0.859), 간단한 설치
- **작업**: 체크포인트 1개만 다운로드

### 우선순위 3: EdgeNAT (선택적)
- **이유**: 최고 정확도 (0.860), 하지만 설치 복잡
- **작업**: 별도 환경 + 5개 가중치 다운로드 + 의존성 설치
- **대안**: Colab에서 실행

---

## 🚀 다음 단계

1. ✅ **PiDiNet 테스트** (즉시 가능)
   ```bash
   source venv/bin/activate
   ./run_detection.sh
   ```

2. ⏳ **DexiNed 체크포인트 다운로드**
   - Google Drive에서 수동 다운로드
   - 또는 gdown 사용

3. 🔜 **EdgeNAT 설치 결정**
   - 로컬 vs Colab 선택
   - 별도 가상환경 필요

4. 🔜 **3개 모델 비교 스크립트 작성**
   - 동일 이미지로 결과 비교
   - 시각화 및 성능 측정
