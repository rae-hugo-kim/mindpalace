"""Tests for mindpalace.embedding.

NOTE: These tests touch the real sentence-transformers model
(``paraphrase-multilingual-MiniLM-L12-v2``). First run downloads
~470MB and may take 1-5 minutes; subsequent runs hit the local cache.
"""
import pytest

from mindpalace.embedding import EMBEDDING_DIM, embed_chunk


@pytest.fixture(scope="module")
def warm_model():
    """Trigger a one-time encode so later assertions don't pay the warm-up cost."""
    embed_chunk("warmup")


def test_embed_chunk_shape(warm_model):
    """T7 (RED): embed returns a list[float] of EMBEDDING_DIM dimensions."""
    vec = embed_chunk("Hello world")
    assert isinstance(vec, list)
    assert len(vec) == EMBEDDING_DIM
    assert all(isinstance(x, float) for x in vec)


def test_embed_chunk_deterministic(warm_model):
    """T7: same input must yield the same vector (model is deterministic in eval mode)."""
    v1 = embed_chunk("repeatable text")
    v2 = embed_chunk("repeatable text")
    assert v1 == v2


def test_embed_chunk_distinguishes_different_text(warm_model):
    """T7: semantically different inputs must yield non-identical vectors (sanity)."""
    v1 = embed_chunk("How do I configure MCP servers?")
    v2 = embed_chunk("What is the capital of France?")
    assert v1 != v2
