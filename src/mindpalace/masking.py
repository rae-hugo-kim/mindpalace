"""Secret masking for raw imports."""
import re

_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
]


def mask_secrets(text: str) -> str:
    """Mask known secret patterns in text.

    Returns the (possibly modified) text with secrets replaced by [MASKED].
    """
    for pattern in _PATTERNS:
        text = pattern.sub("[MASKED]", text)
    return text
