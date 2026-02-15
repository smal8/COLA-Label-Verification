"""Unit tests for regex-based extractors."""

import pytest

from app.extractors.common_extractors import extract_abv, extract_gov_warning, extract_net_contents


class TestExtractABV:
    def test_standard_format(self):
        result = extract_abv("40% ALC/VOL")
        assert result["abv_percent"] == 40.0
        assert result["alcohol_label_present"] is True

    def test_decimal_abv(self):
        result = extract_abv("12.5% ALC/VOL")
        assert result["abv_percent"] == 12.5

    def test_no_space_before_alc(self):
        result = extract_abv("45%ALC/VOL")
        assert result["abv_percent"] == 45.0

    def test_proof_derivation(self):
        result = extract_abv("90 PROOF")
        assert result["abv_percent"] == 45.0

    def test_no_abv_found(self):
        result = extract_abv("This label has no alcohol information")
        assert result["abv_percent"] is None
        assert result["alcohol_label_present"] is False

    def test_alc_prefix_format(self):
        result = extract_abv("ALC. 40% BY VOL.")
        assert result["abv_percent"] == 40.0


class TestExtractNetContents:
    def test_ml(self):
        result = extract_net_contents("750 mL")
        assert len(result["net_contents_candidates"]) >= 1
        assert any("750" in c for c in result["net_contents_candidates"])

    def test_fl_oz(self):
        result = extract_net_contents("12 FL OZ")
        assert len(result["net_contents_candidates"]) >= 1

    def test_liters(self):
        result = extract_net_contents("1.75 L")
        assert len(result["net_contents_candidates"]) >= 1

    def test_no_contents_found(self):
        result = extract_net_contents("no volume here")
        assert result["net_contents_candidates"] == []


class TestExtractGovWarning:
    def test_full_warning_present(self):
        text = (
            "GOVERNMENT WARNING: (1) According to the Surgeon General, "
            "women should not drink alcoholic beverages during pregnancy because of "
            "the risk of birth defects. (2) Consumption of alcoholic beverages impairs "
            "your ability to drive a car or operate machinery, and may cause health problems."
        )
        result = extract_gov_warning(text)
        assert result["gov_warning_header_present"] is True
        assert result["gov_warning_canonical_match"] is True

    def test_header_no_space(self):
        # OCR sometimes merges "GOVERNMENT" and "WARNING"
        result = extract_gov_warning("GOVERNMENTWARNING some body text")
        assert result["gov_warning_header_present"] is True

    def test_no_warning(self):
        result = extract_gov_warning("Just a regular label with no warning")
        assert result["gov_warning_header_present"] is False
        assert result["gov_warning_canonical_match"] is False
