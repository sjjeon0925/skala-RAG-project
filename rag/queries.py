"""검색 질의 생성과 재작성.

기본 질의는 순수 함수라 같은 State에서 항상 재현된다. 재검색 단계에서는
교안(langgraph-v1/20-RAG/04-QueryRewrite)과 같이 LLM이 질의를 다시 쓰되,
실패하면 순수 함수 결과로 되돌아간다.
"""

from config import TECH_PROFILES
from schemas import RewrittenQueries
from workflow_logging import get_logger

TECHNICAL_TERMS = {
    "작동 원리": "architecture mechanism design",
    "KV Cache 저장 위치": "KV cache placement memory tier",
    "Attention 실행 위치": "attention computation GPU PIM PNM",
    "데이터 이동 경로": "data transfer DMA RDMA PCIe bandwidth",
    "실험 환경": "evaluation experimental setup GPU model context length batch",
    "주요 성능 결과": "evaluation throughput latency TTFT TPOT speedup",
    "비교 Baseline": "baseline comparison evaluation",
    "한계점": "limitations overhead bottleneck scalability",
    "출처": "paper authors abstract",
}

REWRITE_INSTRUCTIONS = """Reformulate each retrieval query so it finds the requested evidence
in the target paper. 원 질의의 의도를 바꾸지 않는다.

# Steps
1. 찾으려는 항목(item)의 핵심 의도를 파악한다.
2. 대상 기술의 고유 명칭(distinctive_names)을 반드시 포함해 동명이의 문서를 배제한다.
3. 논문에서 실제로 쓰이는 영문 용어와 동의어를 보강한다(예: throughput, TTFT, baseline).
4. 이전 시도에서 찾지 못했으므로 다른 표현·다른 절(section)을 겨냥한다.

# Output
- item마다 질의 1개. 설명 문장 없이 질의 문자열만.
- 전달받은 item 목록만 사용하고 새 item을 만들지 않는다."""


def distinctive_names(technology):
    profile = TECH_PROFILES.get(technology, {})
    return list(profile.get("distinctive", ())) or [technology]


def rewrite_query(technology, item, retry_count):
    """LLM 없이 만드는 기본 질의. 고유 명칭을 앞에 두어 동명이의를 줄인다."""
    terms = TECHNICAL_TERMS.get(item, item)
    name = distinctive_names(technology)[0]
    if retry_count == 0:
        return f"{technology} {name} {item} {terms}"
    if retry_count == 1:
        return f"{name} {terms} implementation evaluation section evidence"
    return f"{name} {terms} measured result configuration constraint discussion"


def llm_rewrite_queries(services, targets, retry_count):
    """교안 방식의 질의 재작성. targets는 {"technology","item"} 목록이다."""
    fallback = {
        (row["technology"], row["item"]): rewrite_query(row["technology"], row["item"], retry_count)
        for row in targets
    }
    if not targets or getattr(services, "mode", "live") == "demo":
        return fallback
    try:
        result = services.llm.generate(
            "query_rewrite",
            REWRITE_INSTRUCTIONS,
            {
                "retry_count": retry_count,
                "targets": [
                    {
                        "technology": row["technology"],
                        "item": row["item"],
                        "previous_query": fallback[(row["technology"], row["item"])],
                        "distinctive_names": distinctive_names(row["technology"]),
                    }
                    for row in targets
                ],
            },
            RewrittenQueries,
        )
    except Exception as exc:  # noqa: BLE001 -- 재작성 실패가 재검색 자체를 막지 않는다.
        get_logger().warning("QUERY_REWRITE_FALLBACK | %s", type(exc).__name__)
        return fallback
    rewritten = dict(fallback)
    for row in result.queries:
        key = (row.technology, row.item)
        # 전달하지 않은 항목이나 고유 명칭이 빠진 질의는 채택하지 않는다.
        if key in rewritten and row.query.strip() and _keeps_identity(row.query, row.technology):
            rewritten[key] = row.query.strip()
    get_logger().info(
        "QUERY_REWRITE_APPLIED | targets=%d | rewritten=%d",
        len(fallback),
        sum(1 for key in fallback if rewritten[key] != fallback[key]),
    )
    return rewritten


def _keeps_identity(query, technology):
    lowered = query.lower()
    return any(name.lower() in lowered for name in [*distinctive_names(technology), technology])
