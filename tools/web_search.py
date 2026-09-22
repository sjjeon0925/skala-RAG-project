"""Tavily Web Search. 실패는 근거 미발견과 구분하여 호출자에게 전파한다."""

import hashlib
import os
import re
from urllib.parse import urlsplit, urlunsplit

from config import Settings
from workflow_logging import get_logger, log_operation

TRUSTED_DOMAINS = (
    "arxiv.org", "acm.org", "ieee.org", "usenix.org",
    "computeexpresslink.org", "semiconductor.samsung.com",
)
TECH_ALIASES = {
    "ITME": ("ITME", "Inference Tiered Memory Expansion"),
    "CXL-PIM": ("CXL-PIM", "PNM-KV", "PnG-KV"),
}


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in ("https", "http") or not parts.netloc or parts.username:
        return ""
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, parts.query, ""))


def relevance(text: str, technology: str) -> str | None:
    """대상 시스템, 상위 생태계, 별도 비교 시스템을 구분한다."""
    if technology not in TECH_ALIASES:
        return "comparison"
    if technology == "CXL-PIM" and re.search(r"\bCENT\b|PIM Is All You Need", text, re.I):
        return "comparison"
    if any(
        re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.I)
        for alias in TECH_ALIASES[technology]
    ):
        return "direct"
    if technology == "CXL-PIM" and re.search(r"\b(CXL|PIM|PNM)\b", text, re.I):
        return "ecosystem"
    return None


class TavilySearch:
    def __init__(self, settings: Settings, client=None):
        self.settings = settings
        self.api_key = os.getenv("TAVILY_API_KEY")
        self.client = client
        if not self.api_key and client is None:
            raise ValueError("TAVILY_API_KEY 설정 필요")

    @log_operation("WEB_SEARCH")
    def search(self, query: str) -> list[dict]:
        import httpx

        payload = {
            "query": query,
            "search_depth": "advanced",
            "topic": "general",
            "max_results": self.settings.search_results,
            "include_answer": False,
            "include_raw_content": "text",
        }
        if self.settings.web_allowed_domains:
            payload["include_domains"] = list(self.settings.web_allowed_domains)
        # 검색당 한 HTTP 요청. 반대 근거 노드에서 암묵적 재검색하지 않는다.
        headers = {"Authorization": f"Bearer {self.api_key or ''}"}
        if self.client is not None:
            response = self.client.post("https://api.tavily.com/search", json=payload, headers=headers)
        else:
            with httpx.Client(timeout=self.settings.request_timeout) as client:
                response = client.post("https://api.tavily.com/search", json=payload, headers=headers)
        response.raise_for_status()
        sources, seen = [], set()
        for row in response.json().get("results", []):
            url = canonical_url(row.get("url", ""))
            content = row.get("raw_content") or row.get("content") or ""
            if not url or not content.strip() or url in seen:
                continue
            seen.add(url)
            host = urlsplit(url).hostname or ""
            if self.settings.web_allowed_domains and not any(
                host == domain or host.endswith("." + domain)
                for domain in self.settings.web_allowed_domains
            ):
                continue
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
                    "site_name": host,
                    "trusted": any(
                        host == domain or host.endswith("." + domain) for domain in TRUSTED_DOMAINS
                    ),
                }
            )
        sources.sort(key=lambda item: not item["trusted"])
        get_logger().info(
            "WEB_RESULTS | sources=%d | snippets=%d",
            len(sources),
            sum(x["content_type"] == "snippet" for x in sources),
        )
        return sources


def search_web(query: str) -> list[dict]:
    return TavilySearch(Settings.from_env()).search(query)


def summarize_web_sources(sources: list[dict]) -> dict:
    """자료 목록 정규화. Fact/Opinion 의미 분석은 각 평가 Agent의 책임."""
    return {"sources": sources, "source_count": len(sources)}
