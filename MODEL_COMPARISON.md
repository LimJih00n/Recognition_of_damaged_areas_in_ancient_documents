# 3개 Edge Detection 모델 비교

## 📊 성능 및 사양 비교

| 항목 | PiDiNet | DexiNed | EdgeNAT | 승자 |
|------|---------|---------|---------|------|
| **BSDS500 ODS** | 0.807 | 0.859 | **0.860** | 🥇 EdgeNAT |
| **속도 (FPS)** | **100-200** | 빠름 | 20 | 🥇 PiDiNet |
| **모델 크기** | **<1M** | 수 MB | 큼 | 🥇 PiDiNet |
| **GPU 필수** | ❌ (CPU 가능) | 권장 | ✅ 필수 | 🥇 PiDiNet |
| **발표 연도** | 2021/2024 | 2020/2022 | **2024.08** | 🥇 EdgeNAT |
| **4GB VRAM** | ✅ | ✅ | ⚠️ (확인 필요) | PiDiNet/DexiNed |
| **설치 난이도** | 쉬움 | 쉬움 | **어려움** | PiDiNet/DexiNed |

---

## 🎯 각 모델 상세

### 1️⃣ PiDiNet (Pixel Difference Network)

**GitHub**: https://github.com/hellozhuo/pidinet

**장점**:
```
✅ 초고속: 100-200 FPS
✅ 초경량: <1M 파라미터
✅ CPU 실행 가능
✅ 사전학습 모델 포함됨 ⭐
✅ 설치 간단
✅ 2024년 2월 업데이트
✅ 4GB VRAM으로 충분
```

**단점**:
```
❌ 정확도 3위 (0.807)
❌ DexiNed/EdgeNAT보다 5-6% 낮음
```

**설치**:
```bash
# 이미 완료!
# 사전학습 모델: pidinet/trained_models/table5_pidinet.pth
```

**사용**:
```bash
python high_res_edge_detection.py \
    --model pidinet/trained_models/table5_pidinet.pth \
    --image "datasets/1첩/w_0001.tif"
```

---

### 2️⃣ DexiNed (Dense Extreme Inception Network)

**GitHub**: https://github.com/xavysp/DexiNed

**장점**:
```
✅ 고정확도: 0.859 (2위)
✅ 검증된 모델 (WACV 2020)
✅ 설치 비교적 간단
✅ PyTorch 지원
✅ 4GB VRAM으로 충분
```

**단점**:
```
❌ EdgeNAT보다 0.001 낮음
❌ GPU 권장
❌ PiDiNet보다 느림
```

**설치**:
```bash
# 체크포인트 다운로드 필요
# https://drive.google.com/file/d/1V56vGTsu7GYiQouCIKvTWl5UKCZ6yCNu/view
# DexiNed/checkpoints/BIPED/10/에 저장
```

---

### 3️⃣ EdgeNAT (Transformer for Edge Detection)

**GitHub**: https://github.com/jhjie/EdgeNAT

**장점**:
```
✅ 최고 정확도: 0.860 (SOTA!) ⭐
✅ 2024년 8월 최신
✅ Transformer 기반 (최신 기술)
✅ EDTER보다 1.2% 향상
```

**단점**:
```
❌ 복잡한 설치 (NATTEN, MMCV, MMSEG)
❌ GPU 필수
❌ 느림: 20 FPS
❌ 큰 모델 크기
❌ 4GB VRAM 부족할 수 있음
```

**설치**:
```bash
pip install -r requirements-base.txt
pip install -r requirements.txt
# 사전학습 가중치 다운로드 필요 (5개 파일)
```

---

## 💡 어떤 모델을 선택해야 할까?

### 🏆 **상황별 추천**

#### 1. 최고 정확도 필요 (논문, 연구)
→ **EdgeNAT** (Colab 14GB VRAM 사용)
- ODS 0.860 (절대 1위)
- 문화재 손상 정밀 감지

#### 2. 안정성 + 높은 정확도
→ **DexiNed** (로컬 4GB VRAM)
- ODS 0.859 (EdgeNAT과 거의 동일)
- 검증된 모델
- 설치 비교적 쉬움

#### 3. 실용성 + 속도
→ **PiDiNet** (로컬 CPU or GPU)
- ODS 0.807 (인간보다 우수)
- 100배 빠름
- CPU만으로 가능

---

## 🚀 추천 전략

### 방법 1: PiDiNet으로 빠른 프로토타입 (지금)
```
1. PiDiNet으로 먼저 테스트 (사전학습 모델 이미 있음)
2. 결과 확인
3. 만족하면 사용, 부족하면 → 다음
```

### 방법 2: DexiNed로 업그레이드 (로컬)
```
1. 체크포인트 다운로드
2. 4GB VRAM으로 실행
3. PiDiNet과 비교
```

### 방법 3: EdgeNAT로 최종 (Colab)
```
1. Colab에 업로드
2. 14GB VRAM 활용
3. 최고 정확도로 최종 결과
```

---

## 📝 현재 상황

✅ **완료**:
- PyTorch 2.9 설치 완료
- 3개 모델 모두 클론 완료
- PiDiNet 사전학습 모델 있음
- 고해상도 타일 처리 스크립트 작성

⏳ **진행 중**:
- DexiNed 클론 재시도 중

🔜 **다음 단계**:
1. PiDiNet 먼저 테스트
2. DexiNed 체크포인트 다운로드
3. EdgeNAT 설치 (Colab 고려)
4. 3개 모델 비교 실행

---

## 🎬 실행 순서 제안

```bash
# 1단계: PiDiNet 테스트 (지금 바로 가능)
source venv/bin/activate
python high_res_edge_detection.py \
    --image "datasets/1첩/w_0001.tif" \
    --device cuda  # 또는 cpu

# 2단계: 결과 확인
# results/pidinet/w_0001_edges.png

# 3단계: 만족도 평가
# 만족 → 완료
# 부족 → DexiNed 시도
# 최고 필요 → EdgeNAT (Colab)
```

---

## 💻 VRAM 요구사항

| 모델 | 최소 VRAM | 권장 VRAM | 노트 |
|------|-----------|-----------|------|
| PiDiNet | 0GB (CPU 가능) | 2GB | 4GB로 충분 |
| DexiNed | 2GB | 4GB | 4GB로 충분 |
| EdgeNAT | 8GB? | 12GB+ | Colab 권장 (14GB) |

**현재 시스템**: 4GB VRAM
→ PiDiNet ✅, DexiNed ✅, EdgeNAT ⚠️

---

## 🔗 참고 링크

- **PiDiNet Paper**: https://arxiv.org/abs/2108.07009
- **DexiNed Paper**: https://arxiv.org/abs/2112.02250
- **EdgeNAT Paper**: https://arxiv.org/abs/2408.10527
- **BSDS500 Benchmark**: https://paperswithcode.com/sota/edge-detection-on-bsds500-1
