# ITME와 CXL-PIM 비교 평가

수정방안 폴더의 `설계서.pdf`와 `2.md`를 기준으로 구성한 Agentic RAG 프로젝트다.
ITME와 CXL-PIM을 기술 성숙도, 시장성, 이해관계자, 데이터센터 적용성 관점에서 비교한다.
근거가 부족한 항목은 정보 부족으로 남기며 기술의 승자를 정하지 않는다.

## 실행

```bash
uv sync --extra rag
# .env.example을 참고해 .env에 OPENAI_API_KEY, TAVILY_API_KEY 설정
uv run python app.py --show-state --show-graph
uv run python -m rag.pipeline --inspect
uv run python -m rag.pipeline --build
uv run python -m rag.pipeline --query "KV Cache 저장 위치" --technology ITME
uv run python app.py --run --output outputs/report.md --log-file outputs/workflow.log
```

Python 3.11 이상. 최초 실행은 오픈소스 e5 모델을 `.cache/huggingface`에 다운로드한다.
LLM은 OpenAI Responses API, 검색은 Tavily를 사용한다. `OPENAI_MODEL` 기본값은 `gpt-4.1-mini`다.
임베딩 기본 장치는 재현성을 위한 CPU이며 `EMBEDDING_DEVICE`와 `EMBEDDING_THREADS`로 조정할 수 있다.
`.env`는 기존 셸 환경보다 우선하며 키를 로그나 State에 기록하지 않는다.
`LANGCHAIN_TRACING_V2`를 켜면 별도 LangSmith 추적이 동작할 수 있다. 추적은 필수가 아니다.
실제 실행에는 API 사용 비용이 발생한다. 각 기술·기준당 웹 검색은 최초 1회와 대체 1회 이내,
추출 교정은 1회 이내, 반대 근거 검색은 평가 주장당 1회다.

검증을 통과하면 Markdown 보고서와 같은 이름의 JSON State를 저장한다.
진행 중 `outputs/state-<run_id>.json`에는 마지막 완료 단계가 기록된다. 실패하면 완성 보고서를 저장하지 않는다.
PDF 보고서 변환은 현재 제공하지 않는다.

## 문서 구성

| 문서 | 파일 | 역할 | PDF 원본 쪽수 |
| --- | --- | --- | ---: |
| ITME | data/papers/ITME.pdf | 핵심 | 13 |
| CXL-PIM | data/papers/CXL-PIM.pdf | 핵심 | 13 |
| InfiniGen | data/papers/InfiniGen.pdf | 보조 | 18 |
| PagedAttention | data/papers/PagedAttention.pdf | 보조 | 16 |
| Mooncake | data/papers/Mooncake.pdf | 보조 | 17 |
| PIM Is All You Need | data/papers/CENT.pdf | 보조 | 20 |
| CacheGen | data/papers/CacheGen.pdf | 보조 | 19 |

총 116쪽이며 실제 로딩 시 200쪽 상한을 검사한다. 제목·저자·연도·출처·학회/arXiv 정보는
`data/documents.json`에 있다. 원본 파일을 복사했으며 다운로드 폴더는 변경하지 않았다.
보조 논문은 도메인 평가와 이후 Conflict 분석에 비교 맥락으로 전달한다.
보조 논문의 수치를 ITME/CXL-PIM의 직접 성능으로 사용하지 않는다.

## 검색과 근거 검증

- 청크 크기는 e5 tokenizer 기준 400토큰, 긴 구간의 overlap은 50토큰이다.
- 문단·Section과 PDF 원본 페이지를 보존한다. 표 감지 또는 Table 캡션이 있는 페이지는
  원본 페이지 전체를 근거 parent로 유지하고, 최대 400토큰의 child만 임베딩한다.
  검색 결과에는 parent를 돌려주므로 표 제목·단위·주변 조건이 잘려 나가지 않는다.
- Dense 10개와 BM25 10개를 기술·문서 역할별로 필터링한 뒤 RRF(k=60)로 결합한다.
  `chunk_id` 중복을 제거하고 최종 5개를 반환한다. 최종 5개와 토큰 단위는 설계서의 미지정 부분에 대한 구현 초기값이다.
- e5에 `query: ` / `passage: ` 접두어와 정규화를 적용한다.
- 캐시 키는 PDF 바이트·manifest·모델·청크 설정을 포함한다. FAISS와 JSON만 저장하며 pickle을 역직렬화하지 않는다.
- 원문 인용 정규화, 인용 ID·기술 일치, 수치·단위·Baseline·조건을 검사한다.
  불일치 이유는 원문이나 키 대신 사유 코드로 로깅한다.
- 별도 의미 검증으로 생태계 자료의 대상 기술 귀속, CENT 등 다른 시스템과의 혼동, 정보 부족을 부정 사실로 바꾸는 주장을 검사한다.
  긴 근거 ID는 API에 짧은 별칭으로 전달하고 응답에서 복구한다.
- 웹 자료는 직접 기술 근거/direct, 상위 시장/ecosystem을 구분한다.
  `WEB_ALLOWED_DOMAINS`로 호스트 허용 목록을 지정할 수 있다. 기본값은 제한 없이 공신력 있는 도메인을 우선한다.

## State와 그래프

State는 `search_queries`를 포함한 16개 필드다. 초기 검색 후 최대 2회 재검색한다.
1차 검사는 부족 항목을 다시 계산하고 해결된 항목은 제거한다.
네 관점 Agent는 각자의 `*_analysis`만 반환하고, 합류 뒤 2차 검사가 부족 항목을 수집한다.
Counter-Evidence → Conflict → Synthesis → Report 순으로 진행한다.
Report는 새 사실을 생성하지 않고 State를 렌더링한다. 실제 인용한 출처만 `references`에 저장한다.
확인된 반대 근거가 종합과 보고서에서 빠지거나, 인용·수치·단위 검증이 실패하면 저장을 중단한다.

## 검증

```bash
uv run python -m unittest discover -s tests -v
uv run python scripts/evaluate_retrieval.py
```

테스트는 API 키나 모델 다운로드 없이 계약·재검색·Fan-in·인용·수치·RRF·필터를 확인한다.
RAG 테스트에는 `--extra rag` 의존성이 필요하다. 검색 비교는 실제 small/base 모델을 사용한다.
결과와 제한 사항은 [docs/verification.md](docs/verification.md)를 참고한다.
`note.md`, `handout.md`, `v4.pdf`는 이전 설계 기록이며 현재 구현 지침은 이 README와 최신 수정방안 설계다.
