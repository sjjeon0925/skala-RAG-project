"""초기 검색/재작성 전략. 같은 State에서 항상 동일한 질의를 재현한다."""

TECHNICAL_TERMS = {
    "작동 원리": "architecture mechanism design",
    "KV Cache 저장 위치": "KV cache placement memory tier",
    "Attention 실행 위치": "attention computation GPU PIM PNM",
    "데이터 이동 경로": "data transfer DMA RDMA PCIe bandwidth",
    "실험 환경": "evaluation experimental setup GPU model context length batch",
    "주요 성능 결과": "evaluation throughput latency TTFT TPOT speedup",
    "비교 Baseline": "baseline comparison evaluation",
    "한계점": "limitations overhead bottleneck scalability",
    "출처": "paper authors abstract",
}


def rewrite_query(technology, item, retry_count):
    terms = TECHNICAL_TERMS.get(item, item)
    if retry_count == 0:
        return f"{technology} {item} {terms}"
    if retry_count == 1:
        return f"{technology} {terms} implementation evaluation section evidence"
    return f"{technology} {terms} measured result configuration constraint discussion"
