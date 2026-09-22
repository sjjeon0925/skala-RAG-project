"""설계서 4.1의 16개 State 필드. references는 보고서가 교체한다."""
from typing import Literal, NotRequired, TypedDict
from config import DOMAIN, MAX_RETRIES, TECHNOLOGIES, TECHNICAL_EVIDENCE_ITEMS, QUERY_TERMS


class Source(TypedDict):
    title: str
    url: str
    document_id: NotRequired[str]
    authors: NotRequired[list[str]]
    published_at: NotRequired[str]
    venue: NotRequired[str]
    arxiv_id: NotRequired[str]
    site_name: NotRequired[str]


class Evidence(TypedDict):
    evidence_id: str
    technology: str
    perspective: str
    criterion: str
    claim: str
    source: Source
    content: str
    page: NotRequired[int]
    experimental_condition: dict[str, str]
    quantitative: bool
    scope: Literal["direct", "ecosystem", "comparison"]
    kind: Literal["fact", "opinion", "interpretation"]
    speaker: NotRequired[str | None]
    affiliation: NotRequired[str | None]
    published_at: NotRequired[str | None]


class Gap(TypedDict):
    technology: str
    perspective: str
    item: str
    reason: str


class Assessment(TypedDict):
    technology: str
    criterion: str
    claim: str
    evidence_ids: list[str]
    scope: str


class Analysis(TypedDict):
    results: list[Assessment]
    evidence: dict[str, Evidence]
    evidence_ids: list[str]
    missing_evidence: list[Gap]


class ResearchState(TypedDict):
    technologies: list[str]
    domain: str
    search_queries: list[str]
    technical_evidence: dict[str, Evidence]
    trl_analysis: Analysis
    market_analysis: Analysis
    stakeholder_analysis: Analysis
    domain_analysis: Analysis
    missing_evidence: list[Gap]
    retry_count: int
    max_retries: int
    counter_evidence: dict
    conflicts: list
    synthesis: dict
    references: list[Source]
    final_report: str


def initial_state() -> ResearchState:
    return {
        "technologies": list(TECHNOLOGIES), "domain": DOMAIN,
        "search_queries": [f"{tech} {QUERY_TERMS[item]}" for tech in TECHNOLOGIES for item in TECHNICAL_EVIDENCE_ITEMS],
        "technical_evidence": {}, "trl_analysis": {}, "market_analysis": {},
        "stakeholder_analysis": {}, "domain_analysis": {}, "missing_evidence": [],
        "retry_count": 0, "max_retries": MAX_RETRIES, "counter_evidence": {},
        "conflicts": [], "synthesis": {}, "references": [], "final_report": "",
    }
