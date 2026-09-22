import unittest
import os
from unittest.mock import patch

from graph import build_graph
from state import initial_state
from config import PERSPECTIVE_CRITERIA


class GraphFlow(unittest.TestCase):
    def test_retry_limit_and_parallel_ownership(self):
        calls=[]
        def technical(state):
            calls.append(('technical',state['retry_count']))
            return {'technical_evidence':{}}
        def evaluator(name):
            def run(state):
                calls.append((name,state['retry_count']))
                return {name+'_analysis':{'results':[],'evidence':{},'evidence_ids':[],'missing_evidence':[]}}
            return run
        def report(state):
            self.assertTrue(all(state[p+'_analysis'] for p in PERSPECTIVE_CRITERIA))
            self.assertEqual(state['retry_count'],2)
            self.assertEqual(len(state['missing_evidence']),18+36)
            return {'final_report':'verified','references':[]}
        with patch('graph.technical_agent',technical), patch('graph.trl_agent',evaluator('trl')), patch('graph.market_agent',evaluator('market')), patch('graph.stakeholder_agent',evaluator('stakeholder')), patch('graph.domain_agent',evaluator('domain')), patch('graph.counter_evidence_node',lambda s:{'counter_evidence':{}}), patch('graph.conflict_node',lambda s:{'conflicts':[]}), patch('graph.synthesis_agent',lambda s:{'synthesis':{}}), patch('graph.report_agent',report):
            with patch.dict(os.environ, {'LANGCHAIN_TRACING_V2':'false','LANGSMITH_TRACING':'false'}):
                result=build_graph().invoke(initial_state())
        self.assertEqual([retry for name,retry in calls if name=='technical'],[0,1,2])
        self.assertEqual(len(calls),7)
        self.assertEqual(result['final_report'],'verified')


if __name__=='__main__':unittest.main()
