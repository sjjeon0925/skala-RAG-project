"""설계서 4.1의 State 필드. 필드 이름과 개수(15개)는 설계서와 같다.

설계서와 다른 두 가지:
- retry_count: 기술 조사 재검색 루프는 하나뿐이라 dict가 아니라 int.
- references: 병렬 평가 Agent가 함께 추가하므로 누적(operator.add) 리듀서를 둔다.
  재검색으로 중복이 생기므로 Report 단계에서 중복을 제거한다.

missing_evidence는 리듀서 없이 덮어쓴다.
- 1차 검사: 매번 새로 계산해 덮어씀(재검색이 성공하면 자동으로 비워짐).
- 2차 검사: Fan-in 뒤 단일 노드이므로 기존 목록에 이어 붙여 반환.
- 재작성 질의는 별도 키 없이 각 항목의 "query"에 담는다:
  {"technology": ..., "item": ..., "query": ...}

dict/list 내부 구조는 아직 구현하지 않는다.
"""

import operator
from typing import Annotated, TypedDict

from config import DOMAIN, MAX_RETRIES, TECHNOLOGIES


class ResearchState(TypedDict):
    technologies: list
    domain: str
    technical_evidence: dict
    market_analysis: dict
    stakeholder_analysis: dict
    domain_analysis: dict
    trl_analysis: dict
    missing_evidence: list
    retry_count: int
    max_retries: int
    counter_evidence: dict
    conflicts: list
    synthesis: dict
    references: Annotated[list, operator.add]
    final_report: str


def initial_state() -> ResearchState:
    return {
        "technologies": list(TECHNOLOGIES),
        "domain": DOMAIN,
        "technical_evidence": {},
        "market_analysis": {},
        "stakeholder_analysis": {},
        "domain_analysis": {},
        "trl_analysis": {},
        "missing_evidence": [],
        "retry_count": 0,
        "max_retries": MAX_RETRIES,
        "counter_evidence": {},
        "conflicts": [],
        "synthesis": {},
        "references": [],
        "final_report": "",
    }
