"""출처 연결과 인용문 검증. 인용 일치는 의미적 사실 검증을 대신하지 않는다."""

import hashlib
import re
import unicodedata
from collections import Counter

from config import PERSPECTIVES
from schemas import Extraction
from workflow_logging import get_logger, log_operation


def normalized(text):
    text = unicodedata.normalize("NFKC", str(text)).replace("\u00ad", "")
    text = text.replace("−", "-").replace("–", "-")
    text = re.sub(r"(?<=[a-z])-\s*\n\s*(?=[a-z])", "", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_exists(quote, content):
    return len(normalized(quote)) >= 12 and normalized(quote) in normalized(content)


NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w.])")
UNIT = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*\s*"
    r"(%|×|x\b|배|ms\b|us\b|s\b|[KMGT]i?B(?:/s)?\b|tokens?/s\b)",
    re.I,
)


def numeric_supported(claim, evidence):
    """수치/단위는 원문에서만 허용. 모델명 LPDDR5X 등은 성능 배수로 보지 않는다."""
    original = " ".join(
        str(e.get(k, ""))
        for e in evidence
        for k in ("quote", "experimental_condition", "year", "published_date")
    )
    if not set(NUMBER.findall(normalized(claim))).issubset(NUMBER.findall(normalized(original))):
        return False
    expected = {(m.group(0).replace(" ", "").lower()) for m in UNIT.finditer(normalized(original))}
    actual = {(m.group(0).replace(" ", "").lower()) for m in UNIT.finditer(normalized(claim))}
    return actual.issubset(expected)


def extract_evidence(services, chunks, *, technology, perspective, items, retry_count=0):
    from tools.grounding import statement, verify_statements

    if not chunks:
        return {}
    by_id = {x["chunk_id"]: x for x in chunks}
    evidence, rejected = {}, Counter()
    items = list(dict.fromkeys(items))
    for offset in range(0, len(items), 3):
        batch = items[offset:offset + 3]
        payload = {
            "technology": technology,
            "items": batch,
            "chunks": chunks,
            "retry_count": retry_count,
        }
        for _attempt in range(2):
            result = services.llm.generate(
                "extract:" + perspective,
                "대상 기술의 items별 근거를 최대 2개 추출. item은 전달된 항목 중 하나. "
                "quote는 claim을 뒷받침하는 원문 그대로. 수치 성능/비용 주장에는 numeric=true와 "
                "단위·Baseline·GPU·모델·context·batch 등 확인된 실험 조건 원문을 experimental_condition에 "
                "넣고 condition_chunk_id를 지정. 동일 문서의 다른 페이지도 가능. 조건이 없으면 수치 주장 생략. "
                "비수치는 조건 필드를 비운다. ecosystem 자료는 그 범위를 claim에 표시하고 직접 도입으로 바꾸지 말 것. "
                "보조 기술의 성능은 해당 기술 이름으로만 기술. 웹 Opinion의 발언자 speaker, 소속 organization, "
                "발행일 published_date는 원문에 있을 때만 그대로 기입. 확인 불가능하면 빈 문자열.",
                payload, Extraction,
            )
            failures = Counter()
            for fact in result.facts:
                source = by_id.get(fact.chunk_id)
                condition = by_id.get(fact.condition_chunk_id)
                reason = None
                if source is None or not fact.claim.strip() or not quote_exists(fact.quote, source["content"]):
                    reason = "citation_mismatch"
                elif fact.item not in batch:
                    reason = "invalid_item"
                elif source.get("role") == "core" and source.get("technology") != technology:
                    reason = "technology_mismatch"
                elif fact.numeric and (
                    condition is None
                    or condition["document_id"] != source["document_id"]
                    or not quote_exists(fact.experimental_condition, condition["content"])
                ):
                    reason = "missing_numeric_conditions"
                elif UNIT.search(fact.claim) and not fact.numeric:
                    reason = "missing_numeric_conditions"
                elif not numeric_supported(
                    fact.claim,
                    [
                        {
                            **source,
                            "quote": fact.quote,
                            "experimental_condition": fact.experimental_condition,
                        }
                    ],
                ):
                    reason = "numeric_mismatch"
                if reason:
                    failures[reason] += 1
                    continue
                identifier = fact.chunk_id + "-" + hashlib.sha256(
                    (technology + perspective + fact.item + normalized(fact.quote) + normalized(fact.claim)).encode()
                ).hexdigest()[:10]
                # 교정 응답이 이미 승인한 항목을 중복 확장하지 않게 한다.
                if identifier not in evidence and sum(e["item"] == fact.item for e in evidence.values()) >= 2:
                    continue
                metadata = {k: v for k, v in source.items()
                            if k not in ("content", "paragraphs", "score", "parent_content", "embedding_content")}
                evidence[identifier] = {
                    **metadata, "evidence_id": identifier, "technology": technology,
                    "perspective": perspective, "claim": fact.claim, "quote": fact.quote,
                    "kind": fact.kind, "numeric": fact.numeric,
                    "experimental_condition": fact.experimental_condition if fact.numeric else "",
                    "condition_source": ({"chunk_id": condition["chunk_id"], "page": condition.get("page"),
                                          "source_url": condition.get("source_url", "")}
                                         if fact.numeric and condition else {}),
                    "item": fact.item,
                    "scope": source.get("scope", "comparison" if source.get("role") == "supporting" else "direct"),
                }
                for key in ("speaker", "organization", "published_date"):
                    value = getattr(fact, key)
                    evidence[identifier][key] = (value if value and normalized(value) in normalized(
                        source["content"] + " " + source.get("published_date", "")) else source.get(key, ""))
            rejected.update(failures)
            if not failures:
                break
            payload = {**payload, "correction": dict(failures)}
    accepted = verify_statements(services, [statement(i, e["claim"], [e], technology) for i, e in evidence.items()])
    rejected["semantic_mismatch"] += len(evidence) - len(accepted)
    get_logger().info("EVIDENCE_EXTRACTED | perspective=%s | accepted=%d | rejected=%s",
                      perspective, len(accepted), dict(rejected))
    return {i: e for i, e in evidence.items() if i in accepted}


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
                "venue": item.get("venue", ""),
                "arxiv_id": item.get("arxiv_id", ""),
                "site_name": item.get("site_name", ""),
                "evidence_ids": [],
                "pages": [],
            },
        )
        ref["evidence_ids"].append(identifier)
        if item.get("page") is not None and item["page"] not in ref["pages"]:
            ref["pages"].append(item["page"])
    return list(refs.values())


@log_operation("FAN_IN_JOIN")
def fan_in(state):
    # Graph의 barrier가 네 관점의 완료를 보장한다. references는 report만 쓴다.
    return {}
