# Korean Tokenizer Service 배포 가이드

kiwipiepy 기반 한국어 형태소 분석 API 서비스

## 현재 배포 상태 (2025-12-07)

| 항목 | 상태 |
|------|------|
| **운영 URL** | `https://korean-tokenizer-service.onrender.com` |
| **플랫폼** | Render.com (Docker) |
| **상태** | ✅ 정상 운영 중 |
| **버전** | 1.0.0 |
| **kiwipiepy** | 0.17.1 |

### 검증된 테스트 결과

```bash
# Health Check
curl https://korean-tokenizer-service.onrender.com/health
# {"status":"healthy","version":"1.0.0","kiwi_version":"0.17.1"}

# Tokenization Test
curl -X POST https://korean-tokenizer-service.onrender.com/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "금선물의 거래단위는 무엇입니까?", "filter_stopwords": true}'
# {"tokens": ["금", "선물", "거래", "단위", "무엇", "이"], ...}
```

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
│                    Render.com (Docker)                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   FastAPI + kiwipiepy                                     │   │
│  │   - POST /tokenize       단일 텍스트 토큰화               │   │
│  │   - POST /batch_tokenize 다수 텍스트 일괄 토큰화          │   │
│  │   - GET  /health         헬스체크                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  URL: https://korean-tokenizer-service.onrender.com              │
└─────────────────────────────────────────────────────────────────┘
```

## 재배포 방법

### 옵션 A: Render.com (현재 운영 중, 권장)

**GitHub Repository**: https://github.com/MinDongJae/korean-tokenizer-service

1. **Render.com 대시보드 접속**
   - https://dashboard.render.com

2. **수동 배포 트리거** (코드 변경 시)
   - Services → korean-tokenizer → Manual Deploy → Deploy latest commit

3. **자동 배포 설정**
   - `render.yaml`에 `autoDeploy: true` 설정되어 있음
   - GitHub push 시 자동 배포

### 옵션 B: 새 Render 프로젝트 생성

1. https://dashboard.render.com → **New** → **Web Service**

2. **GitHub 연결**
   - Repository: `MinDongJae/korean-tokenizer-service`
   - Branch: `master`

3. **빌드 설정**
   - Runtime: Docker
   - Dockerfile Path: `./Dockerfile`
   - Docker Context: `.`

4. **환경 변수**
   ```
   PORT=8080
   ```

5. **Health Check 설정**
   - Path: `/health`

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
