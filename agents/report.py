"""보고서 Agent: State 자료로 작성하고 실제 인용된 참고문헌만 렌더링."""

import json
import re

from config import PERSPECTIVES
from evidence import all_evidence, collect_references, valid_ids
from state import technology_names
from workflow_logging import get_logger

SECTIONS = {
    "1.1": "데이터센터 환경의 KV Cache 문제",
    "1.2": "분석 목적 및 범위",
    "2.1": "ITME",
    "2.2": "CXL-PIM",
    "2.3": "기술 선정 및 비교 이유",
    "3.1": "ITME 구조, 실험 조건, 주요 결과와 한계",
    "3.2": "CXL-PIM 구조, 실험 조건, 주요 결과와 한계",
    "3.3": "두 기술의 구조적 차이와 직접 비교 한계",
    "4.1": "기술 성숙도",
    "4.2": "시장성",
    "4.3": "이해관계자",
    "4.4": "데이터센터·클라우드 적용성",
    "5.1": "공통적으로 확인된 사항",
    "5.2": "관점에 따라 평가가 엇갈리는 지점",
    "5.3": "주요 Trade-off",
    "5.4": "종합 의견",
    "6.1": "공개 정보 기반 분석의 한계",
    "6.2": "서로 다른 실험 환경에 따른 직접 비교 한계",
    "6.3": "확증편향 방지 및 근거 검증 방법",
}
CHAPTERS = {
    "1": "분석 배경 및 문제 정의",
    "2": "평가 대상 기술 선정",
    "3": "기술 개요",
    "4": "다관점 평가",
    "5": "관점 간 종합 및 시사점",
    "6": "분석 한계 및 신뢰성 확보",
}


def _reference_text(index, ref):
    author = ref["author"] or "저자·기관 정보 미확인"
    date = str(ref["year"] or ref["published_date"] or "발행일 미확인")
    if ref.get("source_type") == "web":
        site = ref.get("site_name") or "사이트명 미확인"
        return f"{index}. {author} ({date}). {ref['source']}. {site}, {ref['source_url']}"
    publication = ", ".join(x for x in (ref.get("venue"), ref.get("identifier")) if x)
    publication = publication or "학술지·학회명 미확인"
    return f"{index}. {author} ({date}). {ref['source']}. {publication}, {ref['source_url']}"


def _render_report(state, draft, *, mode="live"):
    evidence = all_evidence(state)
    technologies = technology_names(state)
    used = set()

    def cited(paragraph):
        if not paragraph["text"].strip() or not valid_ids(paragraph["evidence_ids"], evidence):
            return ""
        ids = list(dict.fromkeys(paragraph["evidence_ids"]))
        used.update(ids)
        return paragraph["text"].strip() + " ⟦CITE:" + "|".join(ids) + "⟧"

    supplemental = {section_id: [] for section_id in SECTIONS}
    for index, selection in enumerate(state["technologies"], 1):
        supplemental[f"2.{index}"].append(
            f"- {selection['name']} ({selection['category']}): {selection['key_approach']} - "
            f"{selection['selection_reason']}"
        )
    section_by_perspective = {"trl": "4.1", "market": "4.2", "stakeholder": "4.3", "domain": "4.4"}
    for perspective, section_id in section_by_perspective.items():
        analysis = state[f"{perspective}_analysis"]
        for finding in analysis.get("findings", []):
            label = f"[{finding['kind']}] {finding['technology']}: {finding['claim']}"
            if finding.get("trl_level") is not None:
                label += f" (공개 정보 기반 추정 TRL {finding['trl_level']})"
            if perspective == "stakeholder":
                speakers = []
                for eid in finding["evidence_ids"]:
                    item = evidence.get(eid, {})
                    if item.get("speaker") or item.get("affiliation"):
                        speakers.append(
                            " / ".join(x for x in (item.get("speaker"), item.get("affiliation")) if x)
                        )
                if speakers:
                    label += " (발언자·소속: " + ", ".join(dict.fromkeys(speakers)) + ")"
            text = cited({"text": label, "evidence_ids": finding["evidence_ids"]})
            if text:
                supplemental[section_id].append("- " + text)
                if finding.get("limitation"):
                    supplemental[section_id].append("  - 한계: " + finding["limitation"])
        supplemental[section_id].extend(
            "- 평가 한계: " + limitation for limitation in analysis.get("limitations", [])
        )

    for eid, item in state["technical_evidence"].items():
        if not item.get("numeric") or item["technology"] not in technologies:
            continue
        section_id = "3.1" if item["technology"] == technologies[0] else "3.2"
        condition = item.get("experimental_condition") or "실험 조건 미확인"
        text = cited(
            {
                "text": f"수치 결과: {item['claim']} / 실험 조건: {condition}",
                "evidence_ids": [eid],
            }
        )
        if text:
            supplemental[section_id].append("- " + text)

    for counter in state["counter_evidence"].values():
        if counter["status"] == "found":
            counter_eid = counter["evidence"]["evidence_id"]
            text = cited(
                {
                    "text": "반대·제약 근거: " + counter["counter_claim"],
                    "evidence_ids": [counter_eid],
                }
            )
            if text:
                supplemental["6.3"].append("- " + text)
        else:
            supplemental["6.3"].append(
                "- 반대 근거 미확인: " + counter["target_claim"] + " (주장별 Web Search 1회 범위)"
            )

    for conflict in state["conflicts"]:
        description = conflict["description"]
        if conflict.get("conditions"):
            description += " 조건: " + conflict["conditions"]
        description += " 해석: " + conflict["implication"]
        text = cited({"text": description, "evidence_ids": conflict["evidence_ids"]})
        if text:
            supplemental["5.2"].append("- 상충·비교 제한: " + text)

    lines = ["# ITME와 CXL-PIM 데이터센터 적용성 비교 평가", ""]
    if mode != "live":
        lines.extend(["> DEMO / 테스트용 가상 근거입니다. 기술 평가나 제출 보고서로 사용하지 마세요.", ""])
    lines.extend(["## SUMMARY", ""])
    # SUMMARY 길이는 글자 기준 700자 이내; 실제 반 페이지 여부는 편집 단계에서 확인.
    length = 0
    for paragraph in state["synthesis"].get("summary", []):
        if length + len(paragraph["text"]) > 700:
            continue
        text = cited(paragraph)
        if text:
            lines.extend([text, ""])
            length += len(paragraph["text"])
    if not length:
        lines.extend(["확인된 근거만으로 요약 결론을 작성하기에 정보가 부족합니다.", ""])
    content = {}
    for section in draft.get("sections", []):
        if section["section_id"] in SECTIONS:
            content.setdefault(section["section_id"], []).extend(section["paragraphs"])
    for section_id, title in SECTIONS.items():
        if section_id.endswith(".1"):
            chapter = section_id.split(".")[0]
            lines.extend([f"## {chapter}. {CHAPTERS[chapter]}", ""])
        lines.extend([f"### {section_id} {title}", ""])
        paragraphs = [cited(p) for p in content.get(section_id, [])]
        paragraphs = [p for p in paragraphs if p]
        if section_id == "1.2":
            paragraphs.insert(
                0, f"분석 범위는 {state['domain']}에서 ITME와 CXL-PIM의 KV Cache 관리 방식이다."
            )
        elif section_id == "2.3":
            paragraphs.insert(
                0, "비교 기술은 설계서에서 사람이 선정했으며 자동 기술 선정 Agent는 사용하지 않았다."
            )
        elif section_id == "4.1":
            paragraphs.append("TRL은 공개 정보 기반 추정이며 공식 인증값이 아니다.")
        elif section_id == "6.1":
            for gap in state["missing_evidence"]:
                paragraphs.append(
                    f"- 미확인: {gap['technology']} / {gap.get('perspective', 'technical')} / "
                    f"{gap['item']} ({gap['reason']})"
                )
        elif section_id == "6.2":
            paragraphs.append(
                "GPU, 모델, Context Length, Batch, Baseline이 다르거나 확인되지 않은 "
                "수치는 동일 조건의 벤치마크로 해석하지 않는다."
            )
        elif section_id == "6.3":
            found = sum(x["status"] == "found" for x in state["counter_evidence"].values())
            paragraphs.append(
                f"기술 재검색 {state['retry_count']}회, 주요 주장별 반대 근거 검색 "
                f"{len(state['counter_evidence'])}회, 반대 근거 채택 {found}건. "
                "반대 근거 미발견은 원 주장의 참을 입증하지 않는다. "
                "인용문 일치는 자동 확인했으나 주장과 인용의 의미적 일치에는 사람의 검토가 필요하다."
            )
        paragraphs.extend(supplemental[section_id])
        lines.extend(paragraphs or ["검증된 자료로 작성할 내용이 부족합니다."])
        lines.append("")

    refs = collect_references({eid: evidence[eid] for eid in sorted(used)})
    by_eid = {eid: index for index, ref in enumerate(refs, 1) for eid in ref["evidence_ids"]}
    lines.extend(["", "## REFERENCE", ""])
    for index, ref in enumerate(refs, 1):
        lines.append(_reference_text(index, ref))
        lines.append("   - 근거 ID: " + ", ".join(ref["evidence_ids"]))

    def replace_citation(match):
        markers = []
        for eid in match.group(1).split("|"):
            page = evidence[eid].get("page")
            marker = str(by_eid[eid]) + (f", p.{page}" if page is not None else "")
            if marker not in markers:
                markers.append(marker)
        return "[" + "; ".join(markers) + "]"

    report = re.sub(r"⟦CITE:([^⟧]+)⟧", replace_citation, "\n".join(lines) + "\n")
    get_logger().info(
        "REPORT_CITATIONS | cited_evidence=%d | reference_sources=%d",
        len(used),
        sum(any(e in used for e in r["evidence_ids"]) for r in refs),
    )
    return report, refs


def render_report(state, draft, *, mode="live"):
    """기존 호출부와 호환되는 Markdown 렌더러."""
    report, _ = _render_report(state, draft, mode=mode)
    return report


def contents_writer(state, services):
    """수업 Report Agent의 contents_writer에 해당하는 근거 기반 작성 단계."""
    if services.report_writer is None:
        raise ValueError("report_writer 서비스 필요")
    payload = {
        "sections": SECTIONS,
        "technologies": state["technologies"],
        "domain": state["domain"],
        "evidence": all_evidence(state),
        "synthesis": state["synthesis"],
        "analyses": {p: state[f"{p}_analysis"] for p in PERSPECTIVES},
        "conflicts": state["conflicts"],
        "counter_evidence": state["counter_evidence"],
        "missing_evidence": state["missing_evidence"],
    }
    return services.report_writer.invoke(
        {"data": json.dumps(payload, ensure_ascii=False), "payload": payload}
    )


def report_generator(state, draft, *, mode="live"):
    """수업 Report Agent의 최종화 단계: 본문과 실제 인용 출처를 함께 반환한다."""
    report, references = _render_report(state, draft, mode=mode)
    return {"final_report": report, "references": references}


def report_agent(state, services):
    draft = contents_writer(state, services)
    return report_generator(state, draft.model_dump(), mode=services.mode)
