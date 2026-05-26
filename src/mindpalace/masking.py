"""Secret masking for raw imports."""
import re

_SK_PATTERN = re.compile(r"sk-[A-Za-z0-9_\-]{8,}")


def mask_secrets(text: str) -> str:
    """Mask known secret patterns in text.

    Returns the (possibly modified) text with secrets replaced by [MASKED].
    """
    return _SK_PATTERN.sub("[MASKED]", text)
