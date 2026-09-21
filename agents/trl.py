from state import ResearchState


def trl_agent(state: ResearchState) -> dict:
    """TRL 평가 Agent (RAG, 필요시 Web Search).

    입력: technologies, technical_evidence.
    출력: trl_analysis, 필요한 근거 부족 및 출처 정보.
    TODO: 논문/PoC/Prototype/실환경 검증/상용 제품 근거로 TRL 추정.
    공식 값이 아니면 공개 정보 기반 추정이라는 점을 명시한다.
    """
    raise NotImplementedError("TRL 평가 Agent를 구현하세요.")
