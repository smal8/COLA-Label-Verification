"""Distilled spirits validator.

Includes all common rules plus alcohol content checks,
which are mandatory for spirits labels.
"""

from app.validators.base_validator import BaseValidator


class SpiritsValidator(BaseValidator):
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
