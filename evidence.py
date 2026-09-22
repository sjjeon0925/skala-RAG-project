"""출처 연결과 인용문 검증. 인용 일치는 의미적 사실 검증을 대신하지 않는다."""

import hashlib
import re

from config import FACT_MAX_TIER, PERSPECTIVES, TECHNICAL_FACT_MAX_TIER
from schemas import Extraction
from workflow_logging import get_logger


def normalized(text):
    return re.sub(r"\s+", " ", text).strip()


def quote_exists(quote, content):
    return len(normalized(quote)) >= 12 and normalized(quote) in normalized(content)


NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*")
UNIT = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*\s*"
    r"(%|×|x\b|배|ms\b|us\b|s\b|[KMGT]i?B(?:/s)?\b|tokens?/s\b)",
    re.IGNORECASE,
)


def numeric_supported(claim, evidence):
    """주장에 쓰인 숫자와 단위가 인용 원문에 실제로 있는지 확인한다."""
    original = " ".join(
        str(e.get(k, ""))
        for e in evidence
        for k in ("quote", "experimental_condition", "year", "published_date")
    )
    if not set(NUMBER.findall(normalized(claim))).issubset(NUMBER.findall(normalized(original))):
        return False
    expected = {m.group(0).replace(" ", "").lower() for m in UNIT.finditer(normalized(original))}
    actual = {m.group(0).replace(" ", "").lower() for m in UNIT.finditer(normalized(claim))}
    return actual.issubset(expected)


def extract_evidence(services, chunks, *, technology, perspective, items):
    if not chunks:
        return {}
    result = services.llm.generate(
        "extract:" + perspective,
        "자료에서 해당 기술의 항목별 근거를 추출한다. item은 items 중 하나만 사용. "
        "quote는 claim을 지지하는 원문 그대로. 숫자 성능/비용 주장이면 numeric=true. "
        "numeric이면 단위·Baseline·GPU·모델·Context Length·요청 수·Batch 중 확인되는 실험 조건 원문을 "
        "experimental_condition에 복사하고 condition_chunk_id에 "
        "그 구절의 청크 ID를 넣는다. 동일 문서의 다른 페이지도 가능. 비수치면 두 필드는 빈 문자열. "
        "자료에서 조건을 못 찾으면 수치 주장을 추출하지 말 것. 웹 Opinion은 Fact로 바꾸지 말 것. "
        "실제 발언이면 speaker와 affiliation을 자료에 적힌 그대로 기록하고, 없으면 빈 문자열로 둔다. "
        "보조 기술 문서를 대상 기술의 직접 성능 근거로 사용하지 말 것.",
        {"technology": technology, "items": list(items), "chunks": chunks},
        Extraction,
    )
    by_id = {x["chunk_id"]: x for x in chunks}
    evidence, rejected = {}, 0
    for fact in result.facts:
        source = by_id.get(fact.chunk_id)
        condition_source = by_id.get(fact.condition_chunk_id)
        if (
            source is None
            or fact.item not in items
            or not fact.claim.strip()
            or not quote_exists(fact.quote, source["content"])
            # 다른 기술의 자료를 대상 기술 근거로 쓰지 않는다.
            or (source.get("role") == "core" and source.get("technology") != technology)
            # 주장에 쓰인 수치·단위가 원문에 없으면 채택하지 않는다.
            or not numeric_supported(fact.claim, [{"quote": fact.quote,
                                                   "experimental_condition": fact.experimental_condition}])
            # 저품질 출처는 Opinion으로만 쓴다. 기술 Fact는 논문·공식 문서만 인정한다.
            # (demo는 가상 URL이라 등급 정책을 적용하지 않는다.)
            or (
                getattr(services, "mode", "live") != "demo"
                and
                fact.kind == "Fact"
                and source.get("role") == "web"
                and source.get("source_tier", 5)
                > (TECHNICAL_FACT_MAX_TIER if perspective in ("technical", "domain", "trl") else FACT_MAX_TIER)
            )
            or (
                (fact.speaker and normalized(fact.speaker).lower() not in normalized(source["content"]).lower())
                or (
                    fact.affiliation
                    and normalized(fact.affiliation).lower() not in normalized(source["content"]).lower()
                )
            )
            or (
                fact.numeric
                and (
                    condition_source is None
                    or condition_source["document_id"] != source["document_id"]
                    or not quote_exists(fact.experimental_condition, condition_source["content"])
                )
            )
        ):
            rejected += 1
            continue
        identifier = (
            fact.chunk_id
            + "-"
            + hashlib.sha256(
                (technology + perspective + fact.item + normalized(fact.quote)).encode()
            ).hexdigest()[:10]
        )
        evidence[identifier] = {
            **{k: v for k, v in source.items() if k not in ("content", "paragraphs", "score")},
            "evidence_id": identifier,
            "technology": technology,
            "perspective": perspective,
            "claim": fact.claim,
            "quote": fact.quote,
            "kind": fact.kind,
            "numeric": fact.numeric,
            "experimental_condition": fact.experimental_condition,
            "condition_source": (
                {
                    "chunk_id": condition_source["chunk_id"],
                    "page": condition_source.get("page"),
                    "source_url": condition_source.get("source_url", ""),
                }
                if fact.numeric and condition_source
                else {}
            ),
            "item": fact.item,
            "speaker": fact.speaker,
            "affiliation": fact.affiliation,
        }
    get_logger().info(
        "EVIDENCE_EXTRACTED | perspective=%s | accepted=%d | rejected=%d",
        perspective,
        len(evidence),
        rejected,
    )
    return evidence


def valid_evidence(item):
    return bool(
        item.get("claim")
        and item.get("quote")
        and item.get("source")
        and item.get("evidence_id")
        and item.get("source_url")
        and (item.get("role") == "web" or (isinstance(item.get("page"), int) and item["page"] > 0))
        and (not item.get("numeric") or item.get("experimental_condition"))
    )


def all_evidence(state, *, include_counter=True):
    combined = dict(state["technical_evidence"])
    for perspective in PERSPECTIVES:
        combined.update(state[f"{perspective}_analysis"].get("evidence", {}))
    if include_counter:
        for entry in state["counter_evidence"].values():
            if entry.get("status") == "found":
                e = entry["evidence"]
                combined[e["evidence_id"]] = e
    return combined


def valid_ids(ids, evidence):
    return bool(ids) and all(i in evidence and valid_evidence(evidence[i]) for i in ids)


def collect_references(evidence):
    refs = {}
    for identifier, item in sorted(evidence.items()):
        key = item.get("source_url") or item["source"]
        ref = refs.setdefault(
            key,
            {
                "source": item["source"],
                "source_url": item.get("source_url", ""),
                "author": item.get("author", ""),
                "year": item.get("year", ""),
                "published_date": item.get("published_date", ""),
                "source_type": item.get("source_type", "paper" if item.get("page") else "web"),
                "venue": item.get("venue", ""),
                "identifier": item.get("identifier", ""),
                "site_name": item.get("site_name", ""),
                "evidence_ids": [],
                "pages": [],
            },
        )
        ref["evidence_ids"].append(identifier)
        if item.get("page") is not None and item["page"] not in ref["pages"]:
            ref["pages"].append(item["page"])
    return list(refs.values())


def fan_in(state):
    """병렬 평가 완료 장벽. references는 보고서가 실제 인용 기준으로만 생성한다."""
    completed = sum(bool(state[f"{perspective}_analysis"]) for perspective in PERSPECTIVES)
    get_logger().info("EVALUATIONS_JOINED | completed=%d", completed)
    return {}
