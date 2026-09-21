"""4개 관점 평가의 공통 검증. 역할/자료 선택은 각 Agent에서 정한다."""

from config import EVALUATION_CRITERIA
from evidence import extract_evidence, valid_ids
from schemas import Evaluation
from workflow_logging import get_logger


def evaluate(state, services, perspective, sources, evidence=None):
    evidence = dict(evidence or {})
    for technology, chunks in sources.items():
        evidence.update(
            extract_evidence(
                services,
                chunks,
                technology=technology,
                perspective=perspective,
                items=EVALUATION_CRITERIA[perspective],
            )
        )
    result = services.llm.generate(
        "evaluate:" + perspective,
        "지정 관점 및 criteria별로 기술을 평가하되 근거 있는 항목만 findings로 반환. "
        "기술별 모든 criteria를 검토하고 미확인 사항은 limitations에 기록. "
        "criterion은 criteria 중 하나. 다른 기술의 근거 ID를 사용할 때 직접 성능 근거로 오인 금지. "
        "TRL 관점에서만 trl_level을 1~9 또는 null로 기입. 검증 근거가 없으면 null. "
        "TRL 1 기초원리, 2 개념, 3 개념증명, 4 실험실 검증, 5 관련환경 검증, "
        "6 관련환경 시제품, 7 운영환경 시제품, 8 시스템 완성/검증, 9 실제 운영 입증. "
        "TRL 값은 공개 정보 기반 추정이라고 limitation에 명시. "
        "기술 문서의 주장을 외부 검증으로 간주하지 말 것. 모든 finding에는 evidence_ids 필요.",
        {
            "perspective": perspective,
            "technologies": state["technologies"],
            "domain": state["domain"],
            "criteria": list(EVALUATION_CRITERIA[perspective]),
            "evidence": evidence,
        },
        Evaluation,
        judge=perspective == "trl",
    )
    findings, limitations = [], list(result.limitations)
    for finding in result.findings:
        item = finding.model_dump()
        if (
            item["technology"] not in state["technologies"]
            or item["criterion"] not in EVALUATION_CRITERIA[perspective]
            or not item["claim"].strip()
            or not valid_ids(item["evidence_ids"], evidence)
            or not any(evidence[i]["technology"] == item["technology"] for i in item["evidence_ids"])
        ):
            limitations.append("근거 ID 또는 평가 항목 검증 실패로 일부 주장을 제외함.")
            continue
        if perspective != "trl":
            item["trl_level"] = None
        elif item["trl_level"] is not None:
            item["limitation"] = "공개 정보 기반 추정 TRL이며 공식 인증값이 아님. " + item["limitation"]
            item["kind"] = "Inference"
        findings.append(item)
    used = {i for finding in findings for i in finding["evidence_ids"]}
    get_logger().info(
        "EVALUATION_READY | perspective=%s | findings=%d | evidence=%d", perspective, len(findings), len(used)
    )
    return {
        f"{perspective}_analysis": {
            "perspective": perspective,
            "findings": findings,
            "evidence": {i: evidence[i] for i in sorted(used)},
            "limitations": list(dict.fromkeys(limitations)),
        }
    }


def web_sources(state, services, suffix):
    return {tech: services.web.search(f'"{tech}" KV cache {suffix}') for tech in state["technologies"]}
