"""Unit tests for validation rules using crafted ValidationContext objects."""

import pytest

from app.extractors.extractor_registry import run_all_extractors
from app.models.schemas import FormData
from app.rules.common_rules import (
    brand_name_contains,
    designation_contains,
    gov_warning_exact,
    name_address_contains,
    net_contents_present,
    ocr_empty_text,
)
from app.rules.spirits_rules import alc_percent_match_exact, alc_percent_present
from app.utils.text_normalization import normalize_loose, normalize_strict
from app.validators.base_validator import ValidationContext


def _make_ctx(ocr_text: str, **form_overrides) -> ValidationContext:
    """Helper to build a ValidationContext from OCR text and optional form overrides."""
    defaults = {
        "brand_name": "Test Brand",
        "class_type_designation": "Bourbon Whiskey",
        "net_contents": "750 mL",
        "name_address": "Acme Distilling Company, Louisville KY",
        "alcohol_content": "40",
        "government_warning_expected": None,
    }
    defaults.update(form_overrides)
    form = FormData(**defaults)
    extracted = run_all_extractors(ocr_text)
    return ValidationContext(
        form=form,
        ocr_raw=ocr_text,
        ocr_loose=normalize_loose(ocr_text),
        ocr_strict=normalize_strict(ocr_text),
        extracted=extracted,
        beverage_type="spirits",
    )


class TestOCREmptyText:
    def test_empty_string_fails(self):
        ctx = _make_ctx("")
        result = ocr_empty_text(ctx)
        assert result is not None
        assert result["rule_id"] == "OCR_EMPTY_TEXT"

    def test_normal_text_passes(self):
        ctx = _make_ctx("This is a normal label with enough text to pass")
        assert ocr_empty_text(ctx) is None


class TestBrandNameContains:
    def test_exact_match(self):
        ctx = _make_ctx("Test Brand Bourbon Whiskey 750 mL")
        assert brand_name_contains(ctx) is None

    def test_case_insensitive_match(self):
        ctx = _make_ctx("test brand bourbon whiskey")
        assert brand_name_contains(ctx) is None

    def test_not_found(self):
        ctx = _make_ctx(
            "Completely different label text here",
            brand_name="Jameson Irish Whiskey",
        )
        result = brand_name_contains(ctx)
        assert result is not None
        assert result["field"] == "brand_name"


class TestNetContentsPresent:
    def test_matching_value(self):
        ctx = _make_ctx("Brand Name 750 mL other text", net_contents="750 mL")
        assert net_contents_present(ctx) is None

    def test_mismatch(self):
        ctx = _make_ctx("Brand Name 750 mL other text", net_contents="12 FL OZ")
        result = net_contents_present(ctx)
        assert result is not None
        assert "mismatch" in result["message"].lower() or "not detected" in result["message"].lower()

    def test_not_detected(self):
        ctx = _make_ctx("Brand Name no volume info here", net_contents="750 mL")
        result = net_contents_present(ctx)
        assert result is not None
        assert result["rule_id"] == "NET_CONTENTS_PRESENT"


class TestAlcPercentPresent:
    def test_abv_detected(self):
        ctx = _make_ctx("40% ALC/VOL some text")
        assert alc_percent_present(ctx) is None

    def test_abv_not_detected(self):
        ctx = _make_ctx("No alcohol info here")
        result = alc_percent_present(ctx)
        assert result is not None
        assert result["field"] == "alcohol_content"


class TestAlcPercentMatchExact:
    def test_matching_abv(self):
        ctx = _make_ctx("40% ALC/VOL", alcohol_content="40")
        # alc_percent_present must run first to set ctx attributes
        alc_percent_present(ctx)
        assert alc_percent_match_exact(ctx) is None

    def test_mismatched_abv(self):
        ctx = _make_ctx("45% ALC/VOL", alcohol_content="40")
        result = alc_percent_match_exact(ctx)
        assert result is not None
        assert "mismatch" in result["message"].lower()


class TestGovWarningExact:
    def test_full_warning_passes(self):
        warning_text = (
            "GOVERNMENT WARNING: (1) According to the Surgeon General, "
            "women should not drink alcoholic beverages during pregnancy because of "
            "the risk of birth defects. (2) Consumption of alcoholic beverages impairs "
            "your ability to drive a car or operate machinery, and may cause health problems."
        )
        ctx = _make_ctx(f"Brand Name 750 mL {warning_text}")
        assert gov_warning_exact(ctx) is None

    def test_missing_warning_fails(self):
        ctx = _make_ctx("Brand Name 750 mL no warning here")
        result = gov_warning_exact(ctx)
        assert result is not None
        assert result["field"] == "government_warning"


class TestNameAddressContains:
    def test_matching_tokens(self):
        ctx = _make_ctx(
            "Produced by Acme Distilling Company Louisville KY",
            name_address="Acme Distilling Company, Louisville KY",
        )
        assert name_address_contains(ctx) is None

    def test_no_match(self):
        ctx = _make_ctx(
            "Some completely unrelated text on a label",
            name_address="Acme Distilling Company, Louisville KY",
        )
        result = name_address_contains(ctx)
        assert result is not None
        assert result["field"] == "name_address"
