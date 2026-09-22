"""설계서의 16개 State 필드. 병렬 노드는 자신의 analysis만 쓴다.

references는 보고서에서 실제 인용한 출처만 병합한다. 공용 list reducer가 필요하지 않다.
missing_evidence는 근거 검사/기록 노드만 변경한다.
재검색 질의는 search_queries에 저장하여 기술 조사에 전달한다.
"""

from typing import TypedDict

from config import DOMAIN, MAX_RETRIES, TECHNICAL_EVIDENCE_ITEMS, TECHNOLOGIES


class Evidence(TypedDict):
    evidence_id: str
    technology: str
    perspective: str
    claim: str
    source: str
    page: int | None
    experimental_condition: str
    condition_source: dict
    quote: str
    source_url: str
    document_id: str
    chunk_id: str
    role: str
    item: str
    kind: str
    numeric: bool
    scope: str


class ResearchState(TypedDict):
    technologies: list[str]
    domain: str
    search_queries: list[str]
    technical_evidence: dict[str, Evidence]
    market_analysis: dict
    stakeholder_analysis: dict
    domain_analysis: dict
    trl_analysis: dict
    missing_evidence: list[dict]
    retry_count: int
    max_retries: int
    counter_evidence: dict
    conflicts: list[dict]
    synthesis: dict
    references: list[dict]
    final_report: str


def initial_state(*, max_retries: int = MAX_RETRIES) -> ResearchState:
    from rag.queries import rewrite_query

    if not 0 <= max_retries <= 10:
        raise ValueError("max_retries는 0~10 사이여야 함")
    return {
        "technologies": list(TECHNOLOGIES),
        "domain": DOMAIN,
        "search_queries": [
            rewrite_query(technology, item, 0)
            for technology in TECHNOLOGIES
            for item in TECHNICAL_EVIDENCE_ITEMS
        ],
        "technical_evidence": {},
        "market_analysis": {},
        "stakeholder_analysis": {},
        "domain_analysis": {},
        "trl_analysis": {},
        "missing_evidence": [],
        "retry_count": 0,
        "max_retries": max_retries,
        "counter_evidence": {},
        "conflicts": [],
        "synthesis": {},
        "references": [],
        "final_report": "",
    }
