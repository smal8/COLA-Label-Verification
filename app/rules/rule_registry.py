"""Rule registry — central lookup of all available validation rules by ID.

Rules are registered here so validators can reference them by ID string
rather than importing functions directly. This makes it easy to add new
rules without modifying validator code.
"""

from app.rules.common_rules import (
    brand_name_contains,
    designation_contains,
    gov_warning_exact,
    name_address_contains,
    net_contents_present,
    ocr_empty_text,
)
from app.rules.spirits_rules import alc_percent_match_exact, alc_percent_present

# Maps rule ID strings to their implementation functions.
# Each function takes a ValidationContext and returns None (pass) or a Discrepancy dict (fail).
RULE_REGISTRY: dict[str, callable] = {
    "OCR_EMPTY_TEXT": ocr_empty_text,
    "BRAND_NAME_CONTAINS": brand_name_contains,
    "DESIGNATION_CONTAINS": designation_contains,
    "NET_CONTENTS_PRESENT": net_contents_present,
    "NAME_ADDRESS_CONTAINS": name_address_contains,
    "GOV_WARNING_EXACT": gov_warning_exact,
    "ALC_PERCENT_PRESENT": alc_percent_present,
    "ALC_PERCENT_MATCH_EXACT": alc_percent_match_exact,
}
