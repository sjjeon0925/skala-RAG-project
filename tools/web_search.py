"""수업 코드의 TavilySearch와 근거 State 사이의 최소 어댑터."""

import hashlib
from urllib.parse import urlsplit, urlunsplit

from langchain_teddynote.tools.tavily import TavilySearch

from workflow_logging import log_operation


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in ("https", "http") or not parts.netloc or parts.username:
        return ""
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, parts.query, ""))


def create_web_search():
    """03-WebSearch.ipynb와 같은 TavilySearch 도구를 생성한다."""
    return TavilySearch()


def normalize_web_results(results: list[dict]) -> list[dict]:
    """수업 도구 결과에 Evidence가 요구하는 ID·출처 필드만 보충한다."""
    sources, seen = [], set()
    for row in results:
        url = canonical_url(row.get("url", ""))
        content = row.get("raw_content") or row.get("content") or ""
        if not url or not content.strip() or url in seen:
            continue
        seen.add(url)
        sources.append(
            {
                "chunk_id": "web-" + hashlib.sha256(url.encode()).hexdigest()[:16],
                "document_id": url,
                "source": row.get("title") or url,
                "source_url": url,
                "page": None,
                "role": "web",
                "content": content[:12000],
                "content_type": "full_text" if row.get("raw_content") else "snippet",
                "published_date": row.get("published_date") or "",
                "author": row.get("author") or "",
                "source_type": "web",
                "site_name": urlsplit(url).netloc,
                "venue": "",
                "identifier": "",
            }
        )
    return sources


@log_operation("WEB_SEARCH")
def web_search(tool, query: str, *, max_results: int | None = None) -> list[dict]:
    """수업 예제의 ``tavily_tool.search`` 호출을 그대로 사용한다."""
    results = tool.search(
        query=query,
        topic="general",
        max_results=max_results,
        format_output=False,
    )
    return normalize_web_results(results)


# 기존 프로젝트 호출부와의 호환성을 위한 별칭이다.
search_web = web_search


def summarize_web_sources(sources: list[dict]) -> dict:
    """Fact/Opinion 의미 분석은 각 평가 Agent가 수행한다."""
    return {"sources": sources, "source_count": len(sources)}
