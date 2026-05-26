"""Tests for mindpalace.masking."""
from mindpalace.masking import mask_secrets


def test_mask_sk_pattern():
    """T1 (RED): sk-... API key pattern must be masked."""
    text = "Use this key: sk-abc123XYZdef456 to call the API"
    result = mask_secrets(text)
    assert "sk-abc123XYZdef456" not in result
    assert "[MASKED]" in result
