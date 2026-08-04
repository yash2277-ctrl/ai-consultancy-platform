"""
Lightweight file-based vector store — stores document chunks as JSON with
BM25-style keyword retrieval.  No external vector DB dependency.

Each project gets its own JSON file under CHROMA_PERSIST_DIR (reusing the
config key for directory path).
"""

import json
import logging
import math
import os
import re
from collections import Counter
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.rag.embeddings import parse_file

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

_STORE_DIR = settings.CHROMA_PERSIST_DIR
os.makedirs(_STORE_DIR, exist_ok=True)


def _project_path(project_id: str) -> str:
    safe = project_id.replace("-", "_")
    return os.path.join(_STORE_DIR, f"proj_{safe}.json")


def _load_store(project_id: str) -> List[Dict[str, Any]]:
    path = _project_path(project_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_store(project_id: str, chunks: List[Dict[str, Any]]) -> None:
    path = _project_path(project_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)


# ── Splitter ─────────────────────────────────────────────────────────────────

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=300,
    separators=["\n\n", "\n", ". ", " ", ""],
)


# ── BM25-style scoring ──────────────────────────────────────────────────────

_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in to for on with at by "
    "from and or not no nor but if then else when where how what which who whom "
    "this that these those it its".split()
)


def _tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP_WORDS and len(w) > 1]


def _bm25_score(query_tokens: List[str], doc_tokens: List[str], avg_dl: float, k1: float = 1.5, b: float = 0.75) -> float:
    tf = Counter(doc_tokens)
    dl = len(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        f = tf.get(qt, 0)
        if f == 0:
            continue
        numerator = f * (k1 + 1)
        denominator = f + k1 * (1 - b + b * dl / max(avg_dl, 1))
        score += numerator / denominator
    return score


class VectorStore:
    """Lightweight BM25-based document store — no external vector DB needed."""

    # ── Ingest ───────────────────────────────────────────────────────────────

    @staticmethod
    async def ingest_file(
        file_path: str,
        file_type: str,
        file_id: str,
        project_id: str,
    ) -> int:
        """Parse → chunk → store.  Returns chunk count."""
        raw_text = parse_file(file_path, file_type)
        if not raw_text.strip():
            logger.warning("File %s produced no text", file_id)
            return 0

        chunks = _splitter.split_text(raw_text)
        if not chunks:
            return 0

        store = _load_store(project_id)

        for i, chunk in enumerate(chunks):
            store.append({
                "id": f"{file_id}_chunk_{i}",
                "content": chunk,
                "file_id": file_id,
                "project_id": project_id,
                "chunk_index": i,
            })

        _save_store(project_id, store)
        logger.info(
            "Stored %d chunks for file %s in project %s",
            len(chunks), file_id, project_id,
        )
        return len(chunks)

    # ── Search ───────────────────────────────────────────────────────────────

    @staticmethod
    async def search(
        query: str,
        project_id: str,
        n_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve most relevant chunks using BM25 keyword scoring."""
        store = _load_store(project_id)
        if not store:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            # Fall back to returning first n chunks
            return [{"content": c["content"], "metadata": c} for c in store[:n_results]]

        # Pre-tokenize docs
        doc_tokens_list = [_tokenize(c["content"]) for c in store]
        avg_dl = sum(len(dt) for dt in doc_tokens_list) / max(len(doc_tokens_list), 1)

        scored = []
        for chunk, doc_tokens in zip(store, doc_tokens_list):
            s = _bm25_score(query_tokens, doc_tokens, avg_dl)
            if s > 0:
                scored.append((s, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {"content": c["content"], "metadata": {"file_id": c["file_id"], "project_id": c["project_id"]}}
            for _, c in scored[:n_results]
        ]

    # ── Delete ───────────────────────────────────────────────────────────────

    @staticmethod
    def delete_project_data(project_id: str) -> None:
        """Remove all stored chunks for a project."""
        path = _project_path(project_id)
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info("Deleted vector store for project %s", project_id)
        except Exception as exc:
            logger.warning("Could not delete store for %s: %s", project_id, exc)
