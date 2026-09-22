"""기술 × 기준별 한정 검색과 평가. 각 Agent는 자신의 analysis만 갱신한다."""
from config import PERSPECTIVE_CRITERIA, QUERY_TERMS, MAX_WEB_ATTEMPTS, RESULTS_PER_CRITERION, PROJECT_ROOT
from evidence import normalize
from agents.extraction import extract_evidence
from tools.web_search import search_web, relevance
from tools.llm import complete_json, object_schema
from rag.pipeline import get_retriever
from tools.grounding import verify_claims, statements_for_rows

ASSESSMENT_SCHEMA = object_schema({
    'claim': {'type':'string'},
    'evidence_ids': {'type':'array','items':{'type':'string'}},
    'missing_reason': {'type':'string'},
})


def assess(state, perspective):
    evidence, results, gaps = {}, [], []
    criteria = PERSPECTIVE_CRITERIA[perspective]
    for tech in state['technologies']:
        for criterion in criteria:
            found = {}
            reason = '검색되지 않음'
            query = f'{tech} {QUERY_TERMS[criterion]}'
            reused = {key: value for key,value in state['technical_evidence'].items() if value['technology'] == tech} if perspective in ('trl','domain') else {}
            if perspective == 'domain':
                retriever = get_retriever()
                candidates = retriever.search(query, perspective=perspective, technology=tech, role='core', k=RESULTS_PER_CRITERION)
                # All supporting papers participate; never relabel them as the target technology.
                candidates += retriever.search(query, perspective=perspective, role='supporting', k=RESULTS_PER_CRITERION)
                found, reason = extract_evidence(candidates, technology=tech, perspective=perspective, criterion=criterion)
            else:
                for attempt in range(MAX_WEB_ATTEMPTS):
                    search_query = query if attempt == 0 else query + ' research industry official statement'
                    candidates = []
                    for row in search_web(search_query):
                        scope = relevance(row['source']['title'] + ' ' + row['content'], tech)
                        if scope and scope != 'comparison' and (perspective == 'market' or scope == 'direct'):
                            candidates.append({**row, 'scope': scope})
                    found, reason = extract_evidence(candidates[:RESULTS_PER_CRITERION], technology=tech, perspective=perspective, criterion=criterion)
                    if found:
                        break
            evidence.update(found)
            available = {**reused, **found}
            if not available:
                gaps.append({'technology':tech,'perspective':perspective,'item':criterion,'reason':reason})
                continue
            instructions = (PROJECT_ROOT / 'prompts/assessment.md').read_text()
            if perspective == 'trl':
                instructions += '\n' + (PROJECT_ROOT / 'prompts/trl.md').read_text()
            output = complete_json(instructions, {'technology':tech,'perspective':perspective,'criterion':criterion,'evidence':available}, ASSESSMENT_SCHEMA)
            ids = list(dict.fromkeys(output['evidence_ids']))
            # No generated numerical paraphrases: numeric assessment statements must
            # retain an exact validated evidence claim. TRL estimates have a distinct rule.
            if not output['claim'] or not ids or any(i not in available for i in ids):
                gaps.append({'technology':tech,'perspective':perspective,'item':criterion,'reason':output['missing_reason'] or '검증 탈락'})
                continue
            from evidence import numbers
            if perspective != 'trl' and numbers(output['claim']) and not any(normalize(output['claim']) == normalize(available[i]['claim']) for i in ids):
                # Keep evidence claims and conditions verbatim instead of publishing an unchecked number.
                output['claim'] = ' / '.join(available[i]['claim'] for i in ids)
            if perspective == 'trl' and '공개 정보 기반 TRL 추정' not in output['claim']:
                output['claim'] = '공개 정보 기반 TRL 추정: ' + output['claim']
            scope = 'direct' if all(available[i]['scope'] == 'direct' for i in ids) else 'comparison' if any(available[i]['scope'] == 'comparison' for i in ids) else 'ecosystem'
            results.append({'technology':tech,'criterion':criterion,'claim':output['claim'],'evidence_ids':ids,'scope':scope})
    index = {**state['technical_evidence'], **evidence}
    supported = verify_claims(statements_for_rows(results, index)) if results else set()
    for n,row in enumerate(results):
        if str(n) not in supported:
            gaps.append({'technology':row['technology'],'perspective':perspective,'item':row['criterion'],'reason':'검증 탈락: 주장과 원문의 대상·의미 불일치'})
    results = [r for n,r in enumerate(results) if str(n) in supported]
    seen = set()
    results = [r for r in results if not ((r['technology'],r['criterion']) in seen or seen.add((r['technology'],r['criterion'])))]
    analysis = {'results':results,'evidence':evidence,'evidence_ids':list(dict.fromkeys(i for r in results for i in r['evidence_ids'])),'missing_evidence':gaps}
    return {f'{perspective}_analysis':analysis}
