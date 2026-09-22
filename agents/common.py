"""기술·평가 기준별 검색과 검증. 각 Agent는 자신의 analysis만 쓴다."""

from config import EVALUATION_CRITERIA, QUERY_TERMS, TECH_PROFILES
from evidence import extract_evidence, valid_ids
from schemas import Evaluation
from tools.grounding import statement, verify_statements
from tools.web_search import relevance, self_reported
from workflow_logging import get_logger


def evaluate(state, services, perspective, sources, evidence=None):
    evidence = dict(evidence or {})
    findings, limitations, missing = [], [], []
    for technology in state["technologies"]:
        for criterion in EVALUATION_CRITERIA[perspective]:
            chunks = sources.get(technology, {}).get(criterion, [])
            found = extract_evidence(
                services,
                chunks,
                technology=technology,
                perspective=perspective,
                items=[criterion],
            )
            evidence.update(found)
            available = {
                key: value
                for key, value in evidence.items()
                if value["technology"] == technology
                and (value.get("item") == criterion or value.get("perspective") == "technical")
            }
            if not available:
                missing.append(
                    {"technology": technology, "item": criterion, "reason": "검색되지 않음 또는 검증 탈락"}
                )
                continue
            result = services.llm.generate(
                "evaluate:" + perspective,
                "한 기술과 한 criterion만 평가한다. 근거 있는 finding은 최대 하나만 반환한다. "
                "다른 시스템의 결과나 상위 생태계 자료를 대상 기술의 직접 성능·채택 근거로 바꾸지 않는다. "
                "직접 확인되지 않은 부재를 단정하지 않고 limitation에 정보 부족으로 기록한다. "
                "TRL만 1~9 또는 null: 1 원리 관찰, 2 개념 정립, 3 개념 증명, 4 실험실 부품 검증, "
                "5 관련 환경 부품 검증, 6 관련 환경 시제품 실증, 7 운영 환경 시스템 시제품, "
                "8 실제 시스템 완성·검증, 9 실제 운영 입증. 공식 값이 아니면 공개 정보 기반 추정으로 표시한다. "
                "모든 finding에는 전달받은 evidence_ids만 사용한다.",
                {
                    "perspective": perspective,
                    "technologies": [technology],
                    "domain": state["domain"],
                    "criteria": [criterion],
                    "evidence": available,
                },
                Evaluation,
                judge=perspective == "trl",
            )
            accepted = []
            for finding in result.findings[:1]:
                item = finding.model_dump()
                if (
                    item["technology"] != technology
                    or item["criterion"] != criterion
                    or not item["claim"].strip()
                    or not valid_ids(item["evidence_ids"], available)
                ):
                    continue
                if perspective != "trl":
                    item["trl_level"] = None
                elif item["trl_level"] is not None:
                    item["limitation"] = (
                        "공개 정보 기반 추정 TRL이며 공식 인증값이 아님. " + item["limitation"]
                    )
                    item["kind"] = "Inference"
                accepted.append(item)
            if accepted:
                row = accepted[0]
                verified = verify_statements(
                    services,
                    [
                        statement(
                            "finding",
                            row["claim"],
                            [available[i] for i in row["evidence_ids"]],
                            technology,
                        )
                    ],
                )
                if "finding" in verified:
                    findings.append(row)
                else:
                    missing.append(
                        {"technology": technology, "item": criterion, "reason": "주장-원문 의미 검증 탈락"}
                    )
            else:
                missing.append(
                    {"technology": technology, "item": criterion, "reason": "평가 또는 근거 ID 검증 탈락"}
                )
            limitations.extend(result.limitations)
    used = {identifier for finding in findings for identifier in finding["evidence_ids"]}
    get_logger().info(
        "EVALUATION_READY | perspective=%s | findings=%d | evidence=%d | missing=%d",
        perspective,
        len(findings),
        len(used),
        len(missing),
    )
    return {
        f"{perspective}_analysis": {
            "perspective": perspective,
            "findings": findings,
            "evidence": {identifier: evidence[identifier] for identifier in sorted(used)},
            "limitations": list(dict.fromkeys(limitations)),
            "missing_evidence": missing,
        }
    }


def web_sources(state, services, perspective):
    sources = {}
    for technology in state["technologies"]:
        sources[technology] = {}
        for criterion in EVALUATION_CRITERIA[perspective]:
            rows = []
            # 동명이의 배제를 위해 고유 명칭으로 검색한다. 상위 생태계 근거를 인정하는
            # 시장 관점에서만 약어 질의를 추가한다.
            seeds = list(TECH_PROFILES.get(technology, {}).get("web_queries", ())) or [f'"{technology}"']
            if perspective == "market":
                seeds.append(f'"{technology}" CXL PIM KV cache market adoption')
            for seed in seeds:
                candidates = services.web.search(f"{seed} {QUERY_TERMS[criterion]}")
                for candidate in candidates:
                    scope = (
                        "direct"
                        if services.mode == "demo"
                        else relevance(candidate["source"] + " " + candidate["content"], technology)
                    )
                    if scope == "direct" and self_reported(candidate["source_url"], technology):
                        # 저자 자신의 주장은 제3자 검증과 구분해 표시한다.
                        scope = "self_reported"
                    if scope in ("direct", "self_reported") or (
                        perspective == "market" and scope == "ecosystem"
                    ):
                        rows.append({**candidate, "technology": technology, "scope": scope})
                if rows:
                    break
            sources[technology][criterion] = rows[: services.settings.search_results]
    return sources
