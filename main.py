"""
Korean Morphological Analyzer API Service
Using kiwipiepy for accurate Korean tokenization
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from kiwipiepy import Kiwi
import kiwipiepy

app = FastAPI(
    title="Korean Tokenizer API",
    description="kiwipiepy 기반 한국어 형태소 분석 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kiwi 인스턴스 (싱글톤)
kiwi = Kiwi()

# 불용어 (검색에서 제외할 품사)
STOPWORD_TAGS = {
    'JKS', 'JKC', 'JKG', 'JKO', 'JKB', 'JKV', 'JKQ',  # 격조사
    'JX', 'JC',  # 보조사, 접속조사
    'EP', 'EF', 'EC', 'ETN', 'ETM',  # 어미류
    'SF', 'SP', 'SS', 'SE', 'SO',  # 문장부호
    'SW',  # 기타 기호
}

# 의미있는 품사 (검색에 포함할 것)
MEANINGFUL_TAGS = {
    'NNG', 'NNP', 'NNB',  # 명사류
    'NR', 'NP',  # 수사, 대명사
    'VV', 'VA', 'VX', 'VCP', 'VCN',  # 동사, 형용사
    'MM', 'MAG', 'MAJ',  # 관형사, 부사
    'SL', 'SH', 'SN',  # 외국어, 한자, 숫자
}


class TokenizeRequest(BaseModel):
    text: str
    include_pos: bool = False  # 품사 태그 포함 여부
    filter_stopwords: bool = True  # 불용어 필터링 여부
    extract_stems: bool = True  # 어간 추출 여부


class MorphInfo(BaseModel):
    form: str  # 형태
    tag: str  # 품사 태그
    start: int  # 시작 위치
    end: int  # 끝 위치


class TokenizeResponse(BaseModel):
    success: bool
    tokens: List[str]  # 토큰 목록
    morphs: Optional[List[MorphInfo]] = None  # 상세 형태소 정보
    stems: Optional[List[str]] = None  # 어간 목록
    original_text: str


class HealthResponse(BaseModel):
    status: str
    version: str
    kiwi_version: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서버 상태 확인"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        kiwi_version=kiwipiepy.__version__
    )


@app.post("/tokenize", response_model=TokenizeResponse)
async def tokenize(request: TokenizeRequest):
    """
    한국어 텍스트 형태소 분석

    - **text**: 분석할 텍스트
    - **include_pos**: 품사 태그 포함 여부
    - **filter_stopwords**: 불용어 필터링 여부
    - **extract_stems**: 어간 추출 여부
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="텍스트가 비어있습니다")

    try:
        # 형태소 분석 수행
        result = kiwi.tokenize(request.text)

        tokens = []
        morphs = []
        stems = []

        for token in result:
            form = token.form
            tag = token.tag

            morph_info = MorphInfo(
                form=form,
                tag=tag,
                start=token.start,
                end=token.end
            )

            # 모든 형태소 정보 저장
            if request.include_pos:
                morphs.append(morph_info)

            # 불용어 필터링
            if request.filter_stopwords:
                if tag in STOPWORD_TAGS:
                    continue
                if tag not in MEANINGFUL_TAGS:
                    continue

            # 토큰 추가 (1자 이상만)
            if len(form) > 0:
                tokens.append(form)

            # 어간 추출 (동사/형용사의 경우)
            if request.extract_stems:
                if tag.startswith('V'):  # 동사, 형용사
                    stems.append(form)
                elif tag.startswith('N'):  # 명사류
                    stems.append(form)

        # 중복 제거
        unique_tokens = list(dict.fromkeys(tokens))
        unique_stems = list(dict.fromkeys(stems))

        return TokenizeResponse(
            success=True,
            tokens=unique_tokens,
            morphs=morphs if request.include_pos else None,
            stems=unique_stems if request.extract_stems else None,
            original_text=request.text
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"형태소 분석 실패: {str(e)}")


@app.post("/batch_tokenize")
async def batch_tokenize(texts: List[str], filter_stopwords: bool = True):
    """
    여러 텍스트 일괄 형태소 분석
    """
    if not texts:
        raise HTTPException(status_code=400, detail="텍스트 목록이 비어있습니다")

    try:
        results = []
        for text in texts:
            if not text.strip():
                results.append({"text": text, "tokens": []})
                continue

            analysis = kiwi.tokenize(text)
            tokens = []

            for token in analysis:
                if filter_stopwords:
                    if token.tag in STOPWORD_TAGS:
                        continue
                    if token.tag not in MEANINGFUL_TAGS:
                        continue

                if len(token.form) > 0:
                    tokens.append(token.form)

            results.append({
                "text": text,
                "tokens": list(dict.fromkeys(tokens))
            })

        return {"success": True, "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"일괄 분석 실패: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
