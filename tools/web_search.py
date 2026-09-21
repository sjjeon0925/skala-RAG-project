def search_web(query: str) -> list[dict]:
    """TODO: 외부 검색 제공자 연결. 검색 결과와 URL·출처 정보를 반환."""
    raise NotImplementedError("Web Search 도구를 구현하세요.")


def summarize_web_sources(sources: list[dict]) -> dict:
    """TODO: 외부 자료를 출처 및 Fact/Opinion 구분과 함께 요약."""
    raise NotImplementedError("외부 자료 요약 도구를 구현하세요.")
