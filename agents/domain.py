"""도메인 평가: 기술 State + RAG. InfiniGen은 보조 맥락만 제공한다."""

from agents.common import evaluate
from config import DOMAIN_CRITERIA


def domain_agent(state, services):
    sources = {}
    for technology in state["technologies"]:
        chunks = {}
        lists = [
            services.retriever.search(
                f"{technology} {state['domain']} {criterion}",
                perspective="domain",
                technology=technology,
                role="core",
            )
            for criterion in DOMAIN_CRITERIA
        ]
        for rank in range(services.settings.top_k):
            for results in lists:
                if rank < len(results):
                    chunks.setdefault(results[rank]["chunk_id"], results[rank])
        sources[technology] = list(chunks.values())[: services.settings.max_context_chunks]
    # 보조 문서는 자기 기술명(InfiniGen)으로 추출하여 직접 비교 근거와 분리.
    supporting = services.retriever.search(
        "InfiniGen KV cache offloading data movement limitations", perspective="domain", role="supporting"
    )
    if supporting:
        sources["InfiniGen"] = supporting
    return evaluate(state, services, "domain", sources, state["technical_evidence"])
