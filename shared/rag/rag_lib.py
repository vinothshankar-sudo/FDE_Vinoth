"""Small RAG toolkit for the Fizzco Migration Assurance Hub (Module 3).

Pipeline: documents -> chunking -> embedding -> vector search -> (optional keyword search) -> grounded answer.

Design choices (kept small on purpose, to use few Databricks Free Edition calls):
  * Embeddings and chat answers come from Databricks Foundation Model API endpoints, called over REST.
    Every embedding and every answer is cached on disk, so re-running a script costs no new calls.
  * The vector index is an in-memory numpy matrix with cosine similarity. Module 4 replaces it with
    Databricks Vector Search.
  * "Token" means a whitespace-separated word piece. This is a proxy: about 0.75 English words per
    real model token, so "200 tokens" here is a little smaller than 200 real tokens.
  * An offline mode (TF-IDF vectors, extractive answers) exists only to test the code without a
    workspace. Results reported in the module README come from the Databricks mode.

Credentials come from environment variables only:
    DATABRICKS_HOST, DATABRICKS_TOKEN
Optional: RAG_EMBED_ENDPOINT, RAG_CHAT_ENDPOINT, RAG_CACHE_DIR
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

LOGGER = logging.getLogger("rag_lib")
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"

DEFAULT_EMBED_ENDPOINT = "databricks-gte-large-en"
DEFAULT_CHAT_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"
HTTP_TIMEOUT_SECONDS = 60
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 7
RETRY_START_SECONDS = 4.0
RETRY_MAX_SECONDS = 60.0
EMBED_BATCH_SIZE = int(os.environ.get("RAG_EMBED_BATCH", "4"))
PACE_SECONDS = float(os.environ.get("RAG_PACE_SECONDS", "1.5"))


def setup_logging() -> None:
    """Send progress and errors to stderr; answers go to stdout."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stderr)


# ----------------------------------------------------------------------------------------------
# Documents and chunks
# ----------------------------------------------------------------------------------------------
@dataclass
class Doc:
    doc_id: str
    title: str
    doc_type: str
    feed: str
    path: str
    body: str


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    doc_type: str
    feed: str
    section: str
    text: str
    n_tokens: int
    position: int = 0


_HEADER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _parse_header(text: str) -> Tuple[Dict[str, str], str]:
    match = _HEADER_RE.match(text)
    if not match:
        return {}, text
    meta: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, text[match.end():]


def _infer_meta(path: Path, body: str) -> Dict[str, str]:
    """Metadata for files that have no header, such as the generated lineage documents."""
    stem = path.stem
    feed = "all"
    for candidate in ("sell_in", "sell_out", "inventory", "promo"):
        if candidate in stem:
            feed = candidate
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return {
        "doc_id": "LIN-" + stem.replace("lineage_", "").replace("pl_fizzco_", "").replace("_load", "").upper().replace("_", "-"),
        "title": title_match.group(1).strip() if title_match else stem,
        "doc_type": "lineage" if stem.startswith("lineage") else "document",
        "feed": feed,
    }


def load_corpus(directories: Sequence[Path]) -> List[Doc]:
    docs: List[Doc] = []
    for directory in directories:
        for path in sorted(Path(directory).glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            text = path.read_text(encoding="utf-8")
            meta, body = _parse_header(text)
            if not meta:
                meta = _infer_meta(path, body)
            docs.append(Doc(meta["doc_id"], meta.get("title", path.stem), meta.get("doc_type", "document"),
                            meta.get("feed", "all"), str(path), body.strip()))
    LOGGER.info("loaded %d documents", len(docs))
    return docs


def chunk_doc(doc: Doc, size: int, overlap: int) -> List[Chunk]:
    """Slide a window of `size` whitespace tokens over the body, moving `size - overlap` each step."""
    if size <= overlap:
        raise ValueError("size must be larger than overlap")
    words: List[str] = []
    word_section: List[str] = []
    section = "Introduction"
    for line in doc.body.splitlines():
        heading = re.match(r"^#{1,3}\s+(.*)$", line)
        if heading:
            section = heading.group(1).strip()
        for word in line.split():
            words.append(word)
            word_section.append(section)
    chunks: List[Chunk] = []
    step = size - overlap
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        # Skip a tiny tail that is fully contained in the previous chunk's overlap.
        if chunks and end - start <= overlap:
            break
        text = " ".join(words[start:end])
        chunks.append(Chunk(
            chunk_id=f"{doc.doc_id}#c{len(chunks) + 1}", doc_id=doc.doc_id, title=doc.title,
            doc_type=doc.doc_type, feed=doc.feed, section=word_section[start], text=text,
            n_tokens=end - start, position=len(chunks) + 1))
        if end == len(words):
            break
        start += step
    return chunks


def chunk_corpus(docs: Sequence[Doc], size: int, overlap: int) -> List[Chunk]:
    chunks: List[Chunk] = []
    for doc in docs:
        chunks.extend(chunk_doc(doc, size, overlap))
    LOGGER.info("chunked %d docs into %d chunks (size=%d, overlap=%d)", len(docs), len(chunks), size, overlap)
    return chunks


# ----------------------------------------------------------------------------------------------
# Databricks REST access, with an on-disk cache
# ----------------------------------------------------------------------------------------------
class ConfigError(RuntimeError):
    pass


def cache_dir() -> Path:
    path = Path(os.environ.get("RAG_CACHE_DIR", Path(__file__).resolve().parent / ".rag_cache"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_get(kind: str, key: str) -> Optional[Any]:
    file = cache_dir() / f"{kind}_{key}.json"
    if file.exists():
        return json.loads(file.read_text(encoding="utf-8"))
    return None


def _cache_put(kind: str, key: str, value: Any) -> None:
    file = cache_dir() / f"{kind}_{key}.json"
    file.write_text(json.dumps(value), encoding="utf-8")


def _hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:32]


class DatabricksClient:
    """Minimal client for model serving endpoints: POST {host}/serving-endpoints/{name}/invocations."""

    def __init__(self) -> None:
        import requests  # imported here so offline tests do not need it

        self._requests = requests
        # RAG_CACHE_ONLY=1 replays a finished run from the on-disk cache: no credentials, no endpoint calls.
        self.cache_only = os.environ.get("RAG_CACHE_ONLY", "") == "1"
        host = os.environ.get("DATABRICKS_HOST", "").rstrip("/") or ("cache-only" if self.cache_only else "")
        raw_token = os.environ.get("DATABRICKS_TOKEN", "") or ("cache-only" if self.cache_only else "")
        # A terminal paste can add hidden escape sequences (ESC [ ...) to the token; remove them, then
        # keep only the characters a Databricks token can contain.
        token = re.sub(r"\x1b\[[0-9;?]*[A-Za-z~]", "", raw_token)
        token = re.sub(r"[^A-Za-z0-9_\-]", "", token)
        self.raw_token_length = len(raw_token)
        if not host or not token:
            raise ConfigError("Set DATABRICKS_HOST and DATABRICKS_TOKEN (see the module README).")
        self.host = host
        self.token_looks_ok = token.startswith("dapi") and token == token.strip() and " " not in token
        self.token_length = len(token)
        self._headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self.calls = 0
        self._last_call = 0.0

    def get(self, path: str) -> Dict[str, Any]:
        response = self._requests.get(self.host + path, headers=self._headers, timeout=HTTP_TIMEOUT_SECONDS)
        if response.status_code >= 400:
            raise RuntimeError(f"GET {path} returned {response.status_code}: {response.text[:300]}")
        return response.json()

    def invoke(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST to a serving endpoint. Free Edition rate limits (HTTP 429) are handled by pacing and backoff."""
        if self.cache_only:
            raise RuntimeError(f"cache-only mode: a result for endpoint {endpoint} is not in the cache; rerun with credentials")
        url = f"{self.host}/serving-endpoints/{endpoint}/invocations"
        delay = RETRY_START_SECONDS
        for attempt in range(1, MAX_RETRIES + 1):
            wait = self._last_call + PACE_SECONDS - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            response = self._requests.post(url, headers=self._headers, json=payload, timeout=HTTP_TIMEOUT_SECONDS)
            self._last_call = time.monotonic()
            self.calls += 1
            if response.status_code in RETRY_STATUSES and attempt < MAX_RETRIES:
                retry_after = response.headers.get("retry-after", "")
                pause = float(retry_after) if retry_after.replace(".", "", 1).isdigit() else delay
                LOGGER.warning("endpoint %s returned %s, retry %d in %.0fs", endpoint, response.status_code, attempt, pause)
                time.sleep(pause)
                delay = min(delay * 2, RETRY_MAX_SECONDS)
                continue
            if response.status_code >= 400:
                # Never echo request headers; the response body is safe to show.
                raise RuntimeError(f"endpoint {endpoint} returned {response.status_code}: {response.text[:300]}")
            return response.json()
        raise RuntimeError(f"endpoint {endpoint} failed after {MAX_RETRIES} attempts")


# ----------------------------------------------------------------------------------------------
# Embedders
# ----------------------------------------------------------------------------------------------
class DatabricksEmbedder:
    def __init__(self, client: DatabricksClient, endpoint: Optional[str] = None) -> None:
        self.client = client
        self.endpoint = endpoint or os.environ.get("RAG_EMBED_ENDPOINT", DEFAULT_EMBED_ENDPOINT)
        self.name = f"databricks:{self.endpoint}"

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        vectors: List[Optional[List[float]]] = [None] * len(texts)
        missing: List[int] = []
        for i, text in enumerate(texts):
            cached = _cache_get("emb", _hash(self.endpoint, text))
            if cached is None:
                missing.append(i)
            else:
                vectors[i] = cached
        LOGGER.info("embeddings: %d cached, %d to fetch from %s", len(texts) - len(missing), len(missing), self.endpoint)
        for start in range(0, len(missing), EMBED_BATCH_SIZE):
            batch_ids = missing[start:start + EMBED_BATCH_SIZE]
            result = self.client.invoke(self.endpoint, {"input": [texts[i] for i in batch_ids]})
            data = sorted(result["data"], key=lambda item: item.get("index", 0))
            if len(data) != len(batch_ids):
                raise RuntimeError("embedding endpoint returned an unexpected number of vectors")
            for i, item in zip(batch_ids, data):
                vectors[i] = item["embedding"]
                _cache_put("emb", _hash(self.endpoint, texts[i]), item["embedding"])
        matrix = np.array(vectors, dtype=np.float32)
        return _normalise(matrix)


class TfidfEmbedder:
    """Offline stand-in used only to test the code. It is lexical, not semantic."""

    name = "offline:tfidf"

    def __init__(self, corpus_texts: Sequence[str]) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=1)
        self._vectorizer.fit(list(corpus_texts))

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        return _normalise(self._vectorizer.transform(list(texts)).toarray().astype(np.float32))


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


# ----------------------------------------------------------------------------------------------
# Indexes: vector and keyword (BM25), plus hybrid fusion
# ----------------------------------------------------------------------------------------------
@dataclass
class Hit:
    chunk: Chunk
    score: float
    rank: int
    source: str = "vector"
    detail: Dict[str, float] = field(default_factory=dict)


def _allowed(chunk: Chunk, filters: Optional[Dict[str, Iterable[str]]]) -> bool:
    if not filters:
        return True
    for key, allowed in filters.items():
        if getattr(chunk, key) not in set(allowed):
            return False
    return True


class VectorIndex:
    def __init__(self, chunks: Sequence[Chunk], embedder: Any) -> None:
        self.chunks = list(chunks)
        self.embedder = embedder
        self.matrix = embedder.embed([c.text for c in self.chunks])

    def search(self, query: str, k: int = 3, filters: Optional[Dict[str, Iterable[str]]] = None) -> List[Hit]:
        query_vector = self.embedder.embed([query])[0]
        scores = self.matrix @ query_vector
        order = np.argsort(-scores)
        hits: List[Hit] = []
        for idx in order:
            chunk = self.chunks[int(idx)]
            if not _allowed(chunk, filters):
                continue
            hits.append(Hit(chunk, float(scores[idx]), len(hits) + 1, "vector"))
            if len(hits) == k:
                break
        return hits


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*")


def keyword_tokens(text: str) -> List[str]:
    """Lower-case tokens that keep ids such as JOB-0049 whole, and also add their parts (job, 0049)."""
    tokens: List[str] = []
    for raw in _TOKEN_RE.findall(text):
        low = raw.lower()
        tokens.append(low)
        if "-" in low:
            tokens.extend(low.split("-"))
    return tokens


class Bm25Index:
    def __init__(self, chunks: Sequence[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = list(chunks)
        self.k1, self.b = k1, b
        self.docs = [keyword_tokens(c.text) for c in self.chunks]
        self.avg_len = sum(len(d) for d in self.docs) / max(len(self.docs), 1)
        df: Dict[str, int] = {}
        for tokens in self.docs:
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def _score(self, query_tokens: Sequence[str], doc_tokens: Sequence[str]) -> float:
        if not doc_tokens:
            return 0.0
        counts: Dict[str, int] = {}
        for token in doc_tokens:
            counts[token] = counts.get(token, 0) + 1
        score = 0.0
        for token in query_tokens:
            if token not in counts:
                continue
            tf = counts[token]
            denom = tf + self.k1 * (1 - self.b + self.b * len(doc_tokens) / self.avg_len)
            score += self.idf.get(token, 0.0) * tf * (self.k1 + 1) / denom
        return score

    def search(self, query: str, k: int = 3, filters: Optional[Dict[str, Iterable[str]]] = None) -> List[Hit]:
        query_tokens = keyword_tokens(query)
        scored = [(self._score(query_tokens, d), i) for i, d in enumerate(self.docs)]
        scored.sort(key=lambda pair: -pair[0])
        hits: List[Hit] = []
        for score, i in scored:
            chunk = self.chunks[i]
            if score <= 0 or not _allowed(chunk, filters):
                continue
            hits.append(Hit(chunk, score, len(hits) + 1, "keyword"))
            if len(hits) == k:
                break
        return hits


def hybrid_search(vector: VectorIndex, keyword: Bm25Index, query: str, k: int = 3,
                  filters: Optional[Dict[str, Iterable[str]]] = None, pool: int = 10, rrf_k: int = 60) -> List[Hit]:
    """Reciprocal rank fusion of the vector and keyword rankings."""
    fused: Dict[str, float] = {}
    by_id: Dict[str, Chunk] = {}
    detail: Dict[str, Dict[str, float]] = {}
    for hits, label in ((vector.search(query, pool, filters), "vector_rank"), (keyword.search(query, pool, filters), "keyword_rank")):
        for hit in hits:
            cid = hit.chunk.chunk_id
            by_id[cid] = hit.chunk
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + hit.rank)
            detail.setdefault(cid, {})[label] = float(hit.rank)
    ranked = sorted(fused.items(), key=lambda pair: -pair[1])[:k]
    return [Hit(by_id[cid], score, i + 1, "hybrid", detail[cid]) for i, (cid, score) in enumerate(ranked)]


# ----------------------------------------------------------------------------------------------
# Generation
# ----------------------------------------------------------------------------------------------
NOT_FOUND_TEXT = "I could not find this in the Fizzco documents."

NAIVE_SYSTEM_PROMPT = "You are a helpful support assistant for Fizzco. Answer the question using the context."

GROUNDED_SYSTEM_PROMPT = (
    "You are a support assistant for Fizzco data engineering. Answer ONLY from the numbered context passages.\n"
    "Rules:\n"
    "1. Cite every fact with the passage label in square brackets, for example [S2]. Use only labels that exist.\n"
    f"2. If the passages do not contain the answer, reply exactly: {NOT_FOUND_TEXT} Do not guess, do not use general knowledge, and do not invent names, numbers or contacts.\n"
    "3. Be brief: at most five sentences or steps."
)


def format_context(hits: Sequence[Hit]) -> str:
    parts = []
    for i, hit in enumerate(hits, 1):
        c = hit.chunk
        parts.append(f"[S{i}] (source: {c.chunk_id}; {c.title}; section: {c.section})\n{c.text}")
    return "\n\n".join(parts)


class DatabricksChat:
    def __init__(self, client: DatabricksClient, endpoint: Optional[str] = None) -> None:
        self.client = client
        self.endpoint = endpoint or os.environ.get("RAG_CHAT_ENDPOINT", DEFAULT_CHAT_ENDPOINT)
        self.name = f"databricks:{self.endpoint}"

    def answer(self, question: str, hits: Sequence[Hit], system_prompt: str = GROUNDED_SYSTEM_PROMPT) -> str:
        user = f"Context passages:\n\n{format_context(hits)}\n\nQuestion: {question}"
        key = _hash(self.endpoint, system_prompt, user)
        cached = _cache_get("chat", key)
        if cached is not None:
            return cached
        result = self.client.invoke(self.endpoint, {
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}],
            "max_tokens": 400, "temperature": 0.0})
        text = result["choices"][0]["message"]["content"].strip()
        _cache_put("chat", key, text)
        return text


class ExtractiveChat:
    """Offline stand-in: returns the best-matching sentence of the top passage. Used only to test the code."""

    name = "offline:extractive"

    def answer(self, question: str, hits: Sequence[Hit], system_prompt: str = GROUNDED_SYSTEM_PROMPT) -> str:
        if not hits:
            return NOT_FOUND_TEXT
        q = set(keyword_tokens(question))
        best, best_score, label = "", 0, "S1"
        for i, hit in enumerate(hits, 1):
            for sentence in re.split(r"(?<=[.!?])\s+", hit.chunk.text):
                score = len(q & set(keyword_tokens(sentence)))
                if score > best_score:
                    best, best_score, label = sentence, score, f"S{i}"
        return f"{best} [{label}]" if best_score >= 3 else NOT_FOUND_TEXT


def cited_labels(answer: str) -> List[str]:
    return sorted(set(re.findall(r"\[(S\d+)\]", answer)))


def citation_check(answer: str, n_hits: int) -> Dict[str, Any]:
    labels = cited_labels(answer)
    valid = [lab for lab in labels if 1 <= int(lab[1:]) <= n_hits]
    return {"labels": labels, "all_valid": len(labels) == len(valid),
            "has_citation": bool(labels), "refused": NOT_FOUND_TEXT.lower()[:30] in answer.lower()}


# ----------------------------------------------------------------------------------------------
# Evaluation helpers
# ----------------------------------------------------------------------------------------------
def normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("`", "").replace("*", "")).lower()


def gold_rank(hits: Sequence[Hit], phrases: Sequence[str]) -> Optional[int]:
    """Rank (1-based) of the first retrieved chunk that contains any gold phrase, else None."""
    wanted = [normalise_text(p) for p in phrases]
    for hit in hits:
        text = normalise_text(hit.chunk.text)
        if any(p in text for p in wanted):
            return hit.rank
    return None


def build_indexes(chunks: Sequence[Chunk], embedder: Any) -> Tuple[VectorIndex, Bm25Index]:
    return VectorIndex(chunks, embedder), Bm25Index(chunks)


def write_out(text: str) -> None:
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
