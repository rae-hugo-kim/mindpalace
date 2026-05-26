"""Tests for mindpalace.masking."""
from mindpalace.masking import mask_secrets


def test_mask_sk_pattern():
    """T1: sk-... API key pattern must be masked."""
    text = "Use this key: sk-abc123XYZdef456 to call the API"
    result = mask_secrets(text)
    assert "sk-abc123XYZdef456" not in result
    assert "[MASKED]" in result


def test_mask_jwt_pattern():
    """T2 (RED): JWT three-segment token must be masked."""
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    text = f"Authorization: Bearer {jwt} for the request"
    result = mask_secrets(text)
    assert jwt not in result
    assert "[MASKED]" in result
