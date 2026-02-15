"""Integration-level unit tests for the validation service pipeline."""

import pytest

from app.models.schemas import FormData
from app.services.validation_service import validate_image


def _make_form(**overrides) -> FormData:
    defaults = {
        "brand_name": "Old Tom Distillery",
        "class_type_designation": "Kentucky Straight Bourbon Whiskey",
        "net_contents": "750 mL",
        "name_address": "Old Tom Distilling Co, Bardstown KY 40004",
        "alcohol_content": "45",
        "government_warning_expected": None,
    }
    defaults.update(overrides)
    return FormData(**defaults)


FULL_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, "
    "women should not drink alcoholic beverages during pregnancy because of "
    "the risk of birth defects. (2) Consumption of alcoholic beverages impairs "
    "your ability to drive a car or operate machinery, and may cause health problems."
)

COMPLIANT_OCR = (
    "OLD TOM DISTILLERY\n"
    "Kentucky Straight Bourbon Whiskey\n"
    "45% ALC/VOL (90 PROOF)\n"
    "750 mL\n"
    "Distilled and Bottled by Old Tom Distilling Co, Bardstown KY 40004\n"
    f"{FULL_WARNING}"
)


class TestValidationPipeline:
    def test_fully_compliant_spirits(self):
        form = _make_form()
        result = validate_image("spirits", form, COMPLIANT_OCR)
        assert result["status"] == "COMPLIANT"
        assert len([d for d in result["discrepancies"] if d.get("severity") == "error"]) == 0

    def test_empty_ocr_is_non_compliant(self):
        form = _make_form()
        result = validate_image("spirits", form, "")
        assert result["status"] == "NON_COMPLIANT"
        rule_ids = [d["rule_id"] for d in result["discrepancies"]]
        assert "OCR_EMPTY_TEXT" in rule_ids

    def test_missing_brand_name(self):
        ocr = COMPLIANT_OCR.replace("OLD TOM DISTILLERY", "XYZ CORP BRAND")
        ocr = ocr.replace("Old Tom Distilling Co", "XYZ Corp")
        form = _make_form()
        result = validate_image("spirits", form, ocr)
        assert result["status"] == "NON_COMPLIANT"
        rule_ids = [d["rule_id"] for d in result["discrepancies"]]
        assert "BRAND_NAME_CONTAINS" in rule_ids

    def test_abv_mismatch_spirits_is_error(self):
        ocr = COMPLIANT_OCR.replace("45%", "50%").replace("90 PROOF", "100 PROOF")
        form = _make_form()
        result = validate_image("spirits", form, ocr)
        assert result["status"] == "NON_COMPLIANT"
        abv_disc = [d for d in result["discrepancies"] if d["field"] == "alcohol_content"]
        assert any(d.get("severity") == "error" for d in abv_disc)

    def test_abv_mismatch_malt_is_info(self):
        ocr = COMPLIANT_OCR.replace("45%", "50%").replace("90 PROOF", "100 PROOF")
        form = _make_form()
        result = validate_image("malt", form, ocr)
        # ABV mismatch should be info, not error — so overall can still be COMPLIANT
        abv_disc = [d for d in result["discrepancies"] if d["field"] == "alcohol_content"]
        assert all(d.get("severity") == "info" for d in abv_disc)

    def test_invalid_beverage_type(self):
        form = _make_form()
        result = validate_image("sake", form, COMPLIANT_OCR)
        assert result["status"] == "NON_COMPLIANT"

    def test_ocr_evidence_populated(self):
        form = _make_form()
        result = validate_image("spirits", form, COMPLIANT_OCR)
        evidence = result.get("ocr_evidence", {})
        # At least some fields should have evidence
        assert any(v is not None for v in evidence.values())
