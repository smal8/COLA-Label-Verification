"""Validation service — orchestrates the full validation pipeline.

For each submission, the pipeline:
  1. Normalizes OCR text (loose + strict)
  2. Runs extractors once (regex, cached in context)
  3. Builds a ValidationContext
  4. Selects the correct validator by beverage type
  5. Executes rules and collects discrepancies
  6. Gathers OCR evidence for each field (pass or fail)
  7. Returns COMPLIANT or NON_COMPLIANT with details
"""

from app.extractors.extractor_registry import run_all_extractors
from app.models.schemas import FormData
from app.utils.text_normalization import normalize_loose, normalize_strict
from app.validators.base_validator import BaseValidator, ValidationContext
from app.validators.malt_validator import MaltValidator
from app.validators.spirits_validator import SpiritsValidator
from app.validators.wine_validator import WineValidator

VALIDATOR_REGISTRY: dict[str, BaseValidator] = {
    "malt": MaltValidator(),
    "spirits": SpiritsValidator(),
    "wine": WineValidator(),
}


def validate_image(
    beverage_type: str,
    form_data: FormData,
    ocr_text: str,
) -> dict:
    """Run the full validation pipeline.

    Returns:
        Dict with "status", "discrepancies" list, and "ocr_evidence" dict
        mapping field names to what OCR found for that field.
    """
    ocr_loose = normalize_loose(ocr_text)
    ocr_strict = normalize_strict(ocr_text)
    extracted = run_all_extractors(ocr_text)

    ctx = ValidationContext(
        form=form_data,
        ocr_raw=ocr_text,
        ocr_loose=ocr_loose,
        ocr_strict=ocr_strict,
        extracted=extracted,
        beverage_type=beverage_type,
    )

    validator = VALIDATOR_REGISTRY.get(beverage_type)
    if validator is None:
        return {
            "status": "NON_COMPLIANT",
            "discrepancies": [{
                "field": "beverage_type",
                "rule_id": "INVALID_BEVERAGE_TYPE",
                "message": f"Unknown beverage type: {beverage_type}",
            }],
            "ocr_evidence": {},
        }

    discrepancies = validator.validate(ctx)

    has_errors = any(d.get("severity", "error") == "error" for d in discrepancies)
    status = "NON_COMPLIANT" if has_errors else "COMPLIANT"

    # Gather OCR evidence for each field — from failing rules (ocr_found in
    # discrepancy) or from passing rules (stored on ctx by the rule).
    ocr_evidence = {}

    # From discrepancies (failed fields)
    for d in discrepancies:
        if "ocr_found" in d:
            ocr_evidence[d["field"]] = d["ocr_found"]

    # From passing rules (stored on ctx attributes)
    if "brand_name" not in ocr_evidence:
        ocr_evidence["brand_name"] = getattr(ctx, "_ocr_found_brand", None)
    if "class_type_designation" not in ocr_evidence:
        ocr_evidence["class_type_designation"] = getattr(ctx, "_ocr_found_designation", None)
    if "alcohol_content" not in ocr_evidence:
        ocr_evidence["alcohol_content"] = getattr(ctx, "_ocr_found_abv", None)
    if "net_contents" not in ocr_evidence:
        ocr_evidence["net_contents"] = getattr(ctx, "_ocr_found_net_contents", None)
    if "name_address" not in ocr_evidence:
        ocr_evidence["name_address"] = getattr(ctx, "_ocr_found_address", None)
    if "government_warning" not in ocr_evidence:
        ocr_evidence["government_warning"] = getattr(ctx, "_ocr_found_warning", None)

    return {"status": status, "discrepancies": discrepancies, "ocr_evidence": ocr_evidence}
