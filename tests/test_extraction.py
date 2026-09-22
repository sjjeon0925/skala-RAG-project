import unittest

from agents.extraction import extract_evidence
from tools.llm import object_schema


class Extraction(unittest.TestCase):
    def test_one_correction_only(self):
        calls=[]
        def complete(*args):
            calls.append(1)
            return {'items':[{'source_id':'invalid','quote':'unknown','claim':'wrong'}]}
        result,reason=extract_evidence([{'evidence_id':'source','content':'actual','source':{'url':'url'},'technology':'ITME','role':'core'}],technology='ITME',perspective='technical',criterion='작동 원리',complete=complete)
        self.assertEqual(len(calls),2)
        self.assertFalse(result)
        self.assertEqual(reason,'검증 탈락')

    def test_valid_quote_and_metadata(self):
        item={'source_id':'source','quote':'Memory is expanded.','claim':'메모리를 확장한다.','quantitative':False,
              'experimental_condition':{},'kind':'fact','speaker':None,'affiliation':None,'published_at':None}
        result,_=extract_evidence([{'evidence_id':'source','content':'Memory is expanded.','source':{'url':'url'},'technology':'ITME','role':'core','page':2}],technology='ITME',perspective='technical',criterion='작동 원리',complete=lambda *a:{'items':[item]}, verify=lambda rows:{r['statement_id'] for r in rows})
        self.assertEqual(len(result),1)
        self.assertEqual(next(iter(result.values()))['page'],2)



class Grounding(unittest.TestCase):
    def test_semantic_rejection_drops_lexically_valid_quote(self):
        item={'source_id':'source','quote':'CXL is a standard.','claim':'CXL-PIM은 상용 제품이다.','quantitative':False,
              'experimental_condition':{},'kind':'fact','speaker':None,'affiliation':None,'published_at':None}
        result,reason=extract_evidence([{'evidence_id':'source','content':'CXL is a standard.','source':{'url':'url'},'scope':'ecosystem','role':'web'}],technology='CXL-PIM',perspective='market',criterion='제품화',complete=lambda *a:{'items':[item]},verify=lambda rows:set())
        self.assertFalse(result)
        self.assertEqual(reason,'검증 탈락')


if __name__ == '__main__':
    unittest.main()
