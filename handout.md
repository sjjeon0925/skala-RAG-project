# RAG 파이프라인 구현 핸드아웃

논문 PDF 3편을 검색하는 부분(`rag/`)을 구현한다. 그래프·Agent·State는 다른 사람이 작업 중이므로 건드리지 않는다.
설계 근거는 보고서 v4의 2.3~2.6절이다. 채점의 "RAG Pipeline 구현"(20점)과 "실행 결과 재현성"(10점)에 걸린다.

## 1. 범위

| 수정한다 | 수정하지 않는다 |
| --- | --- |
| `rag/pipeline.py` (본작업) | `state.py`, `graph.py` |
| `config.py` (RAG 상수 추가만) | `agents/`, `nodes/`, `tools/` |
| `tests/` (새로 만들기) | `data/documents.json` (문서 목록 변경 금지) |
| `pyproject.toml` (부족한 패키지 추가 시, `uv.lock`도 같이 커밋) | 보고서, `prompts/report_outline.md` |

인터페이스(4절)를 바꿔야 할 것 같으면 먼저 상의한다. Agent 쪽 코드가 이 인터페이스를 기준으로 작성된다.

## 2. 시작하기

```bash
cd capstone-v1
uv sync --extra rag
uv run python app.py --show-graph   # 환경 확인
```

- 첫 실행 때 e5 모델(HuggingFace)을 내려받는다. torch 포함 1GB 안팎이라 미리 받아 둔다.
- 이 작업은 API 키가 필요 없다(임베딩과 BM25 모두 로컬). `.env`는 커밋하지 않는다.
- 셸에 다른 프로젝트의 가상환경이 켜져 있으면 `VIRTUAL_ENV ... does not match` 경고가 나온다. 무시해도 되고 `deactivate`로 없앨 수 있다.

## 3. 입력 데이터

`data/documents.json`이 목록이고 PDF는 `data/papers/`에 있다. 합계 44쪽(한도 200쪽).

| technology | role | 파일 | 쪽수 | 용도 |
| --- | --- | --- | --- | --- |
| ITME | core | `ITME.pdf` | 13 | 비교 대상 A의 직접 근거 |
| CXL-PIM | core | `CXL-PIM.pdf` | 13 | 비교 대상 B의 직접 근거 |
| InfiniGen | supporting | `InfiniGen.pdf` | 18 | 오프로딩·데이터 이동 배경 근거. **세 번째 평가 대상이 아니다** |

## 4. 만들 것 (인터페이스)

### 4.1 기존 뼈대 함수: 시그니처를 유지하고 본문만 채운다

```python
load_documents(manifest=DOCUMENT_MANIFEST) -> list    # PDF 로드, 총 쪽수가 MAX_DOCUMENT_PAGES 초과면 ValueError
split_documents(documents) -> list                    # 청크 생성 + 메타데이터
build_embeddings()                                    # e5 임베딩 객체
build_index(chunks, embeddings, index_dir=INDEX_DIR)  # FAISS 인덱스 저장
build_hybrid_retriever(vectorstore, chunks)           # Dense + BM25
```

### 4.2 추가할 것: Agent가 실제로 호출하는 부분

```python
get_retriever() -> HybridRetriever
    # data/index에 캐시가 있으면 로드, 없거나 설정이 바뀌었으면 새로 빌드

HybridRetriever.search(query, *, perspective, technology=None, role=None, k=TOP_K) -> list[dict]
    # 하이브리드 검색 결과를 Evidence 후보(4.3)의 리스트로 반환

chunk_to_evidence(chunk, *, perspective, score=None) -> dict
```

호출 예: 기술 조사 Agent는 `search(q, perspective="technical", technology="ITME")`, 도메인 평가 Agent는 `perspective="domain"`으로 호출한다.

### 4.3 Evidence 후보 형식

보고서의 공통 Evidence 구조를 따른다. `claim`과 `experimental_condition`은 검색이 아니라 Agent(LLM)가 채우므로 여기서는 빈 문자열로 둔다.

```python
{
    "evidence_id": "ITME-p3-c12",       # {document_id}-p{page}-c{청크 번호}. 같은 청크는 항상 같은 ID
    "technology": "ITME",
    "perspective": "technical",          # 호출자가 넘긴 값
    "claim": "",                         # Agent가 채움
    "source": "ITME",                    # document_id
    "page": 3,                           # PDF 원본 쪽 번호, 1부터 시작
    "experimental_condition": "",        # Agent가 채움 (성능 수치가 있을 때만)
    "content": "청크 본문",
    "role": "core",
    "source_url": "https://arxiv.org/abs/2606.12556",   # Reference 작성용
    "score": 0.031,
}
```

### 4.4 청크 메타데이터

보고서 필수 4개(`technology`, `document_id`, `page`, `chunk_id`)에 `role`과 `source_url`을 추가한다. `role`은 InfiniGen을 평가 대상으로 오인하지 않게 하려는 것이다. `page`는 항상 1부터 시작한다(강의 노트북의 0부터 시작하는 page와 헷갈리지 말 것).

## 5. 구현 명세

### 5.1 로딩
- PyMuPDF(`pymupdf`)로 쪽 단위 텍스트를 추출한다. 2단 편집 논문이라 읽기 순서가 섞일 수 있으니 블록 단위(`get_text("blocks", sort=True)` 등)로 추출해 결과를 눈으로 확인한다.
- 줄 끝 하이픈 분리("Attention-\nbased")와 페이지 머리말·꼬리말을 정리한다.
- 총 쪽수를 세어 `MAX_DOCUMENT_PAGES`(200)를 넘으면 예외를 낸다.

### 5.2 분할 (보고서: "문단·Section 경계 기준, 너무 긴 구간만 추가 분할")
- 문단을 모아 청크를 만들고, 번호가 붙은 절 제목(`3.2 ...` 형태)은 새 청크의 경계로 삼는다.
- **청크가 쪽 경계를 넘지 않게 한다.** 그래야 `page`가 정확하다(출처 표기에 쓰임).
- 문단 하나가 한도보다 길 때만 `RecursiveCharacterTextSplitter`로 추가 분할한다.
- 초기값은 청크 약 1,500자, 겹침 약 150자로 시작한다. e5 입력이 512토큰까지라는 점(제 기억, **모델 카드 확인 필요**)을 넘지 않는 크기여야 한다. 보고서가 "임의로 확정하지 말고 검색 결과를 보고 조정"이라고 했으니 상수는 `config.py`로 뽑고, 최종 값과 이유를 9절에 적어 준다.
- 참고문헌(References) 절은 인덱스에서 제외하는 것을 권장한다. 노이즈가 많다. 제외하면 그 사실을 결과 보고에 적는다.

### 5.3 임베딩 (`intfloat/multilingual-e5-base`)
- e5는 질의에 `query: `, 문서에 `passage: ` 접두어를 붙여야 한다(모델 카드 확인). 자동으로 붙지 않으니 임베딩 래퍼(`embed_query`, `embed_documents`)에서 직접 붙인다.
- 임베딩은 정규화한다(`normalize_embeddings=True`).

### 5.4 인덱스 저장과 캐시
- `data/index/`에 FAISS 인덱스와 `chunks.jsonl`, `meta.json`을 저장한다(이 폴더는 `.gitignore` 대상).
- `meta.json`에 문서 목록 해시, 임베딩 모델명, 청크 설정을 적고, 하나라도 다르면 다시 빌드한다. 같으면 로드만 해서 재실행이 빨라야 한다.
- BM25는 저장하지 않고 `chunks.jsonl`에서 로드할 때 다시 만든다.
- FAISS 로드 시 `allow_dangerous_deserialization`이 필요할 수 있다. 우리가 만든 파일만 로드한다.

### 5.5 하이브리드 검색
1. **BM25** (`rank-bm25`): 토큰화는 소문자 변환 후 영숫자와 하이픈 단위로 자른다. `CXL`, `PIM`, `TTFT`, `TPOT`, `RDMA`, `NVMe` 같은 약어가 한 토큰으로 살아야 한다. 한국어와 영어가 섞인 질의("CXL-PIM의 TTFT")에서는 영어 토큰만 걸리는 게 정상이다.
2. **Dense**: FAISS `similarity_search_with_score`. 코퍼스가 수백 청크라 `fetch_k`를 크게(전체 청크 수 수준) 잡아도 된다.
3. **결합**: RRF(순위 역수 합, `Σ 1/(60+rank)`)로 합치고 `chunk_id` 기준으로 중복을 제거한 뒤 상위 `k`(초기값 5)를 반환한다. `EnsembleRetriever`(`langchain_classic`)를 쓸 수도 있지만 패키지를 추가해야 하고, 직접 만들면 20줄 정도라 직접 구현을 권장한다.
4. **필터**: `technology`, `role`로 미리 걸러서 순위를 낸다. `technology="ITME"`이면 ITME 청크만 나와야 한다.

한국어 질의만으로는 BM25가 거의 기여하지 못한다(논문이 영어라 어휘가 겹치지 않음). 나중에 Query Rewrite가 영어 키워드 질의를 만들도록 다른 사람이 구현할 예정이니, 여기서는 한국어와 영어 질의 둘 다 동작하는지만 확인한다.

## 6. 완료 기준

### 6.1 실행 확인
`rag/pipeline.py`를 직접 실행할 수 있게 진입점을 만든다.

```bash
uv run python -m rag.pipeline --build                          # 인덱스 생성, 문서별 쪽수·청크 수 출력
uv run python -m rag.pipeline --query "KV Cache 저장 위치" --technology ITME
```

체크리스트:
- [ ] `--build`가 오류 없이 끝나고 총 쪽수 44가 출력된다.
- [ ] `--query` 결과에 technology, page, score, 본문 미리보기가 나온다.
- [ ] `--technology ITME`를 주면 ITME 청크만 나온다. `--role supporting`이면 InfiniGen만 나온다.
- [ ] 두 번째 실행은 재임베딩 없이 캐시를 로드한다.
- [ ] 한도(200쪽)를 넘는 경우 예외가 난다(임시로 `MAX_DOCUMENT_PAGES`를 낮춰서 확인).

### 6.2 대표 질의 검증 (보고서의 "검색 검증")
아래 표를 채워서 전달한다. "기대 위치"는 논문에서 직접 찾아 적는다.

| 질의(한국어 / 영어) | 기술 | 기대 위치(쪽) | 상위 5개에 포함 | 비고 |
| --- | --- | --- | --- | --- |
| 작동 원리 / operating principle | ITME, CXL-PIM 각각 | | | |
| KV Cache 저장 위치 / where KV cache is stored | 〃 | | | |
| Attention 실행 위치 / where attention is computed | 〃 | | | |
| 데이터 이동 경로 / data movement path | 〃 | | | |
| 실험 환경(GPU, 모델, Context Length) | 〃 | | | |
| 주요 성능 결과 / throughput, latency | 〃 | | | |
| 비교 Baseline | 〃 | | | |
| 한계점 / limitations | 〃 | | | |

추가로 빠른 점검 두 가지(가이드의 설명 기준이므로 논문 본문에서 실제 수치인지 확인): ITME는 "1.80배 처리량 향상", InfiniGen은 "최대 3배". 해당 수치가 든 청크가 검색되는지 본다.
**표와 수치 청크가 깨져서 검색되지 않으면** 그 사실을 기록한다. 보고서 6.1의 "공개 정보 기반 분석의 한계"에 쓸 재료가 된다.

### 6.3 모델 없이 도는 단위 테스트 (`tests/test_rag_pipeline.py`)
모델을 내려받지 않은 사람도 돌릴 수 있도록 다음은 가짜 데이터로 테스트한다: RRF 결합과 중복 제거, BM25 토큰화(`CXL-PIM`, `TTFT`가 살아남는지), `chunk_to_evidence`의 출력 키와 ID 형식, 쪽수 한도 예외, 청크가 쪽 경계를 넘지 않는지.

## 7. 주의사항
- 논문의 표와 수식은 텍스트 추출이 자주 깨진다. 성능 수치가 표에 있으면 실제로 추출되는지 반드시 확인한다.
- 그림 캡션, 머리말·꼬리말, 참고문헌이 검색 결과를 오염시키지 않는지 결과를 눈으로 본다.
- 청크 ID와 `evidence_id`는 재실행해도 같은 값이어야 한다(무작위 UUID 금지). 중복 제거와 출처 추적이 이것에 의존한다.
- `data/index/`는 커밋하지 않는다. 논문 PDF와 `documents.json`은 커밋 대상이다.

## 8. 하지 말 것
- `state.py`, `graph.py`, Agent, 노드 수정
- InfiniGen을 ITME·CXL-PIM과 같은 급의 평가 대상으로 취급하는 코드
- 청크 크기·Top-K를 근거 없이 확정(반드시 6.2 표로 확인 후 정한다)
- 검색이 안 되는 정보를 그럴듯하게 채워 넣는 것(빈 결과는 빈 결과로 반환)
- OpenAI 등 외부 임베딩 API 사용(보고서가 오픈소스 임베딩을 명시)

## 9. 끝나면 전달할 것
1. 변경한 파일 목록과 커밋 (`uv.lock`을 바꿨다면 포함)
2. 6.1 체크리스트 결과
3. 6.2 검증표 (채운 것)
4. 최종 청크 크기, 겹침, Top-K 값과 그렇게 정한 이유
5. 발견한 문제(깨진 표, 검색이 약한 항목 등)
