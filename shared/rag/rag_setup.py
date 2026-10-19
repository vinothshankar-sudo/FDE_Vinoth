"""Shared setup for the Module 3 scenario scripts: paths, components, test questions."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, List, Sequence, Tuple

import rag_lib as R

RAG_DIR = Path(__file__).resolve().parent
ASSIGNMENT_DIR = RAG_DIR.parents[1]
CORPUS_DIRS = [ASSIGNMENT_DIR / "shared" / "docs_corpus", ASSIGNMENT_DIR / "shared" / "fizzco_lake" / "docs"]


def mode() -> str:
    """'databricks' (default) uses the workspace endpoints; 'offline' is for code tests only."""
    return os.environ.get("RAG_MODE", "databricks").lower()


def load_docs() -> List[R.Doc]:
    return R.load_corpus(CORPUS_DIRS)


def make_components(chunks_for_offline: Sequence[R.Chunk]) -> Tuple[Any, Any, Any]:
    """Return (embedder, chat, client). The client is None in offline mode."""
    if mode() == "offline":
        R.LOGGER.warning("RAG_MODE=offline: lexical vectors and extractive answers. Do NOT use for reported results.")
        return R.TfidfEmbedder([c.text for c in chunks_for_offline]), R.ExtractiveChat(), None
    client = R.DatabricksClient()
    return R.DatabricksEmbedder(client), R.DatabricksChat(client), client


def load_questions() -> List[dict]:
    return json.loads((RAG_DIR / "test_questions.json").read_text(encoding="utf-8"))["questions"]


def format_hits(hits: Sequence[R.Hit]) -> str:
    lines = []
    for hit in hits:
        c = hit.chunk
        extra = ""
        if hit.detail:
            extra = "  (" + ", ".join(f"{k}={int(v)}" for k, v in sorted(hit.detail.items())) + ")"
        lines.append(f"  {hit.rank}. {c.chunk_id:<24} score={hit.score:.4f} [{c.feed}/{c.doc_type}] {c.section}{extra}")
    return "\n".join(lines)


def excerpt(text: str, n: int = 150) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= n else flat[:n].rstrip() + "..."


def facts_ok(answer: str, groups: Sequence[Sequence[str]]) -> bool:
    low = R.normalise_text(answer)
    return all(any(R.normalise_text(w) in low for w in group) for group in groups)
