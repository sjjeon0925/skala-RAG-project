from state import ResearchState


def technical_agent(state: ResearchState) -> dict:
    """기술 조사 Agent (RAG).

    입력: technologies, missing_evidence(항목별 "query" 포함).
    출력: technical_evidence, references. retry_count는 query_rewrite가 올린다.
    TODO: ITME/CXL-PIM 원문에서 config.TECHNICAL_EVIDENCE_ITEMS 추출.
    TODO: InfiniGen은 오프로딩·데이터 이동의 보조 근거로만 사용.
    TODO: missing_evidence가 있으면 각 항목의 query로 해당 근거만 재검색해
    기존 technical_evidence에 합친다.
    """
    raise NotImplementedError("기술 조사 Agent의 논문 검색·근거 추출을 구현하세요.")
