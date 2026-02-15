import re
import unicodedata


def normalize_loose(text: str) -> str:
    """Loose normalization for case-insensitive contains checks.

    Used for: brand name, designation, name/address matching.
    Steps:
      1. Lowercase everything
      2. Normalize unicode quotes/apostrophes to ASCII equivalents
      3. Collapse all whitespace (spaces, newlines, tabs) into single spaces
      4. Remove punctuation except alphanumerics and spaces for stable matching
    """
    text = text.lower()

    # Replace unicode curly quotes/apostrophes with ASCII straight quote.
    # OCR engines often produce these variants inconsistently.
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')

    # Collapse any sequence of whitespace characters into a single space
    text = re.sub(r"\s+", " ", text)

    # Strip everything that isn't alphanumeric or space.
    text = re.sub(r"[^a-z0-9 ]", "", text)

    return text.strip()


def normalize_strict(text: str) -> str:
    """Strict normalization — preserves case and punctuation, collapses whitespace only."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_warning(text: str) -> str:
    """Warning-specific normalization — strips whitespace and punctuation, keeps case.

    Used for government warning matching. OCR often garbles punctuation and
    spacing but gets the actual letters mostly right. We only care that
    the right words appear in all caps.
    """
    # Remove all whitespace
    text = re.sub(r"\s+", "", text)
    # Remove punctuation — keep only alphanumerics
    text = re.sub(r"[^A-Za-z0-9]", "", text)
    return text


def _fuzzy_word_match(token: str, words: list[str], max_distance: int) -> str | None:
    """Compare token against whole words, return the matched word or None."""
    token_len = len(token)
    for word in words:
        if abs(len(word) - token_len) > max_distance:
            continue
        min_len = min(len(word), token_len)
        mismatches = sum(1 for a, b in zip(token[:min_len], word[:min_len]) if a != b)
        mismatches += abs(len(word) - token_len)
        if mismatches <= max_distance:
            return word
    return None


def fuzzy_token_match(token: str, text: str, max_distance: int = 1) -> bool:
    """Check if a token appears in text, allowing up to max_distance character differences.

    Only matches against whole words to avoid matching random substrings
    within unrelated words.
    """
    if not token or not text:
        return False

    if token in text:
        return True

    return _fuzzy_word_match(token, text.split(), max_distance) is not None


def fuzzy_token_find(token: str, text: str, max_distance: int = 1) -> str | None:
    """Like fuzzy_token_match but returns the actual OCR word that matched."""
    if not token or not text:
        return None

    if token in text:
        return token

    return _fuzzy_word_match(token, text.split(), max_distance)
