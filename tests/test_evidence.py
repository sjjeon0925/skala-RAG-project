import unittest
from unittest.mock import Mock

from agents.report import render_report
from demo import demo_services
from evidence import extract_evidence, numeric_supported, valid_ids
from graph import build_graph
from schemas import Extraction
from state import initial_state


class EvidenceTests(unittest.TestCase):
    def test_numeric_unit_check_does_not_treat_lpddr5x_as_multiplier(self):
        self.assertTrue(numeric_supported("LPDDR5X 메모리를 사용한다", [{"quote": "LPDDR5X memory"}]))
        self.assertFalse(numeric_supported("처리량이 5x 향상된다", [{"quote": "LPDDR5X memory"}]))

    def test_web_same_quote_has_distinct_ids_for_each_technology(self):
        services = demo_services()
        chunks = services.web.search("test")
        a = extract_evidence(services, chunks, technology="ITME", perspective="market", items=["시장"])
        b = extract_evidence(services, chunks, technology="CXL-PIM", perspective="market", items=["시장"])
        self.assertTrue(a and b)
        self.assertTrue(set(a).isdisjoint(b))

    def test_invalid_quote_source_and_missing_numeric_condition_are_rejected(self):
        services = demo_services()
        chunk = services.retriever.search("", perspective="technical", technology="ITME")[0]
        base = {
            "chunk_id": chunk["chunk_id"],
            "item": "성능",
            "claim": "100x 향상",
            "quote": chunk["content"].split(". ")[0] + ".",
            "kind": "Fact",
            "numeric": True,
            "experimental_condition": "",
            "condition_chunk_id": "",
            "speaker": "",
            "organization": "",
            "published_date": "",
        }
        for change in (
            {},
            {"numeric": False, "quote": "fabricated quote not present"},
            {"numeric": False, "chunk_id": "unknown"},
            {"numeric": False, "item": "unknown"},
        ):
            services.llm = Mock()
            services.llm.generate.return_value = Extraction(facts=[{**base, **change}])
            self.assertEqual(
                extract_evidence(
                    services, [chunk], technology="ITME", perspective="technical", items=["성능"]
                ),
                {},
            )

    def test_report_rejects_unknown_citations_and_omits_unused_references(self):
        state = build_graph("report", demo_services()).invoke(initial_state())
        state["synthesis"]["summary"] = []
        for p in ("trl", "market", "stakeholder", "domain"):
            state[f"{p}_analysis"] = {}
        state["counter_evidence"] = {}
        state["conflicts"] = []
        report = render_report(
            state,
            {
                "sections": [
                    {
                        "section_id": "3.1",
                        "paragraphs": [{"text": "FABRICATED CLAIM", "evidence_ids": ["invented"]}],
                    }
                ]
            },
        )
        self.assertNotIn("FABRICATED CLAIM", report)
        self.assertNotIn("https://example.test", report)

    def test_retrieved_text_without_extraction_is_not_evidence(self):
        from rag.pipeline import chunk_to_evidence

        chunk = demo_services().retriever.search("", perspective="technical")[0]
        item = chunk_to_evidence(chunk, perspective="technical")
        self.assertFalse(valid_ids([item["evidence_id"]], {item["evidence_id"]: item}))

    def test_numeric_condition_can_link_another_page_but_not_another_paper(self):
        services = demo_services()
        chunk = services.retriever.search("", perspective="technical", technology="ITME")[0]
        conditions = {
            **chunk,
            "chunk_id": "condition-page",
            "page": 2,
            "content": "GPU=DEMO model=DEMO context=DEMO batch=DEMO.",
        }
        services.llm = Mock()
        services.llm.generate.return_value = Extraction(
            facts=[
                {
                    "chunk_id": chunk["chunk_id"],
                    "item": "성능",
                    "claim": "DEMO 수치 주장",
                    "quote": chunk["content"].split(". ")[0] + ".",
                    "kind": "Fact",
                    "numeric": True,
                    "experimental_condition": conditions["content"],
                    "condition_chunk_id": "condition-page",
                    "speaker": "",
                    "organization": "",
                    "published_date": "",
                }
            ]
        )
        result = extract_evidence(
            services, [chunk, conditions], technology="ITME", perspective="technical", items=["성능"]
        )
        self.assertEqual(next(iter(result.values()))["condition_source"]["page"], 2)
        conditions["document_id"] = "OTHER"
        self.assertFalse(
            extract_evidence(
                services, [chunk, conditions], technology="ITME", perspective="technical", items=["성능"]
            )
        )


if __name__ == "__main__":
    unittest.main()
