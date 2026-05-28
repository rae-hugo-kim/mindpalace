"""Sentence-transformers wrapper for chunk + query embeddings.

Uses ``intfloat/multilingual-e5-large`` — a 1024-dim multilingual model
trained with the query/passage asymmetric retrieval objective. e5
expects an ``"query: "`` prefix on user queries and ``"passage: "`` on
stored documents; encoding without prefixes loses substantial recall.
``embed_query`` and ``embed_chunk`` add the right prefix so callers
don't have to.

Vectors are L2-normalized (e5 was trained for cosine similarity, and
L2 distance on unit vectors ranges in [0, 2] — much tighter than the
old MiniLM range — so callers should use the recalibrated default
confidence threshold in ``mindpalace.search``).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import for type hints only
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-large"
EMBEDDING_DIM = 1024

_model: "SentenceTransformer | None" = None


def _get_model() -> "SentenceTransformer":
    """Return the module-level model, loading it on first call (lazy)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _encode(text: str, prefix: str) -> list[float]:
    vec = _get_model().encode(
        prefix + text,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [float(x) for x in vec.tolist()]


def embed_chunk(text: str) -> list[float]:
    """Encode a stored chunk (passage). Length :data:`EMBEDDING_DIM`."""
    return _encode(text, "passage: ")


def embed_query(text: str) -> list[float]:
    """Encode a user search query. Length :data:`EMBEDDING_DIM`.

    Uses e5's ``query:`` prefix so the resulting vector is in the
    correct sub-space for matching against passage-encoded chunks.
    """
    return _encode(text, "query: ")
