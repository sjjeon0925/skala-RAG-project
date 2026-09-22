from typing import Literal

from config import TECHNICAL_EVIDENCE_ITEMS, PERSPECTIVE_CRITERIA, QUERY_TERMS
from evidence import evidence_errors, collect_evidence, deduplicate_gaps
from state import ResearchState


def first_evidence_check(state: ResearchState) -> dict:
    valid = [e for e in state['technical_evidence'].values() if not evidence_errors(e)]
    gaps = []
    for tech in state['technologies']:
        for item in TECHNICAL_EVIDENCE_ITEMS:
            if not any(e['technology'] == tech and e.get('scope') == 'direct'
                       and (e.get('criterion') == item or item == '출처') for e in valid):
                gaps.append({'technology': tech, 'perspective': 'technical', 'item': item, 'reason': '검증된 직접 근거 없음'})
    return {'missing_evidence': gaps}


def route_first_evidence(state: ResearchState) -> Literal['rewrite', 'evaluate']:
    return 'rewrite' if state['missing_evidence'] and state['retry_count'] < state['max_retries'] else 'evaluate'


def query_rewrite(state: ResearchState) -> dict:
    if state['retry_count'] >= state['max_retries']:
        raise ValueError('Retry limit exhausted')
    suffix = 'experimental setup results limitations' if state['retry_count'] == 0 else 'implementation evaluation discussion appendix'
    queries = [f"{g['technology']} {QUERY_TERMS[g['item']]} {suffix}"
               for g in state['missing_evidence'] if g['perspective'] == 'technical']
    return {'retry_count': state['retry_count'] + 1, 'search_queries': list(dict.fromkeys(queries))}


def second_evidence_check(state: ResearchState) -> dict:
    index = collect_evidence(state)
    gaps = [g for g in state['missing_evidence'] if g['perspective'] == 'technical']
    for perspective, criteria in PERSPECTIVE_CRITERIA.items():
        analysis = state.get(f'{perspective}_analysis', {})
        for tech in state['technologies']:
            for criterion in criteria:
                rows = [r for r in analysis.get('results', []) if r.get('technology') == tech and r.get('criterion') == criterion]
                valid = any(r.get('claim') and r.get('evidence_ids') and
                            (perspective != 'market' or criterion not in ('제품화', '실제 도입') or r.get('scope') == 'direct') and
                            all(eid in index and not evidence_errors(index[eid]) for eid in r['evidence_ids']) for r in rows)
                if not valid:
                    previous = next((g for g in analysis.get('missing_evidence', [])
                                     if g['technology'] == tech and g['item'] == criterion), None)
                    gaps.append(previous or {'technology':tech,'perspective':perspective,'item':criterion,'reason':'검증된 인용 근거 없음'})
    return {'missing_evidence': deduplicate_gaps(gaps)}
