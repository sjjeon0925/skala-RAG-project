"""도메인 평가: 대상 기술 근거와 모든 보조 논문을 비교 맥락으로 사용한다."""

from agents.common import evaluate
from config import DOMAIN_CRITERIA, QUERY_TERMS


def domain_agent(state, services):
    sources = {technology: {} for technology in state["technologies"]}
    for technology in state["technologies"]:
        for criterion in DOMAIN_CRITERIA:
            query = f"{technology} {state['domain']} {QUERY_TERMS[criterion]}"
            direct = services.retriever.search(
                query,
                perspective="domain",
                technology=technology,
                role="core",
                k=services.settings.top_k,
            )
            supporting = services.retriever.search(
                query,
                perspective="domain",
                role="supporting",
                k=services.settings.top_k,
            )
            sources[technology][criterion] = [
                *({**row, "scope": "direct"} for row in direct),
                *({**row, "scope": "comparison"} for row in supporting),
            ][: services.settings.max_context_chunks]
    return evaluate(state, services, "domain", sources, state["technical_evidence"])
