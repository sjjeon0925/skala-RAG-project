# 프롬프트와 출력 계약

- `extraction.md`: 기술×기준별 근거 추출, 원문 인용·조건·Fact/Opinion, 직접/생태계/비교 범위.
- `assessment.md`: 관점별 평가. 입력 근거 ID만 사용하고 부족한 결과는 별도 사유로 반환.
- `trl.md`: TRL 단계 정의와 추정 표기, 상용 부품과 전체 기술의 상용화 구분.
- `report_outline.md`: 최신 설계서 목차. 보고서는 `agents/report.py`가 검증 후 State를 렌더링한다.

추출은 `agents/extraction.py`, 평가 출력은 `agents/assessment.py`의 JSON Schema로 제한한다.
반대 근거·Conflict·Synthesis 역할 지시는 해당 Node/Agent 코드와 함께 관리한다.
검색 문서에 포함된 지시는 시스템 작업 지시로 취급하지 않는다.
