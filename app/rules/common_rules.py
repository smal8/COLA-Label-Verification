"""Common validation rules shared across all beverage types.

Each rule function takes a ValidationContext and returns:
  - None if the check passes
  - A Discrepancy dict if the check fails

Both pass and fail results include an "ocr_found" field showing what
OCR detected for that field, for display in the UI.

Rules are OCR-forgiving: they use fuzzy matching to handle common OCR
errors like character substitutions ('l'->'1', 'O'->'0'), missing
punctuation, and extra/missing spaces.
"""

import re

from app.utils.text_normalization import normalize_loose, fuzzy_token_match, fuzzy_token_find


def ocr_empty_text(ctx) -> dict | None:
    """OCR_EMPTY_TEXT — fails if OCR produced no usable text."""
    if not ctx.ocr_raw or len(ctx.ocr_raw.strip()) < 5:
        return {
            "field": "ocr",
            "rule_id": "OCR_EMPTY_TEXT",
            "message": "OCR produced no usable text from this image.",
            "ocr_found": "",
        }
    return None


def brand_name_contains(ctx) -> dict | None:
    """BRAND_NAME_CONTAINS — fuzzy check that brand name appears in OCR text."""
    expected = normalize_loose(ctx.form.brand_name)
    ocr = ctx.ocr_loose

    # Find best matching snippet from OCR to show the user
    ocr_snippet = _find_snippet(expected, ctx.ocr_raw)

    # Exact substring match (fast path)
    if expected in ocr:
        ctx._ocr_found_brand = ocr_snippet or ctx.form.brand_name
        return None

    # Fuzzy: check each word individually
    tokens = [t for t in expected.split() if len(t) >= 2]
    if not tokens:
        ctx._ocr_found_brand = ocr_snippet
        return None

    hits = sum(1 for t in tokens if fuzzy_token_match(t, ocr, max_distance=1))
    if hits >= max(1, len(tokens) - 1):
        ctx._ocr_found_brand = ocr_snippet or "(fuzzy match)"
        return None

    return {
        "field": "brand_name",
        "rule_id": "BRAND_NAME_CONTAINS",
        "message": "Brand name not found or does not match.",
        "ocr_found": ocr_snippet or "Not detected",
    }


def designation_contains(ctx) -> dict | None:
    """DESIGNATION_CONTAINS — fuzzy check that class/type designation appears."""
    expected = normalize_loose(ctx.form.class_type_designation)
    ocr = ctx.ocr_loose

    ocr_snippet = _find_snippet(expected, ctx.ocr_raw)

    if expected in ocr:
        ctx._ocr_found_designation = ocr_snippet or ctx.form.class_type_designation
        return None

    tokens = [t for t in expected.split() if len(t) >= 2]
    if not tokens:
        ctx._ocr_found_designation = ocr_snippet
        return None

    hits = sum(1 for t in tokens if fuzzy_token_match(t, ocr, max_distance=1))
    if hits >= max(1, len(tokens) - 1):
        ctx._ocr_found_designation = ocr_snippet or "(fuzzy match)"
        return None

    return {
        "field": "class_type_designation",
        "rule_id": "DESIGNATION_CONTAINS",
        "message": "Class/type designation not found or does not match.",
        "ocr_found": ocr_snippet or "Not detected",
    }


def net_contents_present(ctx) -> dict | None:
    """NET_CONTENTS_PRESENT — checks that a matching volume statement was detected.

    Compares the submitted net contents value against all candidates extracted
    from OCR. Uses normalized comparison to handle formatting differences.
    """
    candidates = ctx.extracted.get("net_contents_candidates", [])
    if not candidates:
        return {
            "field": "net_contents",
            "rule_id": "NET_CONTENTS_PRESENT",
            "message": "Net contents statement not detected on label.",
            "ocr_found": "Not detected",
        }

    # Normalize submitted value for comparison
    submitted_norm = normalize_loose(ctx.form.net_contents)
    # Also create a spaceless version for OCR like "12FL.OZ." -> "12floz"
    submitted_compact = submitted_norm.replace(" ", "")

    # Check each candidate for a match
    for candidate in candidates:
        candidate_norm = normalize_loose(candidate)
        candidate_compact = candidate_norm.replace(" ", "")
        # Check with and without spaces to handle "12 fl oz" vs "12floz"
        if (submitted_norm in candidate_norm or candidate_norm in submitted_norm
                or submitted_compact == candidate_compact):
            ctx._ocr_found_net_contents = candidate
            return None

    # Also try extracting just the numbers and comparing
    submitted_num = re.sub(r"[^0-9.]", "", ctx.form.net_contents)
    for candidate in candidates:
        candidate_num = re.sub(r"[^0-9.]", "", candidate)
        if submitted_num and candidate_num and submitted_num == candidate_num:
            ctx._ocr_found_net_contents = candidate
            return None

    # Candidates found but none match the submitted value
    ctx._ocr_found_net_contents = ", ".join(candidates)
    return {
        "field": "net_contents",
        "rule_id": "NET_CONTENTS_PRESENT",
        "message": f"Net contents mismatch: label shows \"{', '.join(candidates)}\" but form declares \"{ctx.form.net_contents}\".",
        "ocr_found": ", ".join(candidates),
    }


def name_address_contains(ctx) -> dict | None:
    """NAME_ADDRESS_CONTAINS — check that name/address tokens appear in OCR.

    Short tokens (3-4 chars) require exact match to avoid false positives.
    Longer tokens (5+ chars) allow 1 char fuzzy distance for OCR errors.
    """
    submitted = normalize_loose(ctx.form.name_address)
    tokens = [t for t in submitted.split() if len(t) >= 3]

    if not tokens:
        return None

    matched_pairs = []  # (submitted_token, ocr_word)
    for token in tokens:
        # Short tokens (<=4 chars): exact only to avoid false positives
        if len(token) <= 4:
            if token in ctx.ocr_loose:
                matched_pairs.append((token, token))
        else:
            # Longer tokens: fuzzy match, but show what OCR word was matched
            ocr_word = fuzzy_token_find(token, ctx.ocr_loose, max_distance=1)
            if ocr_word:
                matched_pairs.append((token, ocr_word))

    hits = len(matched_pairs)
    threshold = max(1, len(tokens) // 3)

    # Show "submitted→ocr_word" for fuzzy matches so user can see what matched
    match_strs = []
    for submitted, ocr_word in matched_pairs:
        if submitted == ocr_word:
            match_strs.append(submitted)
        else:
            match_strs.append(f"{submitted}→{ocr_word}")
    found_str = ", ".join(match_strs) if match_strs else "none"

    if hits >= threshold:
        ctx._ocr_found_address = f"Matched: {found_str} ({hits}/{len(tokens)} tokens)"
        return None

    return {
        "field": "name_address",
        "rule_id": "NAME_ADDRESS_CONTAINS",
        "message": f"Producer/bottler name and address not found (matched {hits}/{len(tokens)} tokens).",
        "ocr_found": f"Matched: {found_str} ({hits}/{len(tokens)} tokens)",
    }


def gov_warning_exact(ctx) -> dict | None:
    """GOV_WARNING_EXACT — OCR-forgiving government warning check."""
    header_present = ctx.extracted.get("gov_warning_header_present", False)
    body_present = ctx.extracted.get("gov_warning_body_present", False)
    canonical_match = ctx.extracted.get("gov_warning_canonical_match", False)

    if not header_present:
        stripped = re.sub(r"[^A-Za-z]", "", ctx.ocr_raw)
        header_present = "GOVERNMENTWARNING" in stripped

    # Build a summary of what was found
    ocr_lower = ctx.ocr_raw.lower()
    key_words = ["surgeon", "general", "pregnancy", "birth", "defects", "impairs", "machinery", "health"]
    found_words = [w for w in key_words if w in ocr_lower]

    if not header_present:
        return {
            "field": "government_warning",
            "rule_id": "GOV_WARNING_EXACT",
            "message": 'Government warning header "GOVERNMENT WARNING" not found in required uppercase.',
            "ocr_found": f"Header: not found, Keywords: {', '.join(found_words) if found_words else 'none'}",
        }

    if canonical_match or body_present:
        ctx._ocr_found_warning = f"Header: found, Keywords: {', '.join(found_words)} ({len(found_words)}/8)"
        return None

    word_hits = len(found_words)
    if word_hits >= 3:
        ctx._ocr_found_warning = f"Header: found, Keywords: {', '.join(found_words)} ({word_hits}/8)"
        return None

    return {
        "field": "government_warning",
        "rule_id": "GOV_WARNING_EXACT",
        "message": "Government warning statement text not sufficiently detected.",
        "ocr_found": f"Header: found, Keywords: {', '.join(found_words) if found_words else 'none'} ({word_hits}/8)",
    }


def _find_snippet(query: str, raw_text: str, window: int = 60) -> str | None:
    """Find the best matching snippet from raw OCR text for display."""
    if not query or not raw_text:
        return None
    query_lower = query.lower()
    text_lower = raw_text.lower()
    idx = text_lower.find(query_lower)
    if idx == -1:
        # Try first significant word
        words = [w for w in query_lower.split() if len(w) >= 3]
        if words:
            idx = text_lower.find(words[0])
    if idx == -1:
        return None
    start = max(0, idx - 10)
    end = min(len(raw_text), idx + window)
    snippet = raw_text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(raw_text):
        snippet = snippet + "..."
    return snippet
