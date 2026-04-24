"""Tests for KB ingestion and retrieval (no model download required)."""

import json
import math
from pathlib import Path

import pytest

from aigis.kb.ingestion import _chunk_text, _extract_text
from aigis.kb.retrieval import build_query, _cosine_similarity
from aigis.kb.store import KBChunk, load_store, needs_reingest, save_store
from aigis.schemas.checks import CheckResult, Severity


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def test_chunk_txt_produces_expected_count() -> None:
    """Sliding window produces the right number of chunks."""
    text = "A" * 2000
    chunks = _chunk_text(text, chunk_size=800, chunk_overlap=80)
    # step = 720 → starts: 0, 720, 1440 → 3 chunks
    assert len(chunks) == 3


def test_chunk_overlap_shared_content() -> None:
    """Adjacent chunks share chunk_overlap characters at their boundary."""
    # text length 880 = chunk_size(800) + chunk_overlap(80) → exactly 2 chunks
    text = "X" * 880
    chunks = _chunk_text(text, chunk_size=800, chunk_overlap=80)
    assert len(chunks) == 2
    # Last 80 chars of chunk[0] == first 80 chars of chunk[1]
    assert chunks[0][-80:] == chunks[1][:80]


def test_chunk_short_text_single_chunk() -> None:
    """Text shorter than chunk_size produces exactly one chunk."""
    chunks = _chunk_text("hello world", chunk_size=800, chunk_overlap=80)
    assert len(chunks) == 1
    assert chunks[0] == "hello world"


def test_chunk_empty_text() -> None:
    """Empty text produces no chunks."""
    assert _chunk_text("", chunk_size=800, chunk_overlap=80) == []


# ---------------------------------------------------------------------------
# Store round-trip
# ---------------------------------------------------------------------------


def test_store_roundtrip(tmp_path: Path) -> None:
    """save_store + load_store preserves all fields."""
    chunks = [
        KBChunk(source="/a.txt", content="hello", embedding=[0.1, 0.2], source_hash="abc"),
        KBChunk(source="/b.txt", content="world", embedding=[0.3, 0.4], source_hash="def"),
    ]
    store_file = tmp_path / "kb_store.json"
    save_store(chunks, store_file)
    loaded = load_store(store_file)
    assert len(loaded) == 2
    assert loaded[0].source == "/a.txt"
    assert loaded[0].embedding == [0.1, 0.2]
    assert loaded[1].content == "world"


def test_load_store_missing_file(tmp_path: Path) -> None:
    """load_store returns [] when the file doesn't exist."""
    result = load_store(tmp_path / "nonexistent.json")
    assert result == []


# ---------------------------------------------------------------------------
# needs_reingest
# ---------------------------------------------------------------------------


def test_needs_reingest_detects_change(tmp_path: Path) -> None:
    """needs_reingest returns True when a file's content has changed."""
    doc = tmp_path / "guide.txt"
    doc.write_text("original content")

    import hashlib

    old_hash = hashlib.sha256(b"old content").hexdigest()
    store = [KBChunk(source=str(doc), content="x", embedding=[], source_hash=old_hash)]

    assert needs_reingest(tmp_path, store) is True


def test_needs_reingest_no_change(tmp_path: Path) -> None:
    """needs_reingest returns False when all file hashes match."""
    doc = tmp_path / "guide.txt"
    doc.write_text("stable content")

    import hashlib

    current_hash = hashlib.sha256(b"stable content").hexdigest()
    store = [KBChunk(source=str(doc), content="x", embedding=[], source_hash=current_hash)]

    assert needs_reingest(tmp_path, store) is False


def test_needs_reingest_new_file(tmp_path: Path) -> None:
    """needs_reingest returns True when a new file appears in kb_dir."""
    (tmp_path / "new.txt").write_text("new doc")
    # Empty store — no hashes recorded
    assert needs_reingest(tmp_path, []) is True


# ---------------------------------------------------------------------------
# build_query
# ---------------------------------------------------------------------------


def test_build_query_includes_warn_critical() -> None:
    """build_query includes WARN and CRITICAL checks."""
    checks = [
        CheckResult(check_id="restic_backup", name="Restic", severity=Severity.CRITICAL, message="Repo unreachable"),
        CheckResult(check_id="disk_usage", name="Disk", severity=Severity.WARN, message="90% used"),
        CheckResult(check_id="system_load", name="Load", severity=Severity.OK, message="OK"),
    ]
    query = build_query(checks)
    assert "restic_backup" in query
    assert "Repo unreachable" in query
    assert "disk_usage" in query
    assert "90% used" in query
    assert "system_load" not in query  # OK excluded


def test_build_query_empty_on_all_ok() -> None:
    """build_query returns empty string when all checks are OK."""
    checks = [
        CheckResult(check_id="disk_usage", name="Disk", severity=Severity.OK, message="OK"),
    ]
    assert build_query(checks).strip() == ""


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


def test_cosine_similarity_identical() -> None:
    """Identical vectors have cosine similarity 1.0."""
    v = [1.0, 0.0, 0.0]
    assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal() -> None:
    """Orthogonal vectors have cosine similarity 0.0."""
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(_cosine_similarity(a, b)) < 1e-6


def test_cosine_similarity_zero_vector() -> None:
    """Zero vector returns 0.0 without division error."""
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# retrieve (mock embeddings — no model download)
# ---------------------------------------------------------------------------


class _MockConfig:
    store_path: str
    model_name: str = "unused"
    top_k: int = 2
    min_score: float = 0.5

    def __init__(self, store_path: str) -> None:
        self.store_path = store_path


def _make_unit_vec(dim: int, idx: int) -> list[float]:
    """Unit vector with 1.0 at position idx, 0 elsewhere."""
    v = [0.0] * dim
    v[idx] = 1.0
    return v


def test_retrieve_empty_store(tmp_path: Path, monkeypatch) -> None:
    """retrieve returns None when the store is empty."""
    from aigis.kb import retrieval as ret_mod

    cfg = _MockConfig(str(tmp_path / "empty.json"))

    checks = [
        CheckResult(check_id="disk_usage", name="Disk", severity=Severity.CRITICAL, message="95% used"),
    ]
    result = ret_mod.retrieve(checks, cfg)
    assert result is None


class _Vec(list):
    """list subclass that exposes .tolist() so retrieve() can call it without numpy."""

    def tolist(self) -> list[float]:
        return list(self)


def _fake_st_module(vec: list[float]):
    """Return a fake sentence_transformers module whose model returns vec."""
    import sys
    import types

    class _FakeModel:
        def encode(self, texts, **kw):
            return [_Vec(vec)]

    fake = types.ModuleType("sentence_transformers")
    fake.SentenceTransformer = lambda name: _FakeModel()
    return fake


def test_retrieve_below_threshold(tmp_path: Path, monkeypatch) -> None:
    """retrieve returns None when best score is below min_score."""
    import sys
    from aigis.kb import retrieval as ret_mod

    store_path = tmp_path / "kb.json"
    # Chunk embedding at dim 2; query embedding will be at dim 0 → cosine = 0
    chunks = [KBChunk(source="/a.txt", content="irrelevant", embedding=_make_unit_vec(3, 2), source_hash="x")]
    save_store(chunks, store_path)

    cfg = _MockConfig(str(store_path))
    cfg.min_score = 0.99

    monkeypatch.setitem(sys.modules, "sentence_transformers", _fake_st_module(_make_unit_vec(3, 0)))

    checks = [CheckResult(check_id="x", name="x", severity=Severity.CRITICAL, message="y")]
    result = ret_mod.retrieve(checks, cfg)
    assert result is None


def test_retrieve_returns_top_k(tmp_path: Path, monkeypatch) -> None:
    """retrieve returns formatted block with up to top_k chunks above threshold."""
    import sys
    from aigis.kb import retrieval as ret_mod

    # 3 chunks all matching the query vector → score 1.0; top_k=2 → only 2 returned
    store_path = tmp_path / "kb.json"
    chunks = [
        KBChunk(source="/runbook.txt", content=f"chunk {i}", embedding=_make_unit_vec(3, 0), source_hash="h")
        for i in range(3)
    ]
    save_store(chunks, store_path)

    cfg = _MockConfig(str(store_path))
    cfg.top_k = 2
    cfg.min_score = 0.5

    monkeypatch.setitem(sys.modules, "sentence_transformers", _fake_st_module(_make_unit_vec(3, 0)))

    checks = [CheckResult(check_id="x", name="x", severity=Severity.CRITICAL, message="y")]
    result = ret_mod.retrieve(checks, cfg)

    assert result is not None
    assert result.count("[runbook.txt]") == 2
    assert "relevance:" in result
