from state import ResearchState


def technical_agent(state: ResearchState) -> dict:
    """기술 조사 Agent (RAG).

    입력: technologies, missing_evidence, retry_count.
    출력: technical_evidence, references, 필요시 retry_count.
    TODO: ITME/CXL-PIM 원문에서 config.TECHNICAL_EVIDENCE_ITEMS 추출.
    TODO: InfiniGen은 오프로딩·데이터 이동의 보조 근거로만 사용.
    TODO: 누락 항목이 있으면 재작성된 질의로 해당 근거 재검색.
    """
    raise NotImplementedError("기술 조사 Agent의 논문 검색·근거 추출을 구현하세요.")
