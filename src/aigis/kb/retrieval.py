"""Query building and cosine similarity retrieval from the knowledge base."""

import sys
from pathlib import Path

from aigis.kb.store import load_store
from aigis.schemas.checks import CheckResult, Severity


def build_query(checks: list[CheckResult]) -> str:
    """Build a retrieval query from WARN/CRITICAL checks."""
    parts = []
    for c in checks:
        if c.severity in (Severity.WARN, Severity.CRITICAL):
            parts.append(f"{c.check_id}: {c.message}")
    return " ".join(parts)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve(checks: list[CheckResult], config) -> str | None:
    """Return a formatted KB context block for the LLM prompt, or None.

    Loads the store, embeds the query, scores all chunks by cosine similarity,
    and returns the top-k results above min_score as a numbered list with
    source attribution. Returns None if the store is empty or no relevant
    chunks are found.
    """
    store_path = Path(config.store_path).expanduser()
    store = load_store(store_path)
    if not store:
        return None

    query = build_query(checks)
    if not query.strip():
        return None

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print(
            "aigis kb: sentence-transformers not installed — skipping KB retrieval",
            file=sys.stderr,
        )
        return None

    model = SentenceTransformer(config.model_name)
    query_emb = model.encode([query], show_progress_bar=False, convert_to_numpy=True)[0].tolist()

    scored = [
        (chunk, _cosine_similarity(query_emb, chunk.embedding))
        for chunk in store
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    top = [
        (chunk, score)
        for chunk, score in scored[: config.top_k]
        if score >= config.min_score
    ]
    if not top:
        return None

    lines = []
    for i, (chunk, score) in enumerate(top, 1):
        source_name = Path(chunk.source).name
        lines.append(f"{i}. [{source_name}] (relevance: {score:.2f})\n{chunk.content}")

    return "\n\n".join(lines)
