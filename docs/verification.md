# 구현 검증 기록

검증일: 2026-09-22. 기준 브랜치는 `feat/agentic-rag-evidence-workflow`의 `c934664`이며, 결과 브랜치는 `feat/agentic-rag-plus`이다.

## 최종 검증

- 프로젝트 가상환경에서 `python -m unittest discover -s tests -q` 실행: 36개 통과.
- 정상 흐름, 재검색 성공·소진, 2차 부족 기록, 네 평가 Agent의 병렬 실행과 Fan-in 1회를 확인했다.
- State 16개 필드와 `search_queries` 갱신, 보고서 Agent의 실제 인용 출처 저장을 확인했다.
- 7개 PDF 116쪽 로드, 200쪽 상한, 페이지·메타데이터 보존을 확인했다.
- 표 페이지 parent 보존과 400토큰 child, Dense/BM25 필터·RRF·중복 제거, 캐시 재사용·손상 검출을 확인했다.
- 인용문, 근거 ID, 수치·단위·조건, 기술 범위, 반대 근거의 synthesis·보고서 반영을 확인했다.
- API 오류와 LLM 거부가 근거 미발견이나 DEMO 결과로 바뀌지 않는지 확인했다.
- Ruff 실행 파일은 현재 `.venv`에 설치되어 있지 않아 정적 검사는 실행하지 않았다.

테스트 로그에 보이는 `OP_FAILED`는 HTTP 오류, LLM 거부, 잘못된 캐시·입력 등을 의도적으로 주입한 예외 경로 테스트이며 전체 결과는 성공이다. PyMuPDF의 `fitz` 호환 import에 대한 폐기 예정 경고가 남아 있다.

## 검색 모델 비교

`data/retrieval_cases.json`의 원리·조건·성능·한계 질의 20개로 기록한 기존 측정값이다. CPU 1 thread, Dense 10개, BM25 10개, RRF 후 5개 조건이다.

| 모델 | Hit@5 | MRR@5 | 평균 질의 시간 | 인덱스 준비 시간 |
| --- | ---: | ---: | ---: | ---: |
| multilingual-e5-small | 80% | 0.5058 | 0.0119초 | 42.94초 |
| multilingual-e5-base | 75% | 0.5267 | 0.0261초 | 73.12초 |

표본이 작아 보편적 우열로 해석하지 않는다. 설계 기준인 base를 유지한다. 원시 결과는 `docs/retrieval-results.json`, 재현 코드는 `scripts/evaluate_retrieval.py`에 있다.

## 제한 사항

- 이번 최종 검증에서는 OpenAI와 Tavily를 호출하는 전체 유료 실행을 반복하지 않았다.
- 의미 검증도 LLM 판정이므로 완전한 사실성이나 시장 의견의 대표성을 보장하지 않는다.
- 표 감지와 캡션 보존은 휴리스틱이며 이미지 내부 수치와 OCR은 검증하지 않는다.
- 보고서는 Markdown이며 PDF/DOCX 레이아웃 검증은 범위에 포함하지 않았다.
