"""Secret masking for raw imports."""
import re

# (pattern, replacement) — replacement may reference groups (e.g. r"\1\2[MASKED]")
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "[MASKED]"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"), "[MASKED]"),
    (re.compile(r"(?i)(password|passwd|pwd)(\s*[:=]\s*)(\S+)"), r"\1\2[MASKED]"),
]


def mask_secrets(text: str) -> str:
    """Mask known secret patterns in text.

    Returns the (possibly modified) text with secrets replaced by [MASKED].
    Keyword-anchored patterns (e.g. password) preserve the keyword and only
    mask the value via group references in the replacement.
    """
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text
