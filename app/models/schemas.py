from typing import Optional

from pydantic import BaseModel


class FormData(BaseModel):
    """Structured form input submitted by the applicant.

    These fields represent what the applicant declared on their label.
    The system validates that these values actually appear in the label images via OCR.
    """

    brand_name: str
    class_type_designation: str
    net_contents: str
    name_address: str

    alcohol_content: str
    government_warning_expected: Optional[str] = None


class Discrepancy(BaseModel):
    """A single validation finding.

    Each discrepancy identifies which field failed, which rule caught it,
    a human-readable explanation, and a severity level.

    severity:
      - "error" — required for this beverage type, affects COMPLIANT status
      - "info"  — not required for this beverage type, shown but doesn't fail
    """

    field: str       # e.g., "brand_name", "government_warning"
    rule_id: str     # e.g., "BRAND_NAME_CONTAINS", "GOV_WARNING_EXACT"
    message: str     # e.g., "Brand name not found or does not match."
    severity: str = "error"  # "error" or "info"


class ImageOCRResult(BaseModel):
    """OCR output for a single uploaded image — kept for traceability."""

    image_name: str
    ocr_text_excerpt: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Top-level response from POST /analyze.

    When multiple images are uploaded, OCR text is aggregated across all
    images and validation runs once on the combined text.
    """

    beverage_type: str
    status: str  # "COMPLIANT" or "NON_COMPLIANT"
    discrepancies: list[Discrepancy] = []
    image_results: list[ImageOCRResult] = []
