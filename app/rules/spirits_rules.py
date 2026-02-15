"""Alcohol content validation rules.

These rules run for all beverage types. The validator's info_rule_ids
controls whether failures here are "error" (spirits) or "info" (malt/wine).
"""


def alc_percent_present(ctx) -> dict | None:
    """ALC_PERCENT_PRESENT — checks that an ABV pattern was detected on the label."""
    if not ctx.extracted.get("alcohol_label_present", False):
        return {
            "field": "alcohol_content",
            "rule_id": "ALC_PERCENT_PRESENT",
            "message": "Alcohol content (ABV) not detected on label.",
            "ocr_found": "Not detected",
        }
    ctx._ocr_found_abv = f"{ctx.extracted.get('abv_percent')}%"
    return None


def alc_percent_match_exact(ctx) -> dict | None:
    """ALC_PERCENT_MATCH_EXACT — checks that detected ABV matches the submitted value."""
    if not ctx.form.alcohol_content:
        return None

    extracted_abv = ctx.extracted.get("abv_percent")
    if extracted_abv is None:
        return None

    submitted = ctx.form.alcohol_content.strip().rstrip("%").strip()
    try:
        submitted_val = float(submitted)
    except ValueError:
        return {
            "field": "alcohol_content",
            "rule_id": "ALC_PERCENT_MATCH_EXACT",
            "message": f"Could not parse submitted alcohol content '{ctx.form.alcohol_content}'.",
            "ocr_found": f"{extracted_abv}%",
        }

    if abs(extracted_abv - submitted_val) > 0.5:
        return {
            "field": "alcohol_content",
            "rule_id": "ALC_PERCENT_MATCH_EXACT",
            "message": (
                f"Alcohol content mismatch: label shows {extracted_abv}% "
                f"but form declares {submitted_val}%."
            ),
            "ocr_found": f"{extracted_abv}%",
        }

    ctx._ocr_found_abv = f"{extracted_abv}%"
    return None
