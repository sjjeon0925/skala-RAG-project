"""종합 Agent: State만 사용, 새로운 검색/평가 지표를 생성하지 않는다."""

from config import PERSPECTIVES
from evidence import all_evidence, valid_ids
from schemas import Synthesis
from tools.grounding import statement, verify_statements


def synthesis_agent(state, services):
    evidence = all_evidence(state)
    result = services.llm.generate(
        "synthesis",
        "State의 평가/반대근거/상충/부족근거를 종합해 summary, commonalities, differences, tradeoffs, "
        "conclusion을 작성. 모든 항목에 evidence_ids를 달 것. 새로운 평가나 검색은 하지 않는다. "
        "부족한 근거가 있으면 결론의 확실성을 낮춘다. 반대 근거 not_found는 원 주장 확인을 뜻하지 않는다. "
        "특정 기술을 추천하거나 승자를 정하지 않는다. summary는 한국어 500자 내외.",
        {
            "analyses": {p: state[f"{p}_analysis"] for p in PERSPECTIVES},
            "counter_evidence": state["counter_evidence"],
            "conflicts": state["conflicts"],
            "missing_evidence": state["missing_evidence"],
        },
        Synthesis,
    ).model_dump()
    for key in ("summary", "commonalities", "differences", "tradeoffs", "conclusion"):
        result[key] = [x for x in result[key] if x["text"].strip() and valid_ids(x["evidence_ids"], evidence)]
        if result[key]:
            accepted = verify_statements(
                services,
                [
                    statement(str(index), row["text"], [evidence[i] for i in row["evidence_ids"]])
                    for index, row in enumerate(result[key])
                ],
            )
            result[key] = [row for index, row in enumerate(result[key]) if str(index) in accepted]
    reflected = {identifier for rows in result.values() if isinstance(rows, list) for row in rows
                 if isinstance(row, dict) for identifier in row.get("evidence_ids", [])}
    for counter in state["counter_evidence"].values():
        if counter.get("status") != "found":
            continue
        identifier = counter["evidence"]["evidence_id"]
        if identifier not in reflected:
            result["tradeoffs"].append(
                {"text": counter["counter_claim"], "evidence_ids": [identifier]}
            )
    result["missing_evidence"] = state["missing_evidence"]
    return {"synthesis": result}
