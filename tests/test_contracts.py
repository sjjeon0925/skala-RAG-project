import copy
import unittest
from unittest.mock import patch

from config import TECHNICAL_EVIDENCE_ITEMS, PERSPECTIVE_CRITERIA
from state import ResearchState, initial_state
from nodes.evidence import first_evidence_check, route_first_evidence, query_rewrite, second_evidence_check
from evidence import evidence_errors, collect_evidence
from agents.report import report_agent, validate_statement, validate_report
from tools.web_search import relevance


def evidence(tech='ITME', perspective='technical', criterion='작동 원리', suffix='one'):
    eid = f'{perspective}-{tech}-{suffix}'
    return {'evidence_id':eid,'technology':tech,'perspective':perspective,'criterion':criterion,
            'claim':'메모리를 확장한다.','content':'메모리를 확장한다.',
            'source':{'title':'Paper','url':f'https://example.org/{tech}','document_id':tech},
            'page':1,'experimental_condition':{},'quantitative':False,'scope':'direct','kind':'fact'}


class Contracts(unittest.TestCase):
    def test_state_and_retry_bound(self):
        state = initial_state()
        self.assertEqual(len(ResearchState.__annotations__),16)
        self.assertEqual(len(state['search_queries']),18)
        state.update(first_evidence_check(state))
        self.assertEqual(route_first_evidence(state),'rewrite')
        for _ in range(2):
            before = copy.deepcopy(state)
            update = query_rewrite(state)
            self.assertEqual(state,before)
            self.assertEqual(set(update),{'search_queries','retry_count'})
            state.update(update)
        self.assertEqual(route_first_evidence(state),'evaluate')
        with self.assertRaises(ValueError):query_rewrite(state)

    def test_resolved_gaps_are_removed(self):
        state = initial_state()
        state.update(first_evidence_check(state))
        for tech in state['technologies']:
            for n,item in enumerate(TECHNICAL_EVIDENCE_ITEMS):
                ev=evidence(tech,criterion=item,suffix=str(n))
                state['technical_evidence'][ev['evidence_id']]=ev
        state.update(first_evidence_check(state))
        self.assertFalse(state['missing_evidence'])
        self.assertEqual(route_first_evidence(state),'evaluate')

    def test_second_check_requires_real_ids(self):
        state=initial_state()
        state['market_analysis']={'results':[{'technology':'ITME','criterion':'제품화','claim':'x','evidence_ids':['missing']}]}
        gaps=second_evidence_check(state)['missing_evidence']
        self.assertEqual(len(gaps),sum(len(c) for c in PERSPECTIVE_CRITERIA.values())*2)
        self.assertTrue(any(g['item']=='제품화' for g in gaps))

    def test_invalid_numeric_evidence(self):
        ev=evidence();ev.update(claim='Latency 3 ms',content='Latency 3 ms',quantitative=True)
        self.assertIn('missing_numeric_conditions',evidence_errors(ev))
        ev['experimental_condition']={'unit':'ms','baseline':'Latency'}
        self.assertFalse(evidence_errors(ev))
        ev['claim']='Latency 30 ms'
        self.assertIn('numeric_mismatch',evidence_errors(ev))

    def test_report_replaces_references(self):
        state=initial_state(); ev=evidence()
        state['technical_evidence']={ev['evidence_id']:ev}
        state['references']=[{'url':'https://unused.example'}]
        out=report_agent(state)
        self.assertEqual(out['references'],[ev['source']])
        self.assertIn(ev['evidence_id'],out['final_report'])
        self.assertNotIn('unused.example',out['final_report'])

    def test_unit_mismatch_and_unknown_id(self):
        ev=evidence();ev.update(claim='Latency 3 ms',content='Latency 3 ms',quantitative=True,
                               experimental_condition={'unit':'ms','baseline':'Latency'})
        index={ev['evidence_id']:ev}
        with self.assertRaises(ValueError):
            validate_statement({'claim':'Latency 3 GB','evidence_ids':list(index)},index)
        state=initial_state()
        with self.assertRaises(ValueError):validate_report('[technical-unknown-id]',state)

    def test_counter_cannot_be_omitted(self):
        state=initial_state();ev=evidence(perspective='counter')
        state['counter_evidence']={'target':{'status':'found','evidence':{ev['evidence_id']:ev}}}
        with self.assertRaises(ValueError):validate_report('',state)

    def test_duplicate_id_detected(self):
        state=initial_state();ev=evidence()
        state['technical_evidence']={ev['evidence_id']:ev}
        other={**ev,'claim':'different'}
        state['domain_analysis']={'evidence':{ev['evidence_id']:other}}
        with self.assertRaises(ValueError):collect_evidence(state)

    def test_relevance_scope(self):
        self.assertEqual(relevance('PNM-KV throughput','CXL-PIM'),'direct')
        self.assertEqual(relevance('CXL industry growth','ITME'),'ecosystem')
        self.assertEqual(relevance('PNM accelerator with CXL','CXL-PIM'),'ecosystem')
        self.assertIsNone(relevance('ITMEX unrelated','ITME'))



class AdditionalValidation(unittest.TestCase):
    def test_ecosystem_is_not_direct_adoption(self):
        state=initial_state();ev=evidence(perspective='market',criterion='실제 도입');ev['scope']='ecosystem'
        state['market_analysis']={'evidence':{ev['evidence_id']:ev},'results':[{'technology':'ITME','criterion':'실제 도입','claim':'CXL 시장은 성장한다.','evidence_ids':[ev['evidence_id']],'scope':'ecosystem'}]}
        gaps=second_evidence_check(state)['missing_evidence']
        self.assertTrue(any(g['technology']=='ITME' and g['item']=='실제 도입' for g in gaps))

    def test_quote_normalization_does_not_change_numbers(self):
        from evidence import quote_matches
        self.assertTrue(quote_matches('memory expansion','mem-\nory  expansion'))
        self.assertFalse(quote_matches('3 ms','30 ms'))

    def test_missing_conditions_cannot_be_invented(self):
        ev=evidence();ev.update(claim='Latency 3 ms',content='Latency 3 ms',quantitative=True,
                               experimental_condition={'unit':'ms','baseline':'unmentioned GPU'})
        self.assertIn('condition_mismatch',evidence_errors(ev))

    def test_invalid_source_type_is_rejected(self):
        ev=evidence();ev['source']='not a source object'
        self.assertIn('citation_mismatch',evidence_errors(ev))

    def test_publication_year_uses_verified_metadata(self):
        ev=evidence();ev['source']['published_at']='2025'
        index={ev['evidence_id']:ev}
        validate_statement({'claim':'2025년 연구이다.','evidence_ids':list(index)},index)
        with self.assertRaises(ValueError):
            validate_statement({'claim':'2024년 연구이다.','evidence_ids':list(index)},index)

    def test_evidence_id_is_not_a_measurement(self):
        ev=evidence(suffix='9a355dad91ee44d3')
        validate_statement({'claim':'메모리를 확장한다. 근거: '+ev['evidence_id'],
                            'evidence_ids':[ev['evidence_id']]},{ev['evidence_id']:ev})

class SourceIdentity(unittest.TestCase):
    def test_cent_is_not_the_target_cxl_pim(self):
        self.assertEqual(relevance('CENT: PIM Is All You Need CXL-PIM system','CXL-PIM'),'comparison')
        self.assertEqual(relevance('CXL-PIM industry ecosystem','CXL-PIM'),'ecosystem')


if __name__ == '__main__':
    unittest.main()
