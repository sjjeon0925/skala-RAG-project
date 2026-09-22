import io
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from app import main
from config import PERSPECTIVES
from demo import DemoLLM, demo_services
from evidence import fan_in
from graph import build_graph
from state import initial_state
from workflow_logging import configure_logging


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        configure_logging("ERROR")

    def run_scenario(self, scenario="normal", max_retries=2):
        services = demo_services(scenario)
        result = build_graph("test", services).invoke(
            initial_state(max_retries=max_retries), {"recursion_limit": 100, "max_concurrency": 4}
        )
        return result, services

    def test_normal_full_run_preserves_16_fields(self):
        state, services = self.run_scenario()
        self.assertEqual(set(state), set(initial_state()))
        self.assertEqual(len(state), 16)
        self.assertFalse(state["missing_evidence"])
        self.assertEqual(state["retry_count"], 0)
        for perspective in PERSPECTIVES:
            technologies = {f["technology"] for f in state[f"{perspective}_analysis"]["findings"]}
            self.assertEqual(technologies, {"ITME", "CXL-PIM"})
        self.assertIn("DEMO / 테스트용", state["final_report"])
        self.assertIn("## REFERENCE", state["final_report"])
        self.assertEqual(len(services.web.calls), 26 + 8)
        self.assertTrue(all(x["search_count"] == 1 for x in state["counter_evidence"].values()))

    def test_retry_success_clears_first_gaps(self):
        state, _ = self.run_scenario("retry_success")
        self.assertEqual(state["retry_count"], 1)
        self.assertEqual(state["missing_evidence"], [])
        self.assertTrue(state["final_report"])
        self.assertTrue(state["search_queries"])
        # 재작성 질의는 대상 기술의 고유 명칭을 유지해 동명이의 문서를 배제해야 한다.
        from rag.queries import distinctive_names

        for query in state["search_queries"]:
            identifiers = [
                name
                for technology in ("ITME", "CXL-PIM")
                for name in [technology, *distinctive_names(technology)]
            ]
            self.assertTrue(
                any(name.lower() in query.lower() for name in identifiers),
                f"기술 식별자가 없는 질의: {query}",
            )

    def test_retry_exhaustion_continues_and_preserves_gaps(self):
        state, _ = self.run_scenario("retry_exhausted")
        self.assertEqual(state["retry_count"], 2)
        gaps = [x for x in state["missing_evidence"] if x["stage"] == 1]
        self.assertEqual(len(gaps), 18)
        self.assertTrue(all(x["status"] == "retry_exhausted" for x in gaps))
        self.assertIn("미확인: ITME", state["final_report"])

    def test_zero_retries(self):
        state, services = self.run_scenario("retry_exhausted", max_retries=0)
        self.assertEqual(state["retry_count"], 0)
        self.assertEqual(services.llm.technical_calls, {"ITME": 3, "CXL-PIM": 3})

    def test_second_gaps_do_not_restart_retrieval(self):
        state, services = self.run_scenario("second_missing")
        self.assertEqual(state["retry_count"], 0)
        self.assertTrue(any(x["stage"] == 2 and x["status"] == "recorded" for x in state["missing_evidence"]))
        self.assertEqual(services.llm.technical_calls["ITME"], 3)
        self.assertTrue(state["final_report"])

    def test_counter_found_is_cited_and_report_writes_references(self):
        state, _ = self.run_scenario("counter_found")
        self.assertTrue(all(x["status"] == "found" for x in state["counter_evidence"].values()))
        self.assertIn("DEMO 가상 제약 사항", state["final_report"])
        self.assertTrue(any(e.startswith("counter-") for r in state["references"] for e in r["evidence_ids"]))

    def test_four_evaluators_really_parallel_and_join_once(self):
        barrier = threading.Barrier(4)

        class ParallelLLM(DemoLLM):
            seen = set()
            lock = threading.Lock()

            def generate(self, task, *args, **kwargs):
                if task.startswith("evaluate:"):
                    with self.lock:
                        first = task not in self.seen
                        self.seen.add(task)
                    if first:
                        barrier.wait(timeout=5)
                return super().generate(task, *args, **kwargs)

        services = demo_services()
        services.llm = ParallelLLM()
        with patch("graph.fan_in", wraps=fan_in) as join:
            state = build_graph("parallel", services).invoke(initial_state(), {"max_concurrency": 4})
        self.assertEqual(join.call_count, 1)
        self.assertTrue(all(join.call_args.args[0][f"{p}_analysis"] for p in PERSPECTIVES))
        self.assertTrue(state["final_report"])

    def test_cli_saves_report_state_and_log(self):
        with tempfile.TemporaryDirectory() as directory, patch("sys.stdout", new_callable=io.StringIO):
            code = main(
                ["--demo", "--scenario", "retry_exhausted", "--output-dir", directory, "--log-level", "INFO"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(len(list(Path(directory).glob("*/report.md"))), 1)
            self.assertEqual(len(list(Path(directory).glob("*/state.json"))), 1)
            logs = next(Path(directory).glob("logs/*.log")).read_text()
            for event in (
                "RUN_START",
                "QUERY_REWRITE",
                "RETRY_EXHAUSTED",
                "FAN_OUT",
                "FAN_IN",
                "COUNTER_RESULT",
                "REPORT_SAVED",
                "RUN_DONE",
            ):
                self.assertIn(event, logs)
        configure_logging("ERROR")

    def test_no_credentials_does_not_silently_use_demo(self):
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "", "TAVILY_API_KEY": ""}),
            tempfile.TemporaryDirectory() as directory,
        ):
            self.assertEqual(main(["--run", "--output-dir", directory]), 1)
            self.assertEqual(list(Path(directory).glob("*/report.md")), [])
        configure_logging("ERROR")

    def test_show_graph_does_not_need_providers(self):
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(main(["--show-graph"]), 0)
        for name in ("fan_in", "retry_limit", "record_first_missing", "record_second_missing"):
            self.assertIn(name, output.getvalue())


if __name__ == "__main__":
    unittest.main()
