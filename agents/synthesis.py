from config import PERSPECTIVE_CRITERIA
from evidence import collect_evidence, LOGGER
from state import ResearchState
from tools.llm import complete_json, object_schema
from tools.grounding import verify_claims, statements_for_rows

ENTRY = object_schema({'claim':{'type':'string'},'evidence_ids':{'type':'array','items':{'type':'string'}}})
SCHEMA = object_schema({key:{'type':'array','items':ENTRY} for key in ('summary','consensus','differences','tradeoffs','limitations')})


def synthesis_agent(state: ResearchState) -> dict:
    index = collect_evidence(state)
    synthesis = complete_json(
        '입력 State만 사용하는 평가 종합 Agent. 검색이나 새로운 평가를 하지 않는다. 한국어로 공통점, 차이, Trade-off, 한계를 요약한다. '
        '입력 근거 ID만 사용한다. 반대 근거가 결론을 제한하면 반드시 limitations와 summary에 반영한다. '
        'summary는 총 500자 이내. 수치·단위·조건은 새로운 값으로 바꾸지 않는다. 조건이 다른 결과를 모순으로 단정하지 않는다. 승자나 추천을 정하지 않는다.',
        {'analyses':{p:state.get(f'{p}_analysis',{}) for p in PERSPECTIVE_CRITERIA},
         'evidence':index,'counter_evidence':state['counter_evidence'],'conflicts':state['conflicts'],
         'missing_evidence':state['missing_evidence']},SCHEMA)
    for key, rows in synthesis.items():
        valid = []
        for row in rows:
            if not row['evidence_ids'] or any(i not in index for i in row['evidence_ids']):
                LOGGER.info('SYNTHESIS_REJECTED | invalid_evidence_id')
                continue
            valid.append(row)
        synthesis[key] = valid
    flat = [row for rows in synthesis.values() for row in rows]
    supported = verify_claims(statements_for_rows(flat, index)) if flat else set()
    cursor = 0
    for key, rows in synthesis.items():
        synthesis[key] = [r for n,r in enumerate(rows, cursor) if str(n) in supported]
        cursor += len(rows)
    # Preserve every found counter-evidence as a visible limitation even when the
    # model summary omits it. Do not turn not_found into proof that no objection exists.
    covered = {i for row in synthesis['limitations'] for i in row['evidence_ids']}
    for counter in state['counter_evidence'].values():
        if counter['status'] == 'found':
            for key, ev in counter['evidence'].items():
                if key not in covered:
                    synthesis['limitations'].append({'claim':ev['claim'],'evidence_ids':[key]})
    return {'synthesis':synthesis}
