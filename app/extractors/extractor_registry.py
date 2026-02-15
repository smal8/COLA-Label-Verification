from app.extractors.common_extractors import (
    extract_abv,
    extract_gov_warning,
    extract_net_contents,
)


def run_all_extractors(ocr_text: str) -> dict:
    """Run every registered extractor once on the OCR text and merge results.

    This function is called once per image. The returned dict is cached in
    ValidationContext.extracted so that rules can read pre-computed values
    instead of re-running regex patterns themselves.

    Returns a flat dict combining outputs from all extractors, e.g.:
        {
            "abv_percent": 40.0,
            "alcohol_label_present": True,
            "net_contents_candidates": ["750 mL"],
            "gov_warning_header_present": True,
            "gov_warning_body_present": True,
            "gov_warning_canonical_match": True,
        }
    """
    results = {}
    results.update(extract_abv(ocr_text))
    results.update(extract_net_contents(ocr_text))
    results.update(extract_gov_warning(ocr_text))
    return results
