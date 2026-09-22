"""페이지 보존, 표 parent 청크, e5 + BM25 + RRF. 선택 의존성은 사용 시 로드한다."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re

from config import (DOCUMENT_MANIFEST, PROJECT_ROOT, EMBEDDING_MODEL, INDEX_DIR,
                    MAX_DOCUMENT_PAGES, CHUNK_SIZE, CHUNK_OVERLAP, DENSE_TOP_K,
                    BM25_TOP_K, TOP_K, RRF_K)


@dataclass
class Document:
    page_content: str
    metadata: dict


def clean_text(text: str) -> str:
    text = re.sub(r'(\w)-\n(?=[a-z])', r'\1', text)
    return re.sub(r'[ \t]+', ' ', text).strip()


def load_documents(manifest: Path = DOCUMENT_MANIFEST) -> list[Document]:
    import pymupdf
    entries = json.loads(Path(manifest).read_text())
    root = Path(manifest).resolve().parent.parent
    paths = [(entry, root / entry['path']) for entry in entries]
    total = 0
    for entry, path in paths:
        with pymupdf.open(path) as pdf:
            total += len(pdf)
            if entry.get('pages') and entry['pages'] != len(pdf):
                raise ValueError(f"Page count mismatch: {entry['document_id']}")
    if total > MAX_DOCUMENT_PAGES:
        raise ValueError(f'{total} pages exceeds limit {MAX_DOCUMENT_PAGES}')
    documents = []
    for entry, path in paths:
        with pymupdf.open(path) as pdf:
            for number, page in enumerate(pdf, 1):
                blocks = [b for b in page.get_text('blocks', sort=True) if b[6] == 0]
                paragraphs = [clean_text(b[4]) for b in blocks if clean_text(b[4])]
                # Do not split a detected table from caption/units/context. Store the full
                # original page as its parent; bounded child windows are embedded below.
                tables = page.find_tables().tables
                captions = any(re.search(r'\bTable\s+\d+[.:]', p, re.I) for p in paragraphs)
                protected = bool(tables) or captions
                source = {k: entry[k] for k in ('document_id','title','authors','published_at','venue','arxiv_id') if entry.get(k)}
                source['url'] = entry['source_url']
                metadata = {
                    'technology': entry['technology'], 'document_id': entry['document_id'],
                    'page': number, 'role': entry['role'], 'source_url': entry['source_url'],
                    'source': source, 'protected_table': protected,
                    'detected_tables': len(tables),
                }
                text = '\n\n'.join(paragraphs)
                if tables:
                    text += '\n\n' + '\n\n'.join(t.to_markdown() for t in tables)
                documents.append(Document(text, metadata))
    return documents


@lru_cache(maxsize=2)
def get_tokenizer(model_name=EMBEDDING_MODEL):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(model_name, use_fast=True)


def token_windows(text, tokenizer, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Use offsets to preserve original quotes rather than lossy decode()."""
    if not 0 <= overlap < size:
        raise ValueError('overlap must be smaller than chunk size')
    offsets = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True, verbose=False)['offset_mapping']
    for start in range(0, len(offsets), size - overlap):
        end = min(start + size, len(offsets))
        yield text[offsets[start][0]:offsets[end - 1][1]]
        if end == len(offsets):
            break


def split_documents(documents: list, *, tokenizer=None) -> list[Document]:
    tokenizer = tokenizer or get_tokenizer()
    chunks = []
    for doc in documents:
        # Table-bearing pages are indivisible evidence parents; embedding_text is a
        # <=400-token window. Search returns the parent including captions/conditions.
        if doc.metadata.get('protected_table'):
            parts = [(window, doc.page_content) for window in token_windows(doc.page_content, tokenizer)]
        else:
            sections = re.split(r'\n\n(?=\d+(?:\.\d+)*\s+[A-Z])', doc.page_content)
            parts = []
            for section in sections:
                current = ''
                for paragraph in section.split('\n\n'):
                    combined = f'{current}\n\n{paragraph}'.strip()
                    if len(tokenizer.encode(combined, add_special_tokens=False, verbose=False)) <= CHUNK_SIZE:
                        current = combined
                    else:
                        if current:
                            parts.append((current, current))
                            offsets = tokenizer(current, add_special_tokens=False, return_offsets_mapping=True, verbose=False)['offset_mapping']
                            tail = current[offsets[max(0, len(offsets) - CHUNK_OVERLAP)][0]:] if offsets else ''
                            paragraph = tail + '\n\n' + paragraph
                        windows = list(token_windows(paragraph, tokenizer))
                        parts.extend((w, w) for w in windows[:-1])
                        current = windows[-1] if windows else ''
                if current:
                    parts.append((current, current))
        for i, (embedding_text, content) in enumerate(parts):
            chunk_id = f"{doc.metadata['document_id']}-p{doc.metadata['page']}-c{i}"
            chunks.append(Document(content, {**doc.metadata, 'chunk_id': chunk_id, 'embedding_text': embedding_text}))
    return chunks


class E5Embeddings:
    def __init__(self, model_name=EMBEDDING_MODEL):
        import torch
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        torch.set_num_threads(int(os.getenv('EMBEDDING_THREADS', '1')))
        self.model = SentenceTransformer(model_name, device=os.getenv('EMBEDDING_DEVICE', 'cpu'))

    def embed_documents(self, texts):
        return self.model.encode(['passage: ' + text for text in texts], normalize_embeddings=True).tolist()

    def embed_query(self, text):
        return self.model.encode(['query: ' + text], normalize_embeddings=True)[0].tolist()


def build_embeddings():
    return E5Embeddings()


class VectorIndex:
    def __init__(self, index, embeddings):
        self.index, self.embeddings = index, embeddings

    def ranked(self, query, count):
        import numpy as np
        _, indices = self.index.search(np.asarray([self.embeddings.embed_query(query)], dtype='float32'), count)
        return [int(i) for i in indices[0] if i >= 0]


def build_index(chunks, embeddings, index_dir=INDEX_DIR):
    import faiss
    import numpy as np
    if not chunks:
        raise ValueError('Cannot index empty corpus')
    vectors = np.asarray(embeddings.embed_documents([c.metadata['embedding_text'] for c in chunks]), dtype='float32')
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / 'index.faiss'))
    (index_dir / 'chunks.jsonl').write_text('\n'.join(json.dumps(asdict(c), ensure_ascii=False) for c in chunks))
    return VectorIndex(index, embeddings)


def tokenize(text):
    return re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', text.lower())


def reciprocal_rank_fusion(*rankings):
    scores = {}
    for ranking in rankings:
        for rank, key in enumerate(dict.fromkeys(ranking), 1):
            scores[key] = scores.get(key, 0) + 1 / (RRF_K + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def chunk_to_evidence(chunk, *, perspective, score=None):
    m = chunk.metadata
    return {'evidence_id': m['chunk_id'], 'technology': m['technology'],
            'perspective': perspective, 'claim': '', 'source': m['source'],
            'page': m['page'], 'experimental_condition': {}, 'content': chunk.page_content,
            'role': m['role'], 'source_url': m['source_url'], 'score': score}


class HybridRetriever:
    def __init__(self, vectorstore, chunks):
        self.vectorstore, self.chunks = vectorstore, chunks

    def search(self, query, *, perspective, technology=None, role=None, k=TOP_K):
        from rank_bm25 import BM25Okapi
        eligible = [i for i,c in enumerate(self.chunks)
                    if (technology is None or c.metadata['technology'] == technology)
                    and (role is None or c.metadata['role'] == role)]
        if not eligible or k <= 0:
            return []
        eligible_set = set(eligible)
        dense = [i for i in self.vectorstore.ranked(query, len(self.chunks)) if i in eligible_set][:DENSE_TOP_K]
        corpus = [tokenize(self.chunks[i].metadata['embedding_text']) or ['_empty_'] for i in eligible]
        scores = BM25Okapi(corpus).get_scores(tokenize(query))
        sparse = [eligible[j] for j in sorted(range(len(eligible)), key=lambda j: (-scores[j], j)) if scores[j] > 0][:BM25_TOP_K]
        # Rank by stable chunk_id and return each id once.
        keys = lambda indices: [self.chunks[i].metadata['chunk_id'] for i in indices]
        by_id = {self.chunks[i].metadata['chunk_id']: self.chunks[i] for i in eligible}
        return [chunk_to_evidence(by_id[key], perspective=perspective, score=score)
                for key, score in reciprocal_rank_fusion(keys(dense), keys(sparse))[:k]]


def build_hybrid_retriever(vectorstore, chunks):
    return HybridRetriever(vectorstore, chunks)


def corpus_fingerprint(manifest=DOCUMENT_MANIFEST, model_name=EMBEDDING_MODEL):
    manifest = Path(manifest)
    root = manifest.resolve().parent.parent
    files = [root / entry['path'] for entry in json.loads(manifest.read_text())]
    digest = hashlib.sha256(manifest.read_bytes())
    for path in files:
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return {'corpus_sha256': digest.hexdigest(), 'model': model_name,
            'chunk_size': CHUNK_SIZE, 'overlap': CHUNK_OVERLAP, 'pipeline_version': 2}


@lru_cache(maxsize=1)
def get_retriever():
    import faiss
    fingerprint = corpus_fingerprint()
    embeddings = build_embeddings()
    meta = INDEX_DIR / 'meta.json'
    if meta.exists() and all((INDEX_DIR / name).exists() for name in ('index.faiss', 'chunks.jsonl')) and json.loads(meta.read_text()) == fingerprint:
        chunks = [Document(**json.loads(line)) for line in (INDEX_DIR / 'chunks.jsonl').read_text().splitlines()]
        vectorstore = VectorIndex(faiss.read_index(str(INDEX_DIR / 'index.faiss')), embeddings)
    else:
        chunks = split_documents(load_documents())
        vectorstore = build_index(chunks, embeddings)
        meta.write_text(json.dumps(fingerprint, indent=2))
    return build_hybrid_retriever(vectorstore, chunks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inspect', action='store_true', help='PDF 로딩·표 감지 검사 (모델 다운로드 없음)')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--query')
    parser.add_argument('--technology')
    parser.add_argument('--role', choices=['core','supporting'])
    args = parser.parse_args()
    if args.inspect:
        docs = load_documents()
        print(json.dumps({'pages': len(docs), 'table_pages': sum(d.metadata['protected_table'] for d in docs)}, indent=2))
    if args.build or args.query:
        retriever = get_retriever()
        print(f'Chunks: {len(retriever.chunks)}')
        if args.query:
            print(json.dumps(retriever.search(args.query, perspective='technical', technology=args.technology, role=args.role), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
