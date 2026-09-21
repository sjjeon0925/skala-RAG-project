from state import ResearchState


def counter_evidence_node(state: ResearchState) -> dict:
    """TODO: 기존 주장의 반대·제약 근거를 찾아 counter_evidence에 저장.

    반대 근거 미발견 시 '공개된 반대 근거를 확인하지 못함'으로 기록.
    """
    raise NotImplementedError("Counter-Evidence 검증을 구현하세요.")


def conflict_node(state: ResearchState) -> dict:
    """TODO: 성능/비용, 용량/이동량, 상용화, 입장, 실험 조건 차이를 conflicts에 저장.

    GPU·모델·Context Length 등이 다르면 원시 성능 수치를 직접 비교하지 않고
    각 논문의 자기 Baseline 대비 변화를 중심으로 분석한다.
    """
    raise NotImplementedError("Conflict 분석을 구현하세요.")
