"""설계서에 명시된 고정 설정. 기술 선정은 Human 기반이다."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
TECHNOLOGIES = ["ITME", "CXL-PIM"]
DOMAIN = "데이터센터·클라우드"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
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
DOMAIN_CRITERIA = (
    "Capacity", "HBM 절감 효과", "Latency (TTFT/TPOT)", "Throughput",
    "Bandwidth / Data Movement", "Attention 실행 위치", "Scalability",
    "Infrastructure Cost / Complexity",
)
