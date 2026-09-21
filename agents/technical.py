"""기술 조사 Agent: RAG로 원문 사실을 수집하고 기존 근거와 ID 기준 병합."""

from config import TECHNICAL_EVIDENCE_ITEMS
from evidence import extract_evidence
from rag.queries import rewrite_query


def technical_agent(state, services):
    evidence = dict(state["technical_evidence"])
    for technology in state["technologies"]:
        items = [
            x["item"]
            for x in state["missing_evidence"]
            if x.get("stage") == 1 and x.get("technology") == technology
        ]
        if state["retry_count"] == 0:
            items = list(TECHNICAL_EVIDENCE_ITEMS)
        if not items:
            continue
        chunks = {}
        # 순위별 round-robin으로 여러 항목의 검색 결과가 문맥 한도를 공유한다.
        lists = [
            services.retriever.search(
                rewrite_query(technology, item, state["retry_count"]),
                perspective="technical",
                technology=technology,
                role="core",
            )
            for item in items
        ]
        for rank in range(services.settings.top_k):
            for results in lists:
                if rank < len(results):
                    chunks.setdefault(results[rank]["chunk_id"], results[rank])
        selected = list(chunks.values())[: services.settings.max_context_chunks]
        evidence.update(
            extract_evidence(services, selected, technology=technology, perspective="technical", items=items)
        )
    return {"technical_evidence": evidence}
