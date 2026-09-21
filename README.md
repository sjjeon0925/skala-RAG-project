# ITME와 CXL-PIM 비교 평가

이 폴더의 조별 DOCX 설계서를 기준으로 작성한 코드 틀이다.
데이터센터·클라우드의 KV Cache 확장 기술을 데이터 이동 비용과 네 관점에서 평가한다.
비교 대상은 ITME와 CXL-PIM이며 InfiniGen은 보조 문서로 사용한다.

## 현재 구현 범위

- 설정, 설계서의 State 필드, Agent 7개와 제어 Node의 함수 틀
- 재검색, 네 관점 Fan-out/Fan-in, 근거 검사, 반증·상충 분석의 Graph 연결
- RAG 및 외부 검색 함수 틀, 보고서 목차
- 초기 State와 Graph를 확인하는 실행 진입점

실제 PDF 검색, 임베딩, 모델 호출, 평가, 보고서 생성·PDF 저장은 아직 미구현이다.
미구현 함수는 `NotImplementedError`를 발생시킨다. 샘플 분석이나 가짜 보고서를 생성하지 않는다.
기존 설계서와 가이드 PDF는 변경하지 않았다.

## 설계서와 코드 대응

| 설계 내용 | 코드 |
| --- | --- |
| Human 기술 선정, 도메인, 임베딩, 재검색 설정 | config.py |
| State Schema 15개 필드 | state.py |
| 기술·TRL·시장·이해관계자·도메인·종합·보고서 Agent | agents/ |
| Evidence 검사, Query Rewrite | nodes/evidence.py |
| Counter-Evidence, Conflict | nodes/verification.py |
| Graph 흐름 | graph.py |
| 원문 로딩, 분할, Dense + BM25 | rag/pipeline.py |
| 외부 검색·요약 | tools/web_search.py |
| 보고서 목차 | prompts/report_outline.md |

## 디렉터리

```text
capstone-v1/
├── agents/             # 설계서 Agent 7개
├── nodes/              # 충분성 검사, 재검색, 반증·상충 분석
├── rag/                # 논문 검색 파이프라인
├── tools/              # Web Search와 요약
├── prompts/            # 프롬프트 작성 위치, 보고서 목차
├── data/
│   ├── documents.json  # 핵심·보조 문서 목록
│   ├── papers/         # 원 논문 PDF를 준비할 위치
│   └── index/          # 검색 인덱스
├── outputs/            # 후속 구현 시 결과 저장
├── state.py
├── config.py
├── graph.py
└── app.py
```

## 실행

Python 3.11 이상을 사용한다. 이 폴더에서 실행한다.

```bash
uv sync
uv run python app.py --show-state
uv run python app.py --show-graph
```

`.env`의 키는 `config.py`가 `override=True`로 불러오므로 셸에 남은 같은 이름의 키보다 `.env`가 우선한다.
RAG 의존성은 실제 구현 시 `uv sync --extra rag`로 설치할 수 있다.
LLM과 Web Search 제공자는 설계서에서 지정하지 않아 아직 연결하지 않았다.

```bash
uv run python app.py --run
```

현재 `--run`은 첫 기술 조사 노드에서 미구현 메시지와 종료 코드 1로 끝난다.
각 함수의 TODO를 채운 뒤 전체 실행에 사용한다.

## 실행 흐름 로그

기본 INFO 로그는 터미널의 stderr로 출력된다. State·Mermaid·보고서는 stdout으로 출력된다.

```bash
uv run python app.py --run
uv run python app.py --run --log-level DEBUG --log-file outputs/workflow.log
```

로그에는 실행 ID, 시간, 스레드, 노드 이름, 처리 시간, 갱신된 필드와 개수가 표시된다.
DEBUG는 각 노드의 입력 State 필드별 개수를 추가로 표시한다.
문서·프롬프트·답변의 원문과 API 키는 로그에 출력하지 않는다.

| 이벤트 | 확인할 내용 |
| --- | --- |
| GRAPH_BUILD / GRAPH_READY | Graph 구성 및 컴파일 완료 |
| RUN_START / STATE_READY | 분석 대상, 도메인, 재검색 한도, 초기 상태 |
| NODE_START / NODE_DONE | 노드 진입·완료, 소요 시간, 반환 업데이트 |
| ROUTE_SELECTED / RETRY | 선택된 경로, 재검색 진입과 근거 부족 개수 |
| FAN_OUT / FAN_IN | 네 관점 평가 시작 및 전체 평가 합류 |
| NODE_FAILED / ROUTE_FAILED | 실패한 노드·분기와 예외 유형 |
| RUN_STOPPED / RUN_FAILED / RUN_DONE | 전체 실행 중단·실패·완료 |

현재는 기술 조사 Agent가 미구현이므로 `technical`의 NODE_FAILED까지만 관찰할 수 있다.
이후 노드의 로그는 해당 단계에 실제로 도달했을 때 출력된다.
로그 연결은 Agent의 반환값, 예외, State 구조 및 Graph 경로를 변경하지 않는다.

## 구현할 부분

1. (완료) 원문 PDF 3편(ITME 13쪽, CXL-PIM 13쪽, InfiniGen 18쪽, 합계 44쪽)을 `data/papers/`에 두었고 출처 URL은 `data/documents.json`에 있다.
2. multilingual-e5-base와 BM25 기반 Hybrid Retrieval을 작성한다.
3. 각 Agent와 검사 Node의 검색·모델 호출 본체를 채운다.
4. 설계서 dict/list 필드의 내부 구조(Evidence 등)를 구체화한다.
5. 정해진 목차로 보고서 생성과 최종 PDF 저장을 연결한다.
6. 검색 평가(Hit Rate@K, MRR), 실행 재현성, README Contributors를 작성한다.

State는 설계서의 15개 필드를 유지하되 두 가지가 설계서 표와 다르다.

- `retry_count`: 재검색 루프가 하나뿐이라 `dict`가 아니라 `int`.
- `references`: 병렬 평가 Agent가 함께 추가하므로 누적 리듀서를 둔다. 중복은 Report 단계에서 제거한다.

`missing_evidence`는 1차 검사가 덮어쓰고 2차 검사가 이어 붙이며, 재작성 질의는 각 항목의 `query`에 담는다.
Graph의 재검색 한도 후 진행 및 2차 검사 후 진행은 설계서 4.3 본문의 흐름을 따른다.

## Contributors

TODO: 조원별 실제 수행 역할을 작성한다.
