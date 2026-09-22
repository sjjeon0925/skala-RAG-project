"""라벨이 있는 20개 질의로 multilingual-e5-small/base를 비교한다."""

import json
from dataclasses import replace
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import PROJECT_ROOT, Settings
from rag.pipeline import build_hybrid_retriever, build_index, E5Embeddings, load_documents, split_documents


def main():
    documents = load_documents()
    cases = json.loads((PROJECT_ROOT / "data/retrieval_cases.json").read_text())
    for case in cases:
        pages = [
            row for row in documents
            if row["technology"] == case["technology"] and row["page"] in case["expected_pages"]
        ]
        if not any(case["anchor"] in row["content"] for row in pages):
            raise ValueError(f"잘못된 검색 평가 라벨: {case['technology']} / {case['criterion']}")
    output = []
    for suffix in ("small", "base"):
        settings = replace(
            Settings(),
            embedding_model=f"intfloat/multilingual-e5-{suffix}",
            embedding_revision=None,
        )
        started = perf_counter()
        embeddings = E5Embeddings(settings)
        chunks = split_documents(documents, tokenizer=embeddings.tokenizer, settings=settings)
        retriever = build_hybrid_retriever(
            build_index(chunks, embeddings), chunks, embeddings, settings
        )
        build_seconds = perf_counter() - started
        rows = []
        for case in cases:
            query_started = perf_counter()
            hits = retriever.search(
                case["query"],
                perspective="retrieval_eval",
                technology=case["technology"],
                role="core",
                k=5,
            )
            elapsed = perf_counter() - query_started
            rank = next(
                (rank for rank, hit in enumerate(hits, 1) if hit["page"] in case["expected_pages"]),
                None,
            )
            rows.append(
                {
                    **case,
                    "retrieved_pages": [hit["page"] for hit in hits],
                    "hit_at_5": rank is not None,
                    "rr": 1 / rank if rank else 0,
                    "seconds": elapsed,
                }
            )
        output.append(
            {
                "model": settings.embedding_model,
                "build_seconds": build_seconds,
                "chunks": len(chunks),
                "hit_rate_at_5": sum(row["hit_at_5"] for row in rows) / len(rows),
                "mrr_at_5": sum(row["rr"] for row in rows) / len(rows),
                "mean_query_seconds": sum(row["seconds"] for row in rows) / len(rows),
                "cases": rows,
            }
        )
    (PROJECT_ROOT / "docs/retrieval-results.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
