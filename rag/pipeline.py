from pathlib import Path

from config import DOCUMENT_MANIFEST, EMBEDDING_MODEL, INDEX_DIR, MAX_DOCUMENT_PAGES


def load_documents(manifest: Path = DOCUMENT_MANIFEST) -> list:
    """TODO: ITME/CXL-PIM/InfiniGen PDF 로딩 및 총 200페이지 제한 확인."""
    raise NotImplementedError(f"문서 로딩을 구현하세요. 페이지 상한: {MAX_DOCUMENT_PAGES}")


def split_documents(documents: list) -> list:
    """TODO: 페이지·출처를 보존하여 청크 생성. 청크 설정은 설계서에 미지정."""
    raise NotImplementedError("문서 분할을 구현하세요.")


def build_embeddings():
    """TODO: multilingual-e5-base로 오픈소스 임베딩 구성."""
    raise NotImplementedError(f"임베딩을 구현하세요: {EMBEDDING_MODEL}")


def build_index(chunks: list, embeddings, index_dir: Path = INDEX_DIR):
    """TODO: 벡터 저장소 구축. 저장소 종류는 설계서에 미지정."""
    raise NotImplementedError("벡터 저장소를 구현하세요.")


def build_hybrid_retriever(vectorstore, chunks: list):
    """TODO: Dense Retrieval과 BM25를 결합. 가중치와 k는 후속 설정."""
    raise NotImplementedError("Hybrid Retrieval을 구현하세요.")
