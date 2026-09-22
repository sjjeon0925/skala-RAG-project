import unittest
from tools.llm import encode_evidence_refs,decode_evidence_refs


class CitationAliases(unittest.TestCase):
    def test_reversible_and_no_collision(self):
        eid='technical-ITME-1234567890abcdef'
        data={'evidence':{eid:{'content':'R00000 is original text'}},'evidence_ids':[eid]}
        encoded,aliases=encode_evidence_refs(data)
        import json
        self.assertEqual(decode_evidence_refs(json.loads(encoded),aliases),data)
        self.assertNotIn('R00000',aliases)
        self.assertNotIn(eid,encoded)

    def test_unknown_id_stays_unknown(self):
        self.assertEqual(decode_evidence_refs(['R99999'],{'R00000':'valid-id'}),['R99999'])


if __name__=='__main__':unittest.main()
