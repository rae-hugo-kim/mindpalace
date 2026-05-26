"""Sentence-transformers wrapper for chunk embeddings (v0).

Default model is multilingual + lightweight to cover the user's mixed
Korean/English corpus while staying CPU-friendly.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import for type hints only
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

_model: "SentenceTransformer | None" = None


def _get_model() -> "SentenceTransformer":
    """Return the module-level model, loading it on first call (lazy)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_chunk(text: str) -> list[float]:
    """Encode ``text`` into a fixed-dimension dense vector.

    Returns a Python list of floats (length :data:`EMBEDDING_DIM`).
    """
    vec = _get_model().encode(text, convert_to_numpy=True, show_progress_bar=False)
    return [float(x) for x in vec.tolist()]
