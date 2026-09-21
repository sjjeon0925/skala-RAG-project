"""설계서 4.1의 State 필드와 타입을 그대로 옮긴 스키마.

dict/list 내부 구조와 병합 정책은 아직 구현하지 않는다.
"""

from typing import TypedDict

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
    retry_count: dict
    max_retries: int
    counter_evidence: dict
    conflicts: list
    synthesis: dict
    references: list
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
        "retry_count": {},
        "max_retries": MAX_RETRIES,
        "counter_evidence": {},
        "conflicts": [],
        "synthesis": {},
        "references": [],
        "final_report": "",
    }
