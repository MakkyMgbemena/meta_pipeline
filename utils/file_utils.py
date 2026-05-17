import re
import unicodedata


def clean_whitespace(text: str) -> str:
    """
    Removes excessive whitespace, newlines, tabs, and normalizes spacing.
    """
    if not isinstance(text, str):
        return text

    # Replace multiple spaces/newlines/tabs with a single space
    text = re.sub(r"\s+", " ", text)

    # Trim leading/trailing whitespace
    return text.strip()


def normalize_text(text: str) -> str:
    """
    Normalizes text to a consistent Unicode form and removes odd artifacts.
    Useful for cleaning scraped or user-generated content.
    """
    if not isinstance(text, str):
        return text

    # Normalize unicode characters (accents, symbols, etc.)
    text = unicodedata.normalize("NFKC", text)

    # Remove invisible zero-width characters
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

    return text
