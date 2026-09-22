"""State만 렌더링하며 본문 인용 ID를 검증한 다음 References를 만든다."""
import re

from config import TECHNOLOGY_REASONS, PERSPECTIVE_CRITERIA
from evidence import collect_evidence, evidence_errors, numbers, normalize
from state import ResearchState

CITATION = re.compile(r'\[((?:technical|trl|market|stakeholder|domain|counter)-[A-Za-z0-9-]+)\]')
UNIT_PATTERN = re.compile(r'(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*(?:%|×|x\b|[KMGT]i?B(?:/s)?|ms\b|seconds?\b|tokens?/s)', re.I)


def reference_text(source):
    author = ', '.join(source.get('authors', []))
    date = source.get('published_at', '')
    lead = (author + (f' ({date})' if date else '')).strip()
    venue = source.get('venue') or (f"arXiv:{source['arxiv_id']}" if source.get('arxiv_id') else source.get('site_name', ''))
    return '. '.join(s for s in (lead, source.get('title'), venue, source.get('url')) if s)


def validate_statement(row, index, *, allow_trl=False):
    ids = row.get('evidence_ids', [])
    if not ids or any(i not in index or evidence_errors(index[i]) for i in ids):
        raise ValueError('Invalid report evidence reference')
    claim = row['claim']
    for eid in ids:
        claim = claim.replace(eid, '')
    text = ' '.join(index[i]['content'] for i in ids)
    allowed = numbers(text)
    # Bibliographic dates are verified metadata, not experimental measurements.
    for eid in ids:
        date = index[eid]['source'].get('published_at', '')
        for year in re.findall(r'\b\d{4}\b', date):
            if re.search(rf'\b{year}\s*년', claim):
                allowed.add(year)
    if allow_trl and ('공개 정보 기반 TRL 추정' in claim or 'TRL' in claim):
        allowed |= set(str(i) for i in range(1,10))
    if not numbers(claim).issubset(allowed):
        raise ValueError('Report numeric mismatch')
    units = {normalize(m.group()).replace(' ','').lower() for m in UNIT_PATTERN.finditer(text)}
    if any(normalize(m.group()).replace(' ','').lower() not in units for m in UNIT_PATTERN.finditer(claim)):
        raise ValueError('Report numeric unit mismatch')


def validate_report(report, state):
    index = collect_evidence(state)
    cited = list(dict.fromkeys(CITATION.findall(report)))
    if any(eid not in index for eid in cited):
        raise ValueError('Unknown citation in report')
    required = {i for c in state.get('counter_evidence', {}).values() if c['status'] == 'found' for i in c['evidence']}
    in_synthesis = {i for rows in state.get('synthesis', {}).values() for row in rows for i in row['evidence_ids']}
    if not required.issubset(in_synthesis) or not required.issubset(set(cited)):
        raise ValueError('Found counter evidence omitted from synthesis/report')
    references = []
    seen = set()
    for eid in cited:
        ev = index[eid]
        if evidence_errors(ev):
            raise ValueError('Invalid cited evidence')
        source = ev['source']
        key = source.get('url') or source.get('document_id')
        if key not in seen:
            references.append(source)
            seen.add(key)
    return references


def report_agent(state: ResearchState) -> dict:
    index = collect_evidence(state)
    def render(row, allow_trl=False):
        row = dict(row)
        for eid in row['evidence_ids']:
            row['claim'] = row['claim'].replace(eid, '')
        row['claim'] = re.sub(r'\((?:증거|근거|출처)\s*:\s*[,;\s]*\)', '', row['claim']).strip()
        if 'TRL' in row['claim']:
            trl_rows = state.get('trl_analysis', {}).get('results', [])
            allowed_stages = set().union(*(numbers(r['claim']) for r in trl_rows if set(r['evidence_ids']) & set(row['evidence_ids']))) if trl_rows else set()
            derived = numbers(row['claim']) - numbers(' '.join(index[i]['content'] for i in row['evidence_ids'] if i in index))
            allow_trl = allow_trl or bool(derived and derived.issubset(allowed_stages))
        validate_statement(row,index,allow_trl=allow_trl)
        citation = ' '.join(f'[{eid}]' for eid in row['evidence_ids'])
        # Original conditions appear before the result and retain exact strings.
        conditions = []
        for eid in row['evidence_ids']:
            ev = index[eid]
            if ev.get('experimental_condition'):
                conditions.append('; '.join(f'{k}={v}' for k,v in ev['experimental_condition'].items()))
        prefix = ('조건: ' + ' / '.join(dict.fromkeys(conditions)) + '. ') if conditions else ''
        scope = row.get('scope','direct')
        label = {'direct':'','ecosystem':'[상위 시장·생태계] ','comparison':'[보조 문서 비교 맥락] '}.get(scope,'')
        return f'- {label}{prefix}{row["claim"]} {citation}'

    synthesis = state.get('synthesis',{})
    summary = synthesis.get('summary', [])
    # Markdown has no fixed pages; enforce a conservative character budget.
    if sum(len(row['claim']) for row in summary) > 700:
        raise ValueError('Summary exceeds half-page text budget')
    lines = ['# SUMMARY'] + [render(row) for row in summary]
    lines += ['','## 1. 분석 배경 및 문제 정의',f"분석 범위: {state['domain']} 환경의 KV Cache 확장과 데이터 이동 비용.",
              '', '## 2. 평가 대상 기술 선정']
    lines += [f'- {tech}: {TECHNOLOGY_REASONS[tech]}' for tech in state['technologies']]
    lines += ['', '## 3. 기술 개요']
    for eid, ev in state['technical_evidence'].items():
        lines.append(render({'claim':f"{ev['technology']} / {ev['criterion']}: {ev['claim']}",'evidence_ids':[eid]}))
    lines += ['', '## 4. 다관점 평가']
    for section, (p,title) in enumerate(zip(PERSPECTIVE_CRITERIA,('기술 성숙도','시장성','이해관계자','데이터센터·클라우드 적용성')),1):
        lines += ['',f'### 4.{section} {title}']
        for row in state.get(f'{p}_analysis',{}).get('results',[]):
            lines.append(render({**row,'claim':f"{row['technology']} / {row['criterion']}: {row['claim']}"}, allow_trl=p=='trl'))
            if p == 'stakeholder':
                for eid in row['evidence_ids']:
                    e = index[eid]
                    lines.append(f"  - 구분: {e.get('kind')}; 발언자: {e.get('speaker') or '미확인'}; 소속: {e.get('affiliation') or '미확인'}; 발행일: {e.get('published_at') or '미확인'}")
    lines += ['', '## 5. 관점 간 종합 및 시사점']
    for key,label in (('consensus','공통점'),('differences','관점 차이'),('tradeoffs','Trade-off'),('limitations','주장 성립 조건과 반대 근거')):
        lines.append(f'\n**{label}**')
        lines += [render(row) for row in synthesis.get(key,[])]
    for conflict in state['conflicts']:
        ids = conflict['left_evidence_ids'] + conflict['right_evidence_ids']
        lines.append(render({'claim':conflict['claim'] + ' ' + conflict['condition_difference'],'evidence_ids':ids}))
    lines += ['', '## 6. 분석 한계 및 신뢰성 확보',
              '서로 다른 실험 조건의 결과는 직접 비교하기 어렵다. 반대 근거 not_found는 검색 범위에서 미확인이라는 뜻이다.']
    for gap in state['missing_evidence']:
        lines.append(f"- {gap['technology']} / {gap['perspective']} / {gap['item']}: {gap['reason']}")
    not_found = sum(c['status']=='not_found' for c in state['counter_evidence'].values())
    lines.append(f'반대 근거 검색 미확인 주장: {not_found}건.')
    body = '\n'.join(lines)
    references = validate_report(body,state)
    cited = list(dict.fromkeys(CITATION.findall(body)))
    lines += ['', '## REFERENCE']
    for source in references:
        ids = [eid for eid in cited if index[eid]['source']['url'] == source['url']]
        locators = ', '.join(f"{eid}" + (f" (p.{index[eid]['page']})" if index[eid].get('page') else '') for eid in ids)
        lines.append(f'- {reference_text(source)}\n  - 근거: {locators}')
    return {'final_report':'\n'.join(lines)+'\n','references':references}
