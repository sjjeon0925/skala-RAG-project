"""문자열 검증을 통과한 주장에 대한 독립적인 의미 검증."""

from schemas import Grounding
from workflow_logging import get_logger


def verify_statements(services, statements):
    if services.mode == "demo":
        return {x["statement_id"] for x in statements}
    accepted = set()
    for offset in range(0, len(statements), 12):
        batch = statements[offset:offset + 12]
        response = services.llm.generate(
            "grounding",
            "독립 검증자. 각 claim이 제공된 인용문과 메타데이터에 의해 뒷받침되는지 판단한다. "
            "근거에 없는 사실·인과·수치·조건·발언자를 추가하면 supported=false. "
            "ITME와 대상 CXL-PIM(PNM-KV/PnG-KV)은 다른 시스템이다. 일반 CXL/PIM 시장 자료는 "
            "대상 기술의 실제 채택이나 제품화 근거가 아니다. CENT, InfiniGen, Mooncake, CacheGen, "
            "PagedAttention의 성능을 대상 기술에 귀속하면 false. ecosystem/comparison 근거는 "
            "주장에도 그 범위와 별도 시스템이 명시되어야 한다. 미확인을 부재라는 단정으로 바꾸면 false. "
            "TRL은 명시적인 추정만 허용하고 상용 부품만으로 전체 기술의 상용화를 인정하지 않는다. "
            "실험 조건/단위/Baseline/발언 주체가 인용과 달라도 false. statement_id별로 한 번 판정한다.",
            {"statements": batch}, Grounding, judge=True,
        )
        # 중복/누락/모순 판정은 채택하지 않는다.
        for row in batch:
            votes = [v for v in response.verdicts if v.statement_id == row["statement_id"]]
            if len(votes) == 1 and votes[0].supported:
                accepted.add(row["statement_id"])
    get_logger().info("GROUNDING_CHECK | candidates=%d | accepted=%d", len(statements), len(accepted))
    return accepted


def statement(identifier, claim, evidence, technology=None):
    return {
        "statement_id": identifier, "claim": claim, "technology": technology,
        "evidence": [
            {k: e.get(k, "") for k in (
                "technology", "scope", "quote", "experimental_condition", "source", "source_url",
                "author", "year", "speaker", "organization", "published_date",
            )} for e in evidence
        ],
    }
