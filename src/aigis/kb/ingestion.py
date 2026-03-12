"""Document loading, chunking, embedding, and store persistence."""

import sys
from dataclasses import dataclass
from pathlib import Path

from aigis.kb.store import KBChunk, _hash_file, load_store, save_store


@dataclass
class KBIngestionResult:
    """Summary of a single ingestion run."""

    source_file: str
    chunks_created: int
    status: str           # "success" | "error" | "skipped"
    error_message: str | None = None


def _extract_text(path: Path) -> str | None:
    """Extract plain text from a .txt or .pdf file. Returns None on failure."""
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"aigis kb: cannot read {path}: {e}", file=sys.stderr)
            return None
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # optional dep

            reader = PdfReader(str(path))
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                pages.append(text)
            return "\n\n".join(pages)
        except ImportError:
            print(
                "aigis kb: pypdf not installed. Install with: pip install aigis[kb]",
                file=sys.stderr,
            )
            return None
        except Exception as e:
            print(f"aigis kb: cannot read PDF {path}: {e}", file=sys.stderr)
            return None
    return None


def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into overlapping chunks using a sliding window."""
    chunks = []
    step = max(1, chunk_size - chunk_overlap)
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step
    return chunks


def _embed_chunks(texts: list[str], model_name: str) -> list[list[float]]:
    """Embed a list of text chunks using sentence-transformers."""
    try:
        from sentence_transformers import SentenceTransformer  # optional dep
    except ImportError:
        print(
            "aigis kb: sentence-transformers not installed. Install with: pip install aigis[kb]",
            file=sys.stderr,
        )
        raise

    model = SentenceTransformer(model_name)
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return [e.tolist() for e in embeddings]


def _ingest_file(path: Path, config) -> KBIngestionResult:
    """Ingest a single file into the store."""
    store_path = Path(config.store_path).expanduser()
    store = load_store(store_path)
    file_hash = _hash_file(path)
    source_key = str(path)

    # Check if already up-to-date
    existing_hashes = {c.source: c.source_hash for c in store}
    if existing_hashes.get(source_key) == file_hash:
        return KBIngestionResult(source_file=source_key, chunks_created=0, status="skipped")

    text = _extract_text(path)
    if text is None:
        return KBIngestionResult(
            source_file=source_key,
            chunks_created=0,
            status="error",
            error_message="Could not extract text",
        )

    raw_chunks = _chunk_text(text, config.chunk_size, config.chunk_overlap)
    if not raw_chunks:
        return KBIngestionResult(source_file=source_key, chunks_created=0, status="skipped")

    try:
        embeddings = _embed_chunks(raw_chunks, config.model_name)
    except ImportError:
        return KBIngestionResult(
            source_file=source_key,
            chunks_created=0,
            status="error",
            error_message="sentence-transformers not installed",
        )

    # Replace any existing chunks from this source, then append new ones
    store = [c for c in store if c.source != source_key]
    for content, embedding in zip(raw_chunks, embeddings):
        store.append(
            KBChunk(
                source=source_key,
                content=content,
                embedding=embedding,
                source_hash=file_hash,
            )
        )

    save_store(store, store_path)
    return KBIngestionResult(
        source_file=source_key,
        chunks_created=len(raw_chunks),
        status="success",
    )


def ingest(source: Path, config) -> KBIngestionResult:
    """Ingest a file or directory into the knowledge base.

    If source is a directory, all .txt and .pdf files are ingested recursively.
    Returns a combined result when ingesting a directory (summary).
    """
    source = source.expanduser().resolve()

    if source.is_file():
        return _ingest_file(source, config)

    if source.is_dir():
        total_chunks = 0
        errors: list[str] = []
        for path in sorted(source.rglob("*")):
            if path.suffix.lower() not in (".txt", ".md", ".pdf") or not path.is_file():
                continue
            result = _ingest_file(path, config)
            if result.status == "error":
                errors.append(f"{path.name}: {result.error_message}")
            else:
                total_chunks += result.chunks_created
        return KBIngestionResult(
            source_file=str(source),
            chunks_created=total_chunks,
            status="error" if errors else "success",
            error_message="; ".join(errors) if errors else None,
        )

    return KBIngestionResult(
        source_file=str(source),
        chunks_created=0,
        status="error",
        error_message="Path does not exist",
    )
