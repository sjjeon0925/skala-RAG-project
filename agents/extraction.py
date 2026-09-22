from pathlib import Path

from config import PROJECT_ROOT
from evidence import normalize, quote_matches, evidence_errors, stable_id, LOGGER
from tools.llm import complete_json, object_schema
from tools.grounding import verify_claims, statements_for_evidence

STRING = {'type': 'string'}
NULLABLE = {'type': ['string', 'null']}
CONDITIONS = object_schema({key: NULLABLE for key in ('unit','baseline','gpu','model','context','requests','other')})
ITEM = object_schema({
    'source_id': STRING, 'claim': STRING, 'quote': STRING,
    'quantitative': {'type': 'boolean'}, 'experimental_condition': CONDITIONS,
    'kind': {'type':'string','enum':['fact','opinion','interpretation']},
    'speaker': NULLABLE, 'affiliation': NULLABLE, 'published_at': NULLABLE,
})
SCHEMA = object_schema({'items': {'type': 'array', 'items': ITEM}})


def extract_evidence(candidates, *, technology, perspective, criterion, context='', complete=complete_json, verify=verify_claims):
    if not candidates:
        return {}, '검색되지 않음'
    unique = {}
    for candidate in candidates:
        unique.setdefault((candidate['source']['url'], candidate.get('page'), candidate['content']), candidate)
    candidates = list(unique.values())
    by_id = {c['evidence_id']: c for c in candidates}
    instructions = (PROJECT_ROOT / 'prompts/extraction.md').read_text()
    payload = {'technology': technology, 'perspective': perspective, 'criterion': criterion,
               'context': context, 'sources': candidates}
    accepted = {}
    for attempt in range(2):  # 최초 추출 + 검증 실패 교정 1회
        response = complete(instructions, payload, SCHEMA)
        rejected = []
        for item in response.get('items', [])[:2]:
            candidate = by_id.get(item.get('source_id'))
            reason = None
            if candidate is None:
                reason = 'citation_mismatch'
            elif not quote_matches(item.get('quote', ''), candidate['content']):
                reason = 'citation_mismatch'
            elif candidate.get('role') == 'core' and candidate.get('technology') != technology:
                reason = 'technology_mismatch'
            if reason:
                rejected.append(reason)
                continue
            scope = candidate.get('scope', 'comparison' if candidate.get('role') == 'supporting' else 'direct')
            eid = stable_id(perspective, technology, criterion, item['source_id'], item['claim'])
            evidence = {
                'evidence_id': eid, 'technology': technology, 'perspective': perspective,
                'criterion': criterion, 'claim': item['claim'], 'source': candidate['source'],
                'content': item['quote'], 'experimental_condition': {k:v for k,v in item['experimental_condition'].items() if v},
                'quantitative': item['quantitative'], 'scope': scope, 'kind': item['kind'],
                'speaker': item['speaker'], 'affiliation': item['affiliation'],
                'published_at': item['published_at'],
            }
            if candidate.get('page'):
                evidence['page'] = candidate['page']
            for field in ('speaker', 'affiliation', 'published_at'):
                value = evidence.get(field)
                if value and not quote_matches(value, candidate['content']) and value != candidate['source'].get(field):
                    evidence[field] = None
            errors = evidence_errors(evidence)
            if errors:
                rejected.extend(errors)
            else:
                accepted[eid] = evidence
        for reason in rejected:
            LOGGER.info('EVIDENCE_REJECTED | %s | %s | %s | %s', perspective, technology, criterion, reason)
        if not rejected:
            break
        payload['correction'] = {'previous_response':response, 'reasons': sorted(set(rejected)), 'instruction': '실패한 인용·수치 조건을 원문에서 확인해 교정. quote는 연속 원문이며 조건 값도 quote 안의 문자열이어야 한다. 불가능하면 생략.'}
    if accepted:
        supported = verify(statements_for_evidence(accepted))
        for eid in set(accepted) - supported:
            LOGGER.info('EVIDENCE_REJECTED | %s | %s | %s | unsupported_claim', perspective, technology, criterion)
            accepted.pop(eid)
            rejected.append('unsupported_claim')
    return dict(list(accepted.items())[:2]), ('검증 탈락' if rejected else '공개 자료 부족') if not accepted else ''
