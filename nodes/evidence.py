from typing import Literal

from state import ResearchState


def first_evidence_check(state: ResearchState) -> dict:
    """1차 검사: 기술 근거 9항목과 성능 수치의 출처 확인.

    TODO: 부족한 항목을 새로 계산해 missing_evidence를 덮어쓴다(충분하면 빈 목록).
    재검색 한도 소진 시에도 이 결과가 그대로 남아 다음 단계로 전달된다.
    """
    raise NotImplementedError("1차 Evidence 충분성 검사를 구현하세요.")


def route_first_evidence(state: ResearchState) -> Literal["rewrite", "evaluate"]:
    """설계서 본문의 분기: 충분하거나 재검색 한도 소진 시 평가 진행.

    State를 바꾸지 않고 판단만 한다.
    TODO: missing_evidence가 비었으면 evaluate, retry_count < max_retries면 rewrite,
    아니면 evaluate.
    """
    raise NotImplementedError("1차 검사와 재검색 횟수에 따른 라우팅을 구현하세요.")


def query_rewrite(state: ResearchState) -> dict:
    """Query Rewrite: 부족한 기술 근거에 맞춰 검색 질문 재작성.

    TODO: retry_count를 1 올리고, missing_evidence 각 항목의 "query"에
    재작성한 질의를 채워 반환한다(새 State 키를 만들지 않는다).
    """
    raise NotImplementedError("기술 조사 재검색용 Query Rewrite를 구현하세요.")


def second_evidence_check(state: ResearchState) -> dict:
    """2차 검사: 4개 관점의 근거 확인 후 부족한 정보를 기록.

    TODO: 기존 missing_evidence에 관점별 부족 항목을 이어 붙여 반환한다.
    전체 검색은 다시 반복하지 않고, 검사 후 다음 검증 단계로 진행한다.
    """
    raise NotImplementedError("2차 Evidence 검사와 근거 부족 기록을 구현하세요.")
