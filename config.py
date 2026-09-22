"""설계서에 명시된 고정 설정. 기술 선정은 Human 기반이다."""

from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
# 셸에 남은 만료된 키가 .env보다 우선하지 않도록 override=True.
load_dotenv(PROJECT_ROOT / ".env", override=True)
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
if os.getenv("HUGGINGFACEHUB_API_TOKEN"):
    os.environ.setdefault("HF_TOKEN", os.environ["HUGGINGFACEHUB_API_TOKEN"])

TECHNOLOGIES = ["ITME", "CXL-PIM"]
DOMAIN = "데이터센터·클라우드"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
CHUNK_SIZE = 400  # e5 tokenizer tokens
CHUNK_OVERLAP = 50
DENSE_TOP_K = 10
BM25_TOP_K = 10
TOP_K = 5  # RRF 후 최종 결과 수: 설계 미지정 항목의 초기값
RRF_K = 60
RESULTS_PER_CRITERION = 5
MAX_WEB_ATTEMPTS = 2  # 최초 검색 + 대체 검색 1회
MAX_DOCUMENT_PAGES = 200
MAX_RETRIES = 2
DOCUMENT_MANIFEST = PROJECT_ROOT / "data" / "documents.json"
INDEX_DIR = PROJECT_ROOT / "data" / "index"
REPORT_TEMPLATE = PROJECT_ROOT / "prompts" / "report_outline.md"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

TECHNICAL_EVIDENCE_ITEMS = (
    "작동 원리", "KV Cache 저장 위치", "Attention 실행 위치",
    "데이터 이동 경로", "실험 환경", "주요 성능 결과", "비교 Baseline",
    "한계점", "출처",
)
MARKET_CRITERIA = ("제품화", "실제 도입", "지원 생태계", "규모·성장성", "도입 장벽")
STAKEHOLDER_CRITERIA = ("기대 효과", "비용 부담", "호환성", "도입 난이도", "운영상 우려")
DOMAIN_CRITERIA = ("용량", "성능", "데이터 이동", "확장성", "비용과 구축 복잡도")
TRL_CRITERIA = ("개발·검증 단계", "PoC·Prototype", "실환경 검증·상용화")
PERSPECTIVE_CRITERIA = {
    "trl": TRL_CRITERIA, "market": MARKET_CRITERIA,
    "stakeholder": STAKEHOLDER_CRITERIA, "domain": DOMAIN_CRITERIA,
}
TECHNOLOGY_REASONS = {
    "ITME": "CXL/NVMe 계층형 메모리 확장을 통한 KV Cache 배치·이동 방식 비교",
    "CXL-PIM": "CXL 확장과 메모리 근접 연산을 통한 데이터 이동 비용 비교",
}
TECHNOLOGY_ALIASES = {
    "ITME": ("ITME", "Inference Tiered Memory Expansion"),
    "CXL-PIM": ("CXL-PIM", "CXL-PNM", "PNM-KV", "PnG-KV", "Scalable Processing-Near-Memory"),
}
QUERY_TERMS = {
    "작동 원리": "architecture operating principle", "KV Cache 저장 위치": "KV cache storage placement",
    "Attention 실행 위치": "attention computation GPU PNM", "데이터 이동 경로": "data movement prefetch DMA",
    "실험 환경": "evaluation setup GPU model context batch size", "주요 성능 결과": "throughput latency results",
    "비교 Baseline": "baseline comparison", "한계점": "limitations overhead", "출처": "paper authors publication",
    "용량": "KV cache capacity HBM savings", "성능": "latency TTFT TPOT throughput workload",
    "데이터 이동": "bandwidth data movement attention execution location", "확장성": "context length concurrent requests scalability",
    "비용과 구축 복잡도": "hardware cost server compatibility software operational complexity",
    "제품화": "product availability commercialization", "실제 도입": "deployment adoption customer",
    "지원 생태계": "CXL PIM ecosystem support", "규모·성장성": "CXL PIM market size growth",
    "도입 장벽": "adoption barriers compatibility", "기대 효과": "benefits opinion",
    "비용 부담": "cost concerns", "호환성": "compatibility interoperability",
    "도입 난이도": "integration deployment challenges", "운영상 우려": "operational concerns",
    "개발·검증 단계": "technology readiness validation", "PoC·Prototype": "proof of concept prototype",
    "실환경 검증·상용화": "production deployment commercial availability",
}
