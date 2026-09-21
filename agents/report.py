from state import ResearchState


def report_agent(state: ResearchState) -> dict:
    """보고서 Agent.

    입력: 전체 State. 출력: final_report.
    TODO: prompts/report_outline.md 목차로 보고서 생성.
    SUMMARY는 반 페이지 이내, REFERENCE는 실제 활용 자료만 포함.
    공개 정보 부족, 추정 TRL, 실험 환경 차이 및 상충 근거를 명시한다.
    """
    raise NotImplementedError("최종 보고서 생성 Agent를 구현하세요.")
