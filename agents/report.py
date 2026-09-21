"""보고서 Agent: State 자료로 작성하고 실제 인용된 참고문헌만 렌더링."""

from config import PERSPECTIVES
from evidence import all_evidence, collect_references, valid_ids
from schemas import ReportDraft
from workflow_logging import get_logger

SECTIONS = {
    "1.1": "데이터센터 환경의 KV Cache 문제",
    "1.2": "분석 목적 및 범위",
    "2.1": "ITME",
    "2.2": "CXL-PIM",
    "2.3": "기술 선정 및 비교 이유",
    "3.1": "ITME 핵심 구조와 특성",
    "3.2": "CXL-PIM 핵심 구조와 특성",
    "3.3": "두 기술의 구조적 차이",
    "4.1": "기술 성숙도",
    "4.2": "시장성",
    "4.3": "이해관계자",
    "4.4": "데이터센터 클라우드 적용성",
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


def render_report(state, draft, *, mode="live"):
    evidence = all_evidence(state)
    refs = collect_references(evidence)
    by_eid = {eid: index for index, ref in enumerate(refs, 1) for eid in ref["evidence_ids"]}
    used = set()

    def cited(paragraph):
        if not paragraph["text"].strip() or not valid_ids(paragraph["evidence_ids"], evidence):
            return ""
        used.update(paragraph["evidence_ids"])
        markers = []
        for eid in dict.fromkeys(paragraph["evidence_ids"]):
            page = evidence[eid].get("page")
            markers.append(str(by_eid[eid]) + (f", p.{page}" if page is not None else ""))
        return paragraph["text"].strip() + " [" + "; ".join(dict.fromkeys(markers)) + "]"

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
        lines.extend(paragraphs or ["검증된 자료로 작성할 내용이 부족합니다."])
        lines.append("")
    # Fact/Opinion, TRL, 실험 조건, 반대 근거와 conflicts는 생성 모델이 누락해도 보존한다.
    lines.extend(["## 근거 검증 부록", ""])
    for perspective in PERSPECTIVES:
        analysis = state[f"{perspective}_analysis"]
        for finding in analysis.get("findings", []):
            label = f"[{perspective} / {finding['kind']}] {finding['technology']}: {finding['claim']}"
            if finding.get("trl_level") is not None:
                label += f" (추정 TRL {finding['trl_level']})"
            text = cited({"text": label, "evidence_ids": finding["evidence_ids"]})
            if text:
                lines.extend(["- " + text, "  - 한계: " + (finding["limitation"] or "추가 검토 필요")])
        for limitation in analysis.get("limitations", []):
            lines.append("- 평가 한계: " + limitation)
    for counter in state["counter_evidence"].values():
        lines.append("- 검증 대상: " + counter["target_claim"])
        if counter["status"] == "found":
            lines.append(
                "  - 반대/제약 근거: "
                + cited(
                    {"text": counter["counter_claim"], "evidence_ids": [counter["evidence"]["evidence_id"]]}
                )
            )
        else:
            lines.append("  - 공개된 반대 근거를 확인하지 못함 (검색 1회 범위).")
    for conflict in state["conflicts"]:
        text = cited(
            {
                "text": conflict["description"] + " " + conflict["implication"],
                "evidence_ids": conflict["evidence_ids"],
            }
        )
        if text:
            lines.append("- 상충/비교 제한: " + text)
    for eid in sorted(used):
        item = evidence[eid]
        if item.get("numeric"):
            condition = item.get("condition_source", {})
            location = f" (조건 출처 p.{condition['page']})" if condition.get("page") else ""
            lines.append(f"- 수치 근거 {eid}: 실험 조건 — {item['experimental_condition']}{location}")
    lines.extend(["", "## REFERENCE", ""])
    for index, ref in enumerate(refs, 1):
        ids = [eid for eid in ref["evidence_ids"] if eid in used]
        if not ids:
            continue
        author = ref["author"] or "저자 정보 미확인"
        date = str(ref["year"] or ref["published_date"] or "발행일 미확인")
        lines.append(f"{index}. {author} ({date}). {ref['source']}. {ref['source_url']}")
        lines.append("   - 근거 ID: " + ", ".join(ids))
    get_logger().info(
        "REPORT_CITATIONS | cited_evidence=%d | reference_sources=%d",
        len(used),
        sum(any(e in used for e in r["evidence_ids"]) for r in refs),
    )
    return "\n".join(lines) + "\n"


def report_agent(state, services):
    draft = services.llm.generate(
        "report",
        "State의 조사/평가/종합 결과를 제공한 목차의 section_id에 맞춰 전달하는 보고서 작성. "
        "새로운 사실이나 평가를 추가하지 말 것. paragraphs는 text 및 evidence_ids. "
        "자료가 없는 문단은 생략. Fact/Opinion/Inference 구분과 한계를 유지. "
        "SUMMARY는 synthesis.summary를 그대로 요약한다. 참고문헌 목록/URL은 생성하지 말 것.",
        {
            "sections": SECTIONS,
            "technologies": state["technologies"],
            "domain": state["domain"],
            "evidence": all_evidence(state),
            "synthesis": state["synthesis"],
            "analyses": {p: state[f"{p}_analysis"] for p in PERSPECTIVES},
            "conflicts": state["conflicts"],
            "counter_evidence": state["counter_evidence"],
            "missing_evidence": state["missing_evidence"],
            "references": state["references"],
        },
        ReportDraft,
    )
    return {"final_report": render_report(state, draft.model_dump(), mode=services.mode)}
