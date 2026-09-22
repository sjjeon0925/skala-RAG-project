import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from rag.pipeline import Document, split_documents, reciprocal_rank_fusion, tokenize, HybridRetriever, load_documents, chunk_to_evidence


class Tokenizer:
    def __call__(self,text,**kwargs):return {'offset_mapping':[(m.start(),m.end()) for m in re.finditer(r'\S+',text)]}
    def encode(self,text,**kwargs):return list(range(len(text.split())))


class Vector:
    def ranked(self,query,count):return [0,1,2]


class Retrieval(unittest.TestCase):
    def test_rrf_deduplicates(self):
        ranks=reciprocal_rank_fusion(['a','a','b'],['b','a'])
        self.assertEqual(len(ranks),2)
        self.assertEqual(ranks[0][1],1/61+1/62)

    def test_tokenize(self):
        self.assertEqual(tokenize('CXL-PIM의 TTFT NVMe'),['cxl-pim','ttft','nvme'])

    def test_page_and_table_parent_preserved(self):
        content='Table 1 throughput ms GPU A100\n\n'+' '.join(f'w{i}' for i in range(950))
        meta={'document_id':'ITME','technology':'ITME','role':'core','source':{'url':'x'},'source_url':'x','page':3,'protected_table':True}
        chunks=split_documents([Document(content,meta)],tokenizer=Tokenizer())
        self.assertGreater(len(chunks),1)
        for c in chunks:
            self.assertEqual(c.page_content,content)
            self.assertLessEqual(len(c.metadata['embedding_text'].split()),400)
            self.assertEqual(c.metadata['page'],3)
        self.assertEqual([c.metadata['chunk_id'] for c in chunks],[c.metadata['chunk_id'] for c in split_documents([Document(content,meta)],tokenizer=Tokenizer())])

    def test_filter_before_top_k(self):
        chunks=[]
        for i,tech in enumerate(['CXL-PIM','ITME','CENT']):
            chunks.append(Document(tech,{'document_id':tech,'technology':tech,'role':'supporting' if tech=='CENT' else 'core','source':{'url':'x'},'source_url':'x','page':1,'chunk_id':str(i),'embedding_text':tech}))
        r=HybridRetriever(Vector(),chunks)
        self.assertEqual([e['technology'] for e in r.search('ITME',perspective='technical',technology='ITME')],['ITME'])
        self.assertEqual([e['technology'] for e in r.search('CENT',perspective='domain',role='supporting')],['CENT'])
        self.assertEqual(r.search('x',perspective='domain',technology='missing'),[])

    def test_page_limit(self):
        with patch('rag.pipeline.MAX_DOCUMENT_PAGES',1):
            with self.assertRaises(ValueError):load_documents()

    def test_real_manifest(self):
        entries=json.loads(Path('data/documents.json').read_text())
        self.assertEqual(len(entries),7)
        self.assertEqual(sum(e['pages'] for e in entries),116)
        self.assertTrue(all(Path(e['path']).exists() for e in entries))



class ChunkBoundaries(unittest.TestCase):
    def test_overlap_between_paragraphs_and_no_cross_page(self):
        a=' '.join(f'a{i}' for i in range(300));b=' '.join(f'b{i}' for i in range(300))
        doc=Document(a+'\n\n'+b,{'document_id':'D','page':1})
        chunks=split_documents([doc,Document('second page',{'document_id':'D','page':2})],tokenizer=Tokenizer())
        self.assertEqual(chunks[1].page_content.split()[:50],a.split()[-50:])
        self.assertEqual(chunks[-1].metadata['page'],2)
        self.assertEqual(chunks[-1].page_content,'second page')


if __name__ == '__main__':
    unittest.main()
