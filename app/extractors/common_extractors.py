import re

from app.utils.gov_warning_text import CANONICAL_WARNING
from app.utils.text_normalization import normalize_for_warning


def extract_abv(ocr_text: str) -> dict:
    """Extract alcohol by volume (ABV) percentage from OCR text.

    Handles many OCR variations:
      - "40% ALC/VOL", "40% ABV", "ALC. 40% BY VOL"
      - "ALCOHOL 40% BY VOLUME", "40% ALC BY VOL"
      - "40% alc/vol (80 proof)", "ALC 40% BY VOL."
      - "40%ALC/VOL" (no space — common OCR output)
      - Standalone percentage near alcohol-related words
      - "(80 PROOF)" -> derive 40% from proof value
    """
    # Primary pattern: number% followed by alcohol-related text
    patterns = [
        # "40% ALC/VOL", "40% ALC BY VOL", "40%ALC/VOL"
        r"(\d{1,2}(?:\.\d{1,2})?)\s*%\s*(?:alc(?:ohol)?[\s./]*(?:by\s*)?vol(?:ume)?|abv)",
        # "ALC 40%", "ALC. 40%", "ALCOHOL 40%"
        r"(?:alc(?:ohol)?)\s*[.:]?\s*(\d{1,2}(?:\.\d{1,2})?)\s*%",
        # "40 % ALC" (OCR sometimes adds space before %)
        r"(\d{1,2}(?:\.\d{1,2})?)\s+%\s*alc",
        # "40 PERCENT" or "40 PER CENT"
        r"(\d{1,2}(?:\.\d{1,2})?)\s*(?:percent|per\s*cent)",
    ]

    for pattern in patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            # Find the first captured group that has a value
            abv = next((g for g in match.groups() if g is not None), None)
            if abv:
                return {"abv_percent": float(abv), "alcohol_label_present": True}

    # Fallback: extract from proof value (proof = 2 * ABV)
    # Matches "(80 PROOF)", "80 PROOF", "PROOF: 80"
    proof_match = re.search(r"(\d{2,3})\s*proof", ocr_text, re.IGNORECASE)
    if proof_match:
        proof_val = float(proof_match.group(1))
        return {"abv_percent": proof_val / 2.0, "alcohol_label_present": True}

    return {"abv_percent": None, "alcohol_label_present": False}


def extract_net_contents(ocr_text: str) -> dict:
    """Extract net contents volume statements from OCR text.

    Handles:
      - "750 mL", "750mL", "750 ML", "750ml"
      - "1.75 L", "1.75L", "1.75 LITERS"
      - "12 FL OZ", "12 FL. OZ.", "12FL OZ"
      - "355 ml", "330 cl"
      - "1 PINT", "1 PT"
      - "1 GALLON", "1 GAL"
      - OCR misreads: "750 mi" (l->i), "750 mI" (l->I)
    """
    patterns = [
        # FL OZ variations (must come before plain "oz" to match correctly)
        r"(\d+(?:\.\d+)?)\s*(?:fl\.?\s*oz\.?|fluid\s*oz(?:ounces?)?)",
        # mL/ml variations including OCR misreads (mi, mI for ml)
        r"(\d+(?:\.\d+)?)\s*(?:ml|m[il1|]|mi)",
        # Liters
        r"(\d+(?:\.\d+)?)\s*(?:l(?:iters?|itres?)?|ltrs?)(?:\s|$|[.])",
        # Centiliters
        r"(\d+(?:\.\d+)?)\s*cl",
        # Gallons
        r"(\d+(?:\.\d+)?)\s*(?:gal(?:lons?)?)",
        # Pints
        r"(\d+(?:\.\d+)?)\s*(?:pints?|pts?)",
        # Ounces (plain)
        r"(\d+(?:\.\d+)?)\s*oz\.?",
    ]

    candidates = []
    for pattern in patterns:
        matches = re.finditer(pattern, ocr_text, re.IGNORECASE)
        for m in matches:
            candidates.append(m.group(0).strip())

    return {"net_contents_candidates": candidates}


def extract_gov_warning(ocr_text: str) -> dict:
    """Check for the government warning statement — OCR-forgiving approach.

    Instead of requiring an exact canonical match, we:
      1. Check for "GOVERNMENT WARNING" header (allowing OCR spacing issues)
      2. Check for key warning phrases (fuzzy — just checking key words exist)
      3. Use a stripped/no-whitespace comparison for the overall match

    This handles OCR issues like extra spaces, missing punctuation, and
    minor character substitutions.
    """
    # Check 1: Header — "GOVERNMENT WARNING" in all caps.
    # Allow zero or more whitespace between/within the words — OCR often
    # merges them ("GOVERNMENTWARNING") or splits letters ("G OVERNMENT").
    header_present = bool(re.search(
        r"G\s*O\s*V\s*E\s*R\s*N\s*M\s*E\s*N\s*T\s*W\s*A\s*R\s*N\s*I\s*N\s*G",
        ocr_text
    ))

    # Check 2: Key warning phrases — look for important words from the warning.
    # OCR might garble punctuation but usually gets the words right.
    # We check individual key words rather than exact phrases.
    ocr_lower = ocr_text.lower()
    key_words = [
        "surgeon",
        "general",
        "pregnancy",
        "birth",
        "defects",
        "impairs",
        "machinery",
        "health",
    ]
    word_hits = sum(1 for word in key_words if word in ocr_lower)
    # Pass if at least 5 of 8 key words found — very forgiving of OCR errors
    body_present = word_hits >= 5

    # Check 3: Stripped canonical match — remove ALL whitespace and punctuation
    # from both strings, then check containment. This is the most forgiving
    # approach: "GOVERNMENTWARNING1AccordingtotheSurgeonGeneral..." etc.
    canon_stripped = normalize_for_warning(CANONICAL_WARNING)
    ocr_stripped = normalize_for_warning(ocr_text)
    canonical_match = canon_stripped in ocr_stripped

    return {
        "gov_warning_header_present": header_present,
        "gov_warning_body_present": body_present,
        "gov_warning_canonical_match": canonical_match,
    }
