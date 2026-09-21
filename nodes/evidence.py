from typing import Literal

from state import ResearchState


def first_evidence_check(state: ResearchState) -> dict:
    """1차 검사: 기술 근거 9항목과 성능 수치의 출처 확인.

    TODO: 부족한 내용을 missing_evidence에 기록한다.
    """
    raise NotImplementedError("1차 Evidence 충분성 검사를 구현하세요.")


def route_first_evidence(state: ResearchState) -> Literal["rewrite", "evaluate"]:
    """설계서 본문의 분기: 충분하거나 재검색 한도 소진 시 평가 진행.

    TODO: retry_count(dict)의 내부 구조를 정한 뒤 한도 판단 구현.
    """
    raise NotImplementedError("1차 검사와 재검색 횟수에 따른 라우팅을 구현하세요.")


def query_rewrite(state: ResearchState) -> dict:
    """Query Rewrite: 부족한 기술 근거에 맞춰 검색 질문 재작성.

    TODO: 설계서 State 안에서 재작성 질의 전달 방식을 구현한다.
    """
    raise NotImplementedError("기술 조사 재검색용 Query Rewrite를 구현하세요.")


def second_evidence_check(state: ResearchState) -> dict:
    """2차 검사: 4개 관점의 근거 확인 후 부족한 정보를 기록.

    TODO: missing_evidence를 갱신한다. 전체 검색은 다시 반복하지 않는다.
    검사 후 다음 검증 단계로 진행한다.
    """
    raise NotImplementedError("2차 Evidence 검사와 근거 부족 기록을 구현하세요.")
