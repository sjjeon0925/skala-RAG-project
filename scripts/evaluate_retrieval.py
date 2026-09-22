"""작은 정답 페이지 세트에 대한 small/base 비교. 결과는 실행해서만 기록한다."""
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import PROJECT_ROOT
from rag.pipeline import E5Embeddings, VectorIndex, build_hybrid_retriever, load_documents, split_documents, get_tokenizer


def main():
    import faiss
    import numpy as np
    docs = load_documents()
    cases=json.loads((PROJECT_ROOT/'data/retrieval_cases.json').read_text())
    # Verify annotations against actual original pages before reporting retrieval metrics.
    for case in cases:
        matching=[d for d in docs if d.metadata['technology']==case['technology'] and d.metadata['page'] in case['expected_pages']]
        if not any(case['anchor'] in d.page_content for d in matching):
            raise ValueError(f"Invalid page label: {case['technology']} {case['criterion']}")
    results=[]
    for suffix in ('small','base'):
        model='intfloat/multilingual-e5-'+suffix
        started=perf_counter()
        embeddings=E5Embeddings(model)
        chunks=split_documents(docs,tokenizer=get_tokenizer(model))
        vectors=np.asarray(embeddings.embed_documents([c.metadata['embedding_text'] for c in chunks]),dtype='float32')
        index=faiss.IndexFlatIP(vectors.shape[1]);index.add(vectors)
        retriever=build_hybrid_retriever(VectorIndex(index,embeddings),chunks)
        build_seconds=perf_counter()-started
        rows=[]
        for case in cases:
            start=perf_counter()
            hits=retriever.search(case['query'],perspective='technical',technology=case['technology'],role='core',k=5)
            seconds=perf_counter()-start
            rank=next((rank for rank,hit in enumerate(hits,1) if hit['page'] in case['expected_pages']),None)
            rows.append({**case,'retrieved_pages':[h['page'] for h in hits],'hit_at_5':bool(rank),'rr':1/rank if rank else 0,'seconds':seconds})
        results.append({'model':model,'build_seconds':build_seconds,'chunks':len(chunks),'hit_rate_at_5':sum(r['hit_at_5'] for r in rows)/len(rows),'mrr_at_5':sum(r['rr'] for r in rows)/len(rows),'mean_query_seconds':sum(r['seconds'] for r in rows)/len(rows),'cases':rows})
        print(model,results[-1]['hit_rate_at_5'],results[-1]['mrr_at_5'],flush=True)
    (PROJECT_ROOT/'docs/retrieval-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
