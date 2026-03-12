"""JSON-backed embedding store for the knowledge base."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class KBChunk:
    """Single embedded chunk from a knowledge base document."""

    source: str          # Original file path (str for JSON serialisability)
    content: str         # Raw text of this chunk
    embedding: list[float]
    source_hash: str     # SHA-256 of the source file at ingest time


def _hash_file(path: Path) -> str:
    """Return SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_store(path: Path) -> list[KBChunk]:
    """Load chunks from the JSON store. Returns [] if the file doesn't exist."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [KBChunk(**item) for item in data]
    except Exception:
        return []


def save_store(chunks: list[KBChunk], path: Path) -> None:
    """Persist chunks to the JSON store, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(c) for c in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def needs_reingest(kb_dir: Path, store: list[KBChunk]) -> bool:
    """Return True if any supported file in kb_dir has changed since last ingest."""
    stored_hashes: dict[str, str] = {c.source: c.source_hash for c in store}
    for path in kb_dir.rglob("*"):
        if path.suffix.lower() not in (".txt", ".md", ".pdf"):
            continue
        if not path.is_file():
            continue
        current = _hash_file(path)
        if stored_hashes.get(str(path)) != current:
            return True
    return False
