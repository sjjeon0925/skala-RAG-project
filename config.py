"""설계서에 명시된 고정 설정. 기술 선정은 Human 기반이다."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

TECHNOLOGIES = ["ITME", "CXL-PIM"]
DOMAIN = "데이터센터·클라우드"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
EMBEDDING_REVISION = "d128750597153bb5987e10b1c3493a34e5a4502a"
MAX_DOCUMENT_PAGES = 200
MAX_RETRIES = 2
DOCUMENT_MANIFEST = PROJECT_ROOT / "data" / "documents.json"
INDEX_DIR = PROJECT_ROOT / "data" / "index"
REPORT_TEMPLATE = PROJECT_ROOT / "prompts" / "report_outline.md"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

TECHNICAL_EVIDENCE_ITEMS = (
    "작동 원리",
    "KV Cache 저장 위치",
    "Attention 실행 위치",
    "데이터 이동 경로",
    "실험 환경",
    "주요 성능 결과",
    "비교 Baseline",
    "한계점",
    "출처",
)
DOMAIN_CRITERIA = (
    "용량",
    "성능",
    "데이터 이동",
    "확장성",
    "비용과 구축 복잡도",
)

PERSPECTIVES = ("trl", "market", "stakeholder", "domain")
EVALUATION_CRITERIA = {
    "trl": ("검증 단계", "실환경 검증", "제품화 근거"),
    "market": ("제품화", "실제 도입", "지원 생태계", "시장 규모·성장성", "도입 장벽"),
    "stakeholder": ("기대 효과", "비용 부담", "호환성", "도입 난이도", "운영상 우려"),
    "domain": DOMAIN_CRITERIA,
}
QUERY_TERMS = {
    "검증 단계": "paper proof of concept prototype validation",
    "실환경 검증": "production deployment operational validation",
    "제품화 근거": "commercial product roadmap availability",
    "제품화": "commercial product availability",
    "실제 도입": "deployment customer adoption",
    "지원 생태계": "software ecosystem CXL PIM support",
    "시장 규모·성장성": "market size growth forecast CXL PIM",
    "도입 장벽": "adoption barrier cost integration",
    "기대 효과": "developer operator expected benefit statement",
    "비용 부담": "hardware software cost concern statement",
    "호환성": "compatibility integration concern statement",
    "도입 난이도": "deployment migration difficulty statement",
    "운영상 우려": "operations reliability concern statement",
    "용량": "KV cache capacity HBM reduction",
    "성능": "latency TTFT TPOT throughput requests baseline",
    "데이터 이동": "bandwidth data movement attention location",
    "확장성": "context length concurrent requests scalability",
    "비용과 구축 복잡도": "hardware compatibility software operations complexity cost",
}


# 동명이의(同名異義) 방지: 대상 기술을 고유하게 지칭하는 명칭과 도메인 단서.
# "ITME"는 섬유기계 단체·전시회·채용 플랫폼·해양생태 연구소와 이름이 겹치고,
# "CXL-PIM"은 조별 내부 호칭이라 일반 CXL/PIM 아키텍처 문서와 구분되지 않는다.
TECH_PROFILES = {
    "ITME": {
        "paper_ids": ("2606.12556",),
        "distinctive": (
            "Inference Tiered Memory Expansion",
            "Disaggregated CXL-Hybrid",
        ),
        "ambiguous": ("ITME",),
        "web_queries": (
            '"Inference Tiered Memory Expansion" CXL KV cache',
            '"Inference Tiered Memory Expansion" LLM inference memory',
        ),
    },
    "CXL-PIM": {
        "paper_ids": ("2511.00321",),
        "distinctive": (
            "Scalable Processing-Near-Memory",
            "PNM-KV",
            "PnG-KV",
            "1M-Token LLM Inference",
        ),
        "ambiguous": ("CXL-PIM", "CXL PNM", "CXL-PNM"),
        "web_queries": (
            '"Scalable Processing-Near-Memory" "1M-Token" KV cache',
            '"CXL-Enabled KV-Cache Management Beyond GPU Limits"',
        ),
    },
}

# 대상 기술과 무관한 동명 조직·행사·서비스를 걸러낸다.
NEGATIVE_KEYWORDS = (
    "textile", "섬유", "방직", "garment", "weaving", "loom", "apparel",
    "exhibition", "전시회", "trade fair", "expo",
    "society", "association", "산업 단체",
    "recruit", "채용", "hiring", "job board",
    "marine", "해양", "ecology", "생태", "tropical",
    "tourism", "travel", "hotel", "restaurant",
)

# 대상 기술이 속한 기술 도메인 단서. 모호한 약어만 나오면 이 단서를 함께 요구한다.
DOMAIN_TERMS = (
    "kv cache", "kv-cache", "llm", "inference", "gpu", "hbm", "memory expansion",
    "cxl", "pim", "pnm", "processing-near-memory", "processing in memory",
    "nvme", "dram", "attention", "token", "throughput", "bandwidth", "datacenter",
    "메모리", "추론", "캐시", "대역폭",
)

# 기본 신뢰 도메인. .env의 WEB_ALLOWED_DOMAINS로 덮어쓸 수 있다.
DEFAULT_ALLOWED_DOMAINS = (
    "arxiv.org", "acm.org", "ieee.org", "usenix.org", "computeexpresslink.org",
    "semiconductor.samsung.com", "skhynix.com", "micron.com", "intel.com",
    "nvidia.com", "openreview.net", "sigarch.org", "hotchips.org",
)


@dataclass(frozen=True)
class Settings:
    """설계서 미지정 파라미터는 교체 가능하며 최적값으로 간주하지 않는다."""

    model: str = "gpt-4.1-mini"
    judge_model: str = "gpt-4.1-mini"
    embedding_model: str = EMBEDDING_MODEL
    embedding_revision: str | None = EMBEDDING_REVISION
    chunk_tokens: int = 400
    overlap_tokens: int = 50
    dense_top_k: int = 10
    bm25_top_k: int = 10
    embedding_device: str = "cpu"
    embedding_threads: int = 1
    web_allowed_domains: tuple[str, ...] = ()
    top_k: int = 5
    max_context_chunks: int = 30
    search_results: int = 5
    max_claims_per_perspective: int = 2
    request_timeout: float = 60.0
    manifest: Path = DOCUMENT_MANIFEST
    index_dir: Path = INDEX_DIR
    model_cache_dir: Path = PROJECT_ROOT / ".cache" / "models"

    def __post_init__(self):
        if not 0 <= self.overlap_tokens < self.chunk_tokens <= 500:
            raise ValueError("0 <= overlap_tokens < chunk_tokens <= 500 필요")
        if (
            min(
                self.top_k,
                self.dense_top_k,
                self.bm25_top_k,
                self.embedding_threads,
                self.max_context_chunks,
                self.search_results,
                self.max_claims_per_perspective,
            )
            < 1
            or self.request_timeout <= 0
        ):
            raise ValueError("검색/문맥/주장 개수 및 timeout은 양수여야 함")

    @classmethod
    def from_env(cls):
        model = os.getenv("GENERATOR_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
        embedding_model = os.getenv("EMBEDDING_MODEL") or EMBEDDING_MODEL
        return cls(
            model=model,
            judge_model=os.getenv("JUDGE_MODEL") or model,
            embedding_model=embedding_model,
            embedding_revision=os.getenv("EMBEDDING_REVISION")
            or (EMBEDDING_REVISION if embedding_model == EMBEDDING_MODEL else None),
            chunk_tokens=int(os.getenv("CHUNK_TOKENS", "400")),
            overlap_tokens=int(os.getenv("CHUNK_OVERLAP", "50")),
            dense_top_k=int(os.getenv("DENSE_TOP_K", "10")),
            bm25_top_k=int(os.getenv("BM25_TOP_K", "10")),
            embedding_device=os.getenv("EMBEDDING_DEVICE", "cpu"),
            embedding_threads=int(os.getenv("EMBEDDING_THREADS", "1")),
            web_allowed_domains=tuple(
                x.strip() for x in os.getenv("WEB_ALLOWED_DOMAINS", "").split(",") if x.strip()
            )
            or DEFAULT_ALLOWED_DOMAINS,
            top_k=int(os.getenv("TOP_K", "5")),
            max_context_chunks=int(os.getenv("MAX_CONTEXT_CHUNKS", "30")),
            search_results=int(os.getenv("SEARCH_RESULTS", "5")),
            max_claims_per_perspective=int(os.getenv("COUNTER_CLAIMS_PER_PERSPECTIVE", "2")),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", "60")),
        )
