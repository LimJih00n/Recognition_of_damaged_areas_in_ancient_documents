# 문화재 손상 부위 감지 및 SVG 변환 프로젝트

문화재 그림 이미지에서 찢어지고 손상된 부위를 픽셀 단위로 정확하게 인식하고, 그 형태를 SVG 벡터로 변환하는 프로젝트입니다.

## 프로젝트 구조

```
riwum/
├── datasets/           # 원본 이미지 (TIFF 고해상도)
│   ├── 1첩/
│   ├── 2첩/
│   └── ...
├── DexiNed/           # DexiNed edge detection 모델
├── results/           # 처리 결과 이미지
├── venv/              # Python 가상환경
├── requirements.txt   # 필수 패키지 목록
└── README.md          # 이 파일
```

## 환경 설정

### 1. 가상환경 활성화
```bash
source venv/bin/activate
```

### 2. 패키지 설치 (이미 설치됨)
```bash
pip install -r requirements.txt
```

### 3. DexiNed 모델 다운로드
DexiNed 사전학습 모델을 다운로드해야 합니다:
- 다운로드 링크: https://drive.google.com/file/d/1V56vGTsu7GYiQouCIKvTWl5UKCZ6yCNu/view?usp=sharing
- 저장 위치: `DexiNed/checkpoints/BIPED/10/`

## 테스트 결과 확인

현재 `results/` 디렉토리에 OpenCV 방법으로 테스트한 결과가 있습니다:

1. **edge_comparison.png** - 여러 edge detection 방법 비교
2. **damage_detection_pipeline.png** - 손상 부위 감지 파이프라인
3. **boundary_detail_analysis.png** - 경계 디테일 분석
4. **preview_w_0001.png** - 첫 번째 이미지 미리보기

## 접근 방법

### OpenCV 전통적 방법 (프로토타입)
- Threshold 기반 밝은 영역 감지
- 형태학적 연산 (Opening, Closing)
- 윤곽선 추출

**한계점:**
- 노이즈 많음 (87% 오검출)
- 경계 부정확 (모폴로지로 뭉개짐)
- 그림 내용과 혼동

### PiDiNet (최종 선택) - 2024년 업데이트 ⭐
- **Pixel Difference Network**
- **초고속**: 100-200 FPS
- **초경량**: <1M 파라미터, CPU 실행 가능
- **성능**: ODS 0.807 (인간 성능 0.803 초과)
- **2024년 2월 최신 업데이트**
- 고해상도 타일 처리 지원 (원본 해상도 유지)

## 사용 방법

### 1. 간단한 실행
```bash
./run_detection.sh
```

### 2. 고급 사용 (고해상도 원본 이미지)
```bash
source venv/bin/activate

python high_res_edge_detection.py \
    --image "datasets/1첩/w_0001.tif" \
    --tile-size 512 \
    --overlap 64 \
    --output-dir "results/pidinet" \
    --device cpu
```

**파라미터 설명:**
- `--tile-size`: 타일 크기 (512 or 1024 추천)
- `--overlap`: 타일 겹침 (경계 블렌딩용, 64 추천)
- `--device`: cpu 또는 cuda (GPU 사용 시)

### 타일 처리 방식의 장점
1. **원본 해상도 유지**: 7216x5412 원본 그대로 처리
2. **메모리 효율**: 큰 이미지도 작은 타일로 분할 처리
3. **경계 블렌딩**: 가중 평균으로 타일 경계 부드럽게
4. **정확도 향상**: 압축 없이 미세한 손상도 감지

## 다음 단계

1. ✅ PiDiNet으로 교체 완료
2. ✅ 고해상도 타일 처리 스크립트 작성
3. ⏳ PyTorch 설치 진행 중
4. 🔜 실제 원본 이미지로 테스트
5. 🔜 pypotrace로 SVG 변환 파이프라인 구축
6. 🔜 원본 이미지와 좌표 매핑 시스템 구현

## 이미지 정보

- 형식: TIFF
- 해상도: 7216 x 5412 픽셀
- 파일 크기: ~111MB
- 촬영 장비: Hasselblad CF-39MS
- DPI: 300

## 참고 자료

- **PiDiNet GitHub**: https://github.com/hellozhuo/pidinet
- **PiDiNet Paper**: [Pixel Difference Networks for Efficient Edge Detection (ICCV 2021)](https://arxiv.org/abs/2108.07009)
- **pypotrace**: https://github.com/flupke/pypotrace
- **EdgeNAT** (최신 SOTA): https://github.com/jhjie/EdgeNAT
- **DexiNed**: https://github.com/xavysp/DexiNed
