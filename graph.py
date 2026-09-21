"""설계서 4.2~4.4의 실행 흐름. 각 노드 본체는 TODO 상태다."""

from langgraph.graph import END, START, StateGraph

from agents.domain import domain_agent
from agents.market import market_agent
from agents.report import report_agent
from agents.stakeholder import stakeholder_agent
from agents.synthesis import synthesis_agent
from agents.technical import technical_agent
from agents.trl import trl_agent
from nodes.evidence import (
    first_evidence_check, query_rewrite, route_first_evidence, second_evidence_check,
)
from nodes.verification import conflict_node, counter_evidence_node
from state import ResearchState
from workflow_logging import get_logger, log_node, log_router


def build_graph(run_id: str = "standalone"):
    logger = get_logger(run_id)
    logger.info("GRAPH_BUILD | 설계서 기반 Graph 구성 시작")
    builder = StateGraph(ResearchState)
    node_functions = {
        "technical": technical_agent,
        "first_check": first_evidence_check,
        "query_rewrite": query_rewrite,
        "trl": trl_agent,
        "market": market_agent,
        "stakeholder": stakeholder_agent,
        "domain": domain_agent,
        "second_check": second_evidence_check,
        "counter_evidence": counter_evidence_node,
        "conflict": conflict_node,
        "synthesis": synthesis_agent,
        "report": report_agent,
    }
    for name, function in node_functions.items():
        builder.add_node(name, log_node(name, function, logger))

    builder.add_edge(START, "technical")
    builder.add_edge("technical", "first_check")
    builder.add_conditional_edges(
        "first_check", log_router(route_first_evidence, logger),
        {"rewrite": "query_rewrite", "evaluate": "fan_out"},
    )
    builder.add_edge("query_rewrite", "technical")

    # 흐름 연결 전용: 새 Agent가 아니라 설계서의 Fan-out 지점이다.
    builder.add_node("fan_out", log_node("fan_out", lambda state: {}, logger))
    evaluators = ["trl", "market", "stakeholder", "domain"]
    for name in evaluators:
        builder.add_edge("fan_out", name)
    # 설계서의 Fan-in: 4개 관점 평가가 끝난 후 2차 검사.
    builder.add_edge(evaluators, "second_check")
    builder.add_edge("second_check", "counter_evidence")
    builder.add_edge("counter_evidence", "conflict")
    builder.add_edge("conflict", "synthesis")
    builder.add_edge("synthesis", "report")
    builder.add_edge("report", END)
    graph = builder.compile()
    logger.info("GRAPH_READY | 노드 %d개 | 병렬 평가 4개 | 재검색 분기 연결 완료", len(node_functions) + 1)
    return graph
