"""Base validator — defines the shared validation interface and pipeline.

Beverage-specific validators inherit from this and provide their own
rule list. The base class handles executing rules in order and collecting
discrepancies.
"""

from app.rules.rule_registry import RULE_REGISTRY


class ValidationContext:
    """Shared context passed to every rule during validation of a single image.

    Attributes:
        form: The structured form data submitted by the applicant.
        ocr_raw: Raw OCR text as returned by Tesseract.
        ocr_loose: Loose-normalized OCR text (lowercased, punctuation stripped).
        ocr_strict: Strict-normalized OCR text (whitespace collapsed, case preserved).
        extracted: Dict of cached extractor outputs (ABV, net contents, warning flags).
    """

    def __init__(self, form, ocr_raw: str, ocr_loose: str, ocr_strict: str, extracted: dict, beverage_type: str = ""):
        self.form = form
        self.ocr_raw = ocr_raw
        self.ocr_loose = ocr_loose
        self.ocr_strict = ocr_strict
        self.extracted = extracted
        self.beverage_type = beverage_type


class BaseValidator:
    """Base class for beverage-specific validators.

    Subclasses override `rule_ids` to define which rules apply.
    The validate() method executes each rule in order and collects failures.
    """

    # Subclasses set this to their list of rule IDs (e.g., ["BRAND_NAME_CONTAINS", ...])
    rule_ids: list[str] = []

    # Rules that are informational for this beverage type — they still run
    # and show findings, but don't affect COMPLIANT/NON_COMPLIANT status.
    info_rule_ids: set[str] = set()

    def validate(self, ctx: ValidationContext) -> list[dict]:
        """Run all rules for this beverage type and return discrepancies.

        Rules execute in order. If OCR_EMPTY_TEXT fires, remaining rules
        are skipped since there's no text to validate against.

        Each discrepancy gets a "severity" field:
          - "error" for required rules (affects overall status)
          - "info" for informational rules (shown but doesn't fail)

        Returns:
            List of discrepancy dicts.
        """
        discrepancies = []

        for rule_id in self.rule_ids:
            rule_fn = RULE_REGISTRY.get(rule_id)
            if rule_fn is None:
                continue

            result = rule_fn(ctx)
            if result is not None:
                result["severity"] = "info" if rule_id in self.info_rule_ids else "error"
                discrepancies.append(result)

                # If OCR produced no text, skip remaining rules — they'd all fail
                if rule_id == "OCR_EMPTY_TEXT":
                    break

        return discrepancies
