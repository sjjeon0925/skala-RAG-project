"""Tavily 검색 + 기술 관련성 구분. 시장 생태계는 직접 채택 근거와 구분한다."""
import hashlib
import os
import re
from urllib.parse import urlparse

from config import TECHNOLOGY_ALIASES, RESULTS_PER_CRITERION
from tools.llm import post_json, ProviderError

TRUSTED_DOMAINS = ('arxiv.org', 'acm.org', 'ieee.org', 'usenix.org', 'computeexpresslink.org',
                   'skhynix.com', 'news.skhynix.com', 'samsung.com', 'nvidia.com', 'intel.com',
                   'amd.com', 'micron.com', 'snia.org')


def relevance(text, technology):
    aliases = TECHNOLOGY_ALIASES.get(technology, (technology,))
    if technology == 'CXL-PIM':
        # Generic CXL-PIM/CXL-PNM names also refer to unrelated architectures.
        aliases = ('PNM-KV', 'PnG-KV', 'Scalable Processing-Near-Memory')
        if re.search(r'\bCENT\b|PIM Is All You Need', text, re.I) and not any(re.search(re.escape(a),text,re.I) for a in aliases):
            return 'comparison'
    if any(re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text, re.I) for alias in aliases):
        return 'direct'
    if technology == 'CXL-PIM' and re.search(r'\bPNM\b', text, re.I) and re.search(r'CXL|KV.?cache', text, re.I):
        return 'ecosystem'  # PNM alone does not identify the target paper/system.
    if re.search(r'\b(CXL|PIM|PNM)\b', text, re.I):
        return 'ecosystem'
    return None


def search_web(query: str) -> list[dict]:
    key = os.getenv('TAVILY_API_KEY')
    if not key:
        raise ProviderError('TAVILY_API_KEY is required in .env')
    payload = {'query': query, 'search_depth': 'basic', 'max_results': RESULTS_PER_CRITERION,
               'include_raw_content': True, 'include_answer': False}
    domains = [s.strip() for s in os.getenv('WEB_ALLOWED_DOMAINS', '').split(',') if s.strip()]
    if domains:
        payload['include_domains'] = domains
    response = post_json('https://api.tavily.com/search', payload, key)
    results = []
    seen = set()
    for row in response.get('results', []):
        url = row.get('url', '')
        if not url or url in seen:
            continue
        seen.add(url)
        host = urlparse(url).hostname or ''
        if domains and not any(host == d or host.endswith('.' + d) for d in domains):
            continue
        content = row.get('raw_content') or row.get('content') or ''
        if not content:
            continue
        source = {'title': row.get('title', ''), 'url': url, 'site_name': host}
        if row.get('published_date'):
            source['published_at'] = row['published_date']
        results.append({'evidence_id': 'web-' + hashlib.sha256(url.encode()).hexdigest()[:16],
                        'source': source, 'content': content[:14000], 'role': 'web',
                        'trusted': any(host == d or host.endswith('.' + d) for d in TRUSTED_DOMAINS)})
    return sorted(results, key=lambda r: not r['trusted'])
