from state import ResearchState


def synthesis_agent(state: ResearchState) -> dict:
    """평가 종합 Agent.

    입력: 각 관점 평가, counter_evidence, conflicts, missing_evidence.
    출력: synthesis.
    TODO: 공통점, 차이, 관점 간 상충과 Trade-off를 중립적으로 정리.
    특정 기술을 추천하거나 승자를 정하지 않는다.
    """
    raise NotImplementedError("평가 종합 Agent를 구현하세요.")
