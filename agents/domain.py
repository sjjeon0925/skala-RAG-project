from state import ResearchState


def domain_agent(state: ResearchState) -> dict:
    """도메인 평가 Agent (RAG).

    입력: domain, technical_evidence.
    출력: domain_analysis, 필요한 근거 부족 및 출처 정보.
    TODO: config.DOMAIN_CRITERIA 기준으로 데이터센터 적용성 평가.
    실험 조건이 다른 수치는 직접 비교하지 않는다.
    """
    raise NotImplementedError("도메인 평가 Agent를 구현하세요.")
