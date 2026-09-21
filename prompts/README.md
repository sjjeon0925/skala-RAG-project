# 프롬프트와 검증 위치

역할별 프롬프트는 코드와 함께 관리한다. 출력 계약은 schemas.py의 Pydantic 모델이다.

| 위치 | 책임 |
| --- | --- |
| tools/llm.py | 비신뢰 자료 취급, 근거 기반 응답, OpenAI 구조화 출력 |
| evidence.py | 기술/웹 자료에서 근거 추출, 인용문과 실험 조건 청크 검증 |
| agents/common.py | 관점별 평가 기준, TRL 단계, Fact/Opinion/Inference |
| nodes/verification.py | 반대 근거 검색 결과 판정, 상충 분석 |
| agents/synthesis.py | State만을 사용한 종합 |
| agents/report.py | 정해진 목차, 인용 필터링, 참고문헌 구성 |
| rag/queries.py | 기술 부족 항목별 결정적 Query Rewrite |
| report_outline.md | 설계서 보고서 목차 |

원문 인용 검증은 문자열/출처 검증이며 의미적 사실 검증의 보증은 아니다. 보고서 제출 전 검토가 필요하다.
