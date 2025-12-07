# Korean Tokenizer Service 배포 가이드

kiwipiepy 기반 한국어 형태소 분석 API 서비스

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Supabase Edge Functions                       │
│                         (Deno Runtime)                           │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   kiwipiepy-client.ts                                     │   │
│  │   - tokenizeWithKiwipiepy()   (비동기, 외부 API 호출)    │   │
│  │   - smartTokenize()            (권장 함수)               │   │
│  │   - tokenizeSync()             (동기, rule-based)        │   │
│  │   - 자동 Fallback: 외부 서비스 실패 시 rule-based 사용   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼ HTTP POST                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Railway Cloud (Python)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   FastAPI + kiwipiepy                                     │   │
│  │   - POST /tokenize       단일 텍스트 토큰화               │   │
│  │   - POST /batch_tokenize 다수 텍스트 일괄 토큰화          │   │
│  │   - GET  /health         헬스체크                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  URL: https://korean-tokenizer-production.up.railway.app         │
└─────────────────────────────────────────────────────────────────┘
```

## 현재 상태

- **코드**: 완성됨 (`tokenizer-service/` 디렉토리)
- **배포**: Railway에 배포 필요

## 배포 방법

### 옵션 A: Railway CLI (권장)

1. **Railway CLI 설치**
   ```bash
   npm install -g @railway/cli
   ```

2. **로그인** (브라우저 인증 필요)
   ```bash
   railway login
   ```

3. **프로젝트 연결 또는 생성**
   ```bash
   cd tokenizer-service
   railway init
   # 또는 기존 프로젝트 연결:
   railway link
   ```

4. **배포**
   ```bash
   railway up
   ```

5. **도메인 확인**
   ```bash
   railway domain
   ```

### 옵션 B: Railway Dashboard (GUI)

1. https://railway.app 접속 및 로그인

2. **New Project** → **Deploy from GitHub repo** 선택
   - 또는 **Empty Project** → **Add Service** → **GitHub Repo**

3. 이 저장소의 `tokenizer-service/` 디렉토리 선택

4. Railway가 자동으로 `Dockerfile` 감지하여 빌드

5. **Settings** → **Networking** → **Generate Domain** 클릭

6. 생성된 URL 확인 (예: `korean-tokenizer-production.up.railway.app`)

### 옵션 C: 로컬 Docker 테스트

Docker Desktop 실행 후:

```bash
cd tokenizer-service

# 빌드 및 실행
docker-compose up --build -d

# 헬스체크
curl http://localhost:8080/health

# 토큰화 테스트
curl -X POST http://localhost:8080/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "금선물의 거래단위는 무엇입니까?", "filter_stopwords": true}'

# 중지
docker-compose down
```

## API 사용법

### POST /tokenize

단일 텍스트 형태소 분석

**Request:**
```json
{
  "text": "금선물의 거래단위는 무엇입니까?",
  "include_pos": false,
  "filter_stopwords": true,
  "extract_stems": false
}
```

**Response:**
```json
{
  "success": true,
  "tokens": ["금선물", "거래", "단위", "무엇"],
  "morphs": null,
  "stems": null,
  "original_text": "금선물의 거래단위는 무엇입니까?"
}
```

### POST /batch_tokenize

다수 텍스트 일괄 분석

**Request:**
```json
{
  "texts": [
    "금선물의 거래단위",
    "ETF 상장요건은?"
  ],
  "filter_stopwords": true
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {"text": "금선물의 거래단위", "tokens": ["금선물", "거래", "단위"]},
    {"text": "ETF 상장요건은?", "tokens": ["ETF", "상장", "요건"]}
  ]
}
```

### GET /health

서버 상태 확인

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "kiwi_version": "0.17.1"
}
```

## Edge Function 연동

`kiwipiepy-client.ts` 사용 예시:

```typescript
import { smartTokenize, tokenizeWithKiwipiepy } from './_shared/kiwipiepy-client.ts';

// 권장: 자동 fallback 포함
const tokens = await smartTokenize("금선물의 거래단위는?");
// → ["금선물", "거래", "단위"]

// 상세 옵션 사용
const { tokens, stats } = await tokenizeWithKiwipiepy("금선물의 거래단위는?", {
  filter_stopwords: true,
  include_pos: true
});
console.log(stats.method);  // "kiwipiepy" 또는 "rule-based"
console.log(stats.latency_ms);  // 응답 시간
```

## 환경 변수 (선택)

Edge Function에서 기본 URL 변경 시:

```bash
# Supabase Secrets
TOKENIZER_SERVICE_URL=https://your-custom-domain.railway.app
```

## 파일 구조

```
tokenizer-service/
├── main.py              # FastAPI 서버 (kiwipiepy 사용)
├── requirements.txt     # Python 의존성
├── Dockerfile          # Docker 이미지 정의
├── docker-compose.yml  # 로컬 테스트용
├── railway.toml        # Railway 배포 설정
└── DEPLOYMENT.md       # 이 문서

supabase/functions/_shared/
├── kiwipiepy-client.ts # Edge Function 클라이언트
└── korean-tokenizer.ts # Rule-based fallback (동기)
```

## 품사 태그 필터링

### 제외되는 품사 (STOPWORD_TAGS)
- 격조사: JKS, JKC, JKG, JKO, JKB, JKV, JKQ
- 보조사, 접속조사: JX, JC
- 어미류: EP, EF, EC, ETN, ETM
- 문장부호: SF, SP, SS, SE, SO
- 기타 기호: SW

### 포함되는 품사 (MEANINGFUL_TAGS)
- 명사류: NNG, NNP, NNB
- 수사, 대명사: NR, NP
- 동사, 형용사: VV, VA, VX, VCP, VCN
- 관형사, 부사: MM, MAG, MAJ
- 외국어, 한자, 숫자: SL, SH, SN

## 트러블슈팅

### Railway 404 오류
- 서비스가 배포되지 않았음
- Railway Dashboard에서 배포 상태 확인

### 타임아웃 (5초)
- kiwipiepy-client.ts가 자동으로 rule-based fallback 사용
- 네트워크 상태 확인

### Docker 빌드 실패
- Python 3.11-slim 이미지 사용 확인
- gcc/g++ 설치 필요 (kiwipiepy 빌드용)

## 다음 단계

1. Railway에 배포 완료
2. Health check 테스트: `curl https://korean-tokenizer-production.up.railway.app/health`
3. BM25 Hybrid Search에서 kiwipiepy 토큰화 사용 확인
4. 성능 비교 테스트 실행
