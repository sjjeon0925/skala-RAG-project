import json
import unittest
from unittest.mock import Mock

import httpx

from config import Settings
from schemas import Extraction
from tools.llm import OpenAILLM
from tools.web_search import TavilySearch, canonical_url


class ToolTests(unittest.TestCase):
    def test_web_normalizes_deduplicates_and_preserves_snippet_status(self):
        seen = []

        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "url": "https://example.test/p#x",
                            "title": "paper",
                            "content": "a useful search excerpt",
                        },
                        {"url": "https://example.test/p#y", "content": "duplicate"},
                        {"url": "javascript:alert(1)", "content": "bad"},
                    ]
                },
            )

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            results = TavilySearch(Settings(), client).search("query")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_url"], "https://example.test/p")
        self.assertEqual(results[0]["content_type"], "snippet")
        self.assertFalse(seen[0]["include_answer"])

    def test_http_error_is_not_not_found(self):
        with (
            httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(401))) as client,
            self.assertRaises(httpx.HTTPStatusError),
        ):
            TavilySearch(Settings(), client).search("query")

    def test_llm_uses_schema_and_store_false(self):
        client = Mock()
        client.responses.parse.return_value.output_parsed = Extraction(facts=[])
        client.responses.parse.return_value.usage = None
        result = OpenAILLM(Settings(), client).generate("test", "instruction", {}, Extraction)
        self.assertEqual(result.facts, [])
        self.assertFalse(client.responses.parse.call_args.kwargs["store"])
        self.assertIs(client.responses.parse.call_args.kwargs["text_format"], Extraction)

    def test_llm_refusal_stops(self):
        client = Mock()
        client.responses.parse.return_value.output_parsed = None
        with self.assertRaises(ValueError):
            OpenAILLM(Settings(), client).generate("test", "instruction", {}, Extraction)

    def test_unsafe_urls_rejected(self):
        self.assertFalse(canonical_url("file:///private/document"))
        self.assertFalse(canonical_url("https://secret@example.com/p"))
