"""State 본문 대신 단계, 데이터 개수, 처리 시간을 기록한다."""

import logging
from collections.abc import Mapping
from functools import wraps
from pathlib import Path
from time import perf_counter


LOGGER_NAME = "capstone.workflow"


def configure_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(threadName)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handlers = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def get_logger(run_id: str) -> logging.LoggerAdapter:
    class RunLogger(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return f"[run={self.extra['run_id']}] {msg}", kwargs

    return RunLogger(logging.getLogger(LOGGER_NAME), {"run_id": run_id})


def summarize_state(value) -> str:
    """문서·프롬프트·응답 원문은 출력하지 않고 필드별 크기만 표시."""
    if not isinstance(value, Mapping):
        return type(value).__name__
    parts = []
    for key, item in value.items():
        if isinstance(item, (list, dict, tuple, set)):
            detail = f"{len(item)}개"
        elif isinstance(item, str):
            detail = f"{len(item)}자"
        elif key == "max_retries" and isinstance(item, int):
            detail = str(item)
        else:
            detail = type(item).__name__
        parts.append(f"{key}={detail}")
    return ", ".join(parts) or "변경 없음"


def log_node(name, function, logger):
    @wraps(function)
    def wrapped(state, *args, **kwargs):
        started = perf_counter()
        logger.info("NODE_START | %s", name)
        logger.debug("NODE_INPUT | %s | %s", name, summarize_state(state))
        if name == "query_rewrite":
            logger.info(
                "RETRY | 부족 근거=%d개 | 설정된 재검색 한도=%s",
                len(state.get("missing_evidence", [])), state.get("max_retries"),
            )
        elif name == "fan_out":
            logger.info("FAN_OUT | TRL·시장·이해관계자·도메인 평가 시작")
        elif name == "second_check":
            logger.info("FAN_IN | 4개 평가 완료 후 2차 근거 검사 시작")
        try:
            result = function(state, *args, **kwargs)
        except Exception as exc:
            # API 오류에 요청 원문 등이 포함될 수 있어 메시지 대신 유형만 기록.
            logger.error(
                "NODE_FAILED | %s | %.3fs | %s%s", name,
                perf_counter() - started, type(exc).__name__,
                " (미구현 단계)" if isinstance(exc, NotImplementedError) else "",
            )
            raise
        logger.info(
            "NODE_DONE | %s | %.3fs | 업데이트: %s",
            name, perf_counter() - started, summarize_state(result),
        )
        return result

    return wrapped


def log_router(function, logger):
    @wraps(function)
    def wrapped(state, *args, **kwargs):
        logger.info("ROUTE_START | 1차 근거 검사 후 경로 판단")
        try:
            route = function(state, *args, **kwargs)
        except Exception as exc:
            logger.error("ROUTE_FAILED | %s", type(exc).__name__)
            raise
        destinations = {"rewrite": "Query Rewrite → 기술 조사 재검색", "evaluate": "4개 관점 평가"}
        logger.info("ROUTE_SELECTED | %s → %s", route, destinations.get(route, "미정의 경로"))
        return route

    return wrapped
