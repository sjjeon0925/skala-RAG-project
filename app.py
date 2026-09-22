"""Graph 실행과 검증된 보고서·State 저장."""

import argparse
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from state import initial_state
from workflow_logging import configure_logging, get_logger, summarize_state


def main() -> int:
    parser = argparse.ArgumentParser(description="ITME / CXL-PIM 다관점 비교 평가")
    parser.add_argument("--show-state", action="store_true", help="초기 State 출력")
    parser.add_argument("--show-graph", action="store_true", help="Graph Mermaid 출력")
    parser.add_argument("--run", action="store_true", help="전체 실행 (OpenAI·Tavily API 및 로컬 e5 사용)")
    parser.add_argument("--output", type=Path, help="검증 통과 후 저장할 Markdown 경로")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    parser.add_argument("--log-file", type=Path, help="로그를 추가로 저장할 파일 경로")
    args = parser.parse_args()
    run_id = uuid4().hex[:8]
    configure_logging(args.log_level, args.log_file)
    logger = get_logger(run_id)

    if args.show_state:
        print(json.dumps(initial_state(), ensure_ascii=False, indent=2))
    if args.show_graph or args.run:
        from graph import build_graph

        graph = build_graph(run_id)
        if args.show_graph:
            print(graph.get_graph().draw_mermaid())
        if args.run:
            state = initial_state()
            started = perf_counter()
            logger.info("RUN_START | 기술=%s | 도메인=%s | 재검색 한도=%s", state["technologies"], state["domain"], state["max_retries"])
            logger.info("STATE_READY | %s", summarize_state(state))
            try:
                from config import OUTPUT_DIR
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                checkpoint = OUTPUT_DIR / f"state-{run_id}.json"
                # Keep the last completed superstep for diagnosing provider failures.
                # Checkpoints are local, ignored by Git, and contain no credentials.
                for result in graph.stream(state, stream_mode="values"):
                    checkpoint.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as exc:
                logger.error("RUN_FAILED | %.3fs | %s", perf_counter() - started, type(exc).__name__)
                return 1
            from config import OUTPUT_DIR
            destination = args.output or OUTPUT_DIR / f"report-{run_id}.md"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(result["final_report"], encoding="utf-8")
            destination.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("RUN_DONE | %.3fs | 최종 보고서=%d자 | %s", perf_counter() - started, len(result["final_report"]), destination)
            print(result["final_report"])
    if not any((args.show_state, args.show_graph, args.run)):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
