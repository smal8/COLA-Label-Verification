"""Malt/beer beverage validator.

Alcohol content rules run but are informational — a mismatch is shown
but doesn't affect the overall COMPLIANT status.
"""

from app.validators.base_validator import BaseValidator


class MaltValidator(BaseValidator):
    rule_ids = [
        "OCR_EMPTY_TEXT",
        "BRAND_NAME_CONTAINS",
        "DESIGNATION_CONTAINS",
        "ALC_PERCENT_PRESENT",
        "ALC_PERCENT_MATCH_EXACT",
        "NET_CONTENTS_PRESENT",
        "NAME_ADDRESS_CONTAINS",
        "GOV_WARNING_EXACT",
    ]

    info_rule_ids = {"ALC_PERCENT_PRESENT", "ALC_PERCENT_MATCH_EXACT"}
