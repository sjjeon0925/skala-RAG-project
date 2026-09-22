# 수정방안 적용 기록

기준: Downloads/수정방안/2.md 및 설계서.pdf (9쪽). 원본 파일은 수정하지 않았다.
현재 저장소는 수정 목록이 전제한 완성 구현이 아니라 NotImplementedError 기반 함수 틀이었다.
따라서 기존 동작을 바꾸는 항목뿐 아니라 필요한 본체도 구현했다.

| 수정 목록 | 적용 |
| --- | --- |
| State 16개와 search_queries | 초기 검색어, Query Rewrite 갱신, 기술 조사에서 사용 |
| references 소유권 | Report만 작성, 실제 본문 인용만 중복 제거하여 교체 |
| 평가 기준 | 시장/이해관계자/도메인 각 5개, TRL 3개 근거 묶음 |
| RAG 초기값 | 400토큰, 긴 구간 overlap 50, Dense/BM25 각각 10, RRF 후 5 |
| 표 보존 | PyMuPDF 표 감지 및 캡션 휴리스틱, 표 페이지 parent + 토큰 제한 child |
| 문서 7편 | 원본 byte 동일 복사, manifest 서지·쪽수 추가 |
| 검색 품질 | 기술×기준 질의·상한, 별칭, 신뢰 도메인 우선/선택 허용 목록, direct/ecosystem 구분 |
| 추출 | 기준 단위 호출, 인용 정규화, 교정 1회, 별도 의미 검증, 탈락 사유 코드 |
| 평가 | 기술×기준 결과 1개, 근거 ID, 미확보 사유, 검색 최대 2회 |
| TRL | 관련 환경 검증(5)/시연(6)/운영 환경 프로토타입(7) 구분, 추정 표기 |
| 목차 | 4.x 외 세부 번호 제거, 미확보 항목은 6장에 모음 |
| References | 논문 학회/arXiv, 웹 사이트명, 확인된 메타데이터만 표시 |
| 저장 전 검증 | 출처 ID, 인용 수치·단위·조건(서지 연도·ID·규격명 제외), 반대 근거 종합/보고서 포함 여부 |
| small/base | scripts/evaluate_retrieval.py와 정답 페이지·anchor 세트, 실제 측정 결과 별도 기록 |

## 설계 보완 사항

- 현재 제공된 자료에는 별도 수업 가이드의 TRL 단계 표가 없다. NASA 표준 단계의 환경 구분을 참고했으며,
  강의 가이드와의 문구 일치까지 검증했다고 주장하지 않는다.
- 7편은 사용자가 지정한 최신 문서 묶음으로 구성했다. 강의 Doc Pool 허용 여부를 코드가 판단하지 않는다.
- CENT는 성능 수치의 동일성 검증이 아니라 유사 구조의 비교 맥락으로 사용한다.
- 1차 검사에는 Attention 실행 위치를 유지한다.
- 이전 핸드아웃의 ITME 1.80배라는 수치를 상수나 정답으로 사용하지 않는다. 제공 PDF는 초록에서 35.7%를 제시한다.
  수치는 특정 Baseline/조건과 함께 확인해야 한다.

## 참고한 공식 구현 자료

- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [multilingual-e5-base 모델 카드](https://huggingface.co/intfloat/multilingual-e5-base)
- [PyMuPDF Page / find_tables](https://pymupdf.readthedocs.io/en/latest/page.html)
- [NASA TRL 정의](https://www.nasa.gov/sbir_sttr/program-definitions/)
