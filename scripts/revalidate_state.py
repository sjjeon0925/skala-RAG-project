"""저장한 State의 근거를 재검증한다. PDF/웹 검색은 반복하지 않는다."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import PERSPECTIVE_CRITERIA
from evidence import collect_evidence, evidence_errors
from tools.grounding import verify_claims, statements_for_evidence, statements_for_rows
from nodes.evidence import first_evidence_check, second_evidence_check
from nodes.verification import conflict_node
from agents.synthesis import synthesis_agent
from agents.report import report_agent


def revalidate(state):
    index=collect_evidence(state)
    index={key:ev for key,ev in index.items() if not evidence_errors(ev)}
    accepted=verify_claims(statements_for_evidence(index))
    print('Evidence accepted:',len(accepted),'/',len(index),flush=True)
    state['technical_evidence']={key:ev for key,ev in state['technical_evidence'].items() if key in accepted}
    for p in PERSPECTIVE_CRITERIA:
        analysis=state[p+'_analysis']
        analysis['evidence']={key:ev for key,ev in analysis['evidence'].items() if key in accepted}
        rows=[]
        for row in analysis['results']:
            row['evidence_ids']=[i for i in row['evidence_ids'] if i in accepted]
            if row['evidence_ids']:rows.append(row)
        valid=verify_claims(statements_for_rows(rows,index)) if rows else set()
        analysis['results']=[row for n,row in enumerate(rows) if str(n) in valid]
        analysis['evidence_ids']=list(dict.fromkeys(i for r in analysis['results'] for i in r['evidence_ids']))
    claims={r['claim'] for p in PERSPECTIVE_CRITERIA for r in state[p+'_analysis']['results']}
    counters={}
    for key,c in state['counter_evidence'].items():
        if c['target_claim'] not in claims:continue
        c['evidence']={i:ev for i,ev in c['evidence'].items() if i in accepted}
        c['evidence_ids']=[i for i in c['evidence_ids'] if i in accepted]
        c['status']='found' if c['evidence'] else 'not_found'
        c['counter_claim']=' / '.join(e['claim'] for e in c['evidence'].values())
        counters[key]=c
    state['counter_evidence']=counters
    state.update(first_evidence_check(state));state.update(second_evidence_check(state))
    checkpoint=Path('outputs/revalidation-state.json')
    checkpoint.parent.mkdir(parents=True,exist_ok=True)
    checkpoint.write_text(json.dumps(state,ensure_ascii=False,indent=2))
    state.update(conflict_node(state));state.update(synthesis_agent(state))
    checkpoint.write_text(json.dumps(state,ensure_ascii=False,indent=2))
    state.update(report_agent(state))
    return state


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('state',type=Path)
    parser.add_argument('--output',type=Path,default=Path('outputs/revalidated-report.md'))
    args=parser.parse_args()
    result=revalidate(json.loads(args.state.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(result['final_report'])
    args.output.with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('Saved:',args.output,'sources:',len(result['references']),'gaps:',len(result['missing_evidence']))


if __name__=='__main__':main()
