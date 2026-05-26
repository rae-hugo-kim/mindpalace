"""Tests for mindpalace.masking."""
from mindpalace.masking import mask_secrets


def test_mask_sk_pattern():
    """T1: sk-... API key pattern must be masked."""
    text = "Use this key: sk-abc123XYZdef456 to call the API"
    result = mask_secrets(text)
    assert "sk-abc123XYZdef456" not in result
    assert "[MASKED]" in result


def test_mask_jwt_pattern():
    """T2: JWT three-segment token must be masked."""
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    text = f"Authorization: Bearer {jwt} for the request"
    result = mask_secrets(text)
    assert jwt not in result
    assert "[MASKED]" in result


def test_mask_password_keyword():
    """T3: value after a password/passwd/pwd keyword must be masked, keyword preserved."""
    text = "Connect with password: SuperSecret123! to login"
    result = mask_secrets(text)
    assert "SuperSecret123!" not in result
    assert "[MASKED]" in result
    # keyword preserved for context
    assert "password" in result.lower()


def test_mask_plain_text_unchanged():
    """T4 (regression net): text with no known secret patterns is returned as-is."""
    text = "Hello world. This is a normal sentence with no secrets."
    result = mask_secrets(text)
    assert result == text


def test_mask_multiple_secrets_in_one_text():
    """E2 (regression net): all secret occurrences in a single text are masked."""
    text = "key1=sk-abcdefghij12345 and password: foo123secret and bearer eyJaaaaaaaa.eyJbbbbbbbb.ccccccc done"
    result = mask_secrets(text)
    assert "sk-abcdefghij12345" not in result
    assert "foo123secret" not in result
    assert "eyJaaaaaaaa.eyJbbbbbbbb.ccccccc" not in result
    assert result.count("[MASKED]") >= 3
