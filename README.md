# AI-Powered Alcohol Label Verification

A standalone prototype that validates alcohol beverage label images against structured application form data using OCR. Designed to assist TTB compliance analysts by automating the routine "matching" checks they perform on ~150,000 label applications per year.

**Live Demo:** http://44.230.59.49.nip.io:8000

## What It Does

1. User selects a beverage type (Beer/Malt, Distilled Spirits, or Wine)
2. User fills in the declared label fields (brand name, class/type, ABV, net contents, name/address)
3. User uploads one or more label images (front, back, etc.)
4. System extracts text from all images via OCR, aggregates the results
5. System validates each declared field against the extracted text
6. System displays a field-by-field compliance report showing what was submitted vs. what OCR found

## Quick Start

### Docker (Recommended)

```bash
docker build -t label-verification .
docker run -p 8000:8000 label-verification

# App: http://localhost:8000
# Health: http://localhost:8000/health
```

### Local Development

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Run Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

## Architecture

```
┌─────────────┐     HTTP      ┌──────────────────────────────────────────────┐
│   Browser   │◄────────────►│  Docker Container                            │
│             │               │  ┌──────────────────────────────────────┐    │
│  Form +     │               │  │  Uvicorn (ASGI Server)               │    │
│  File Upload│               │  │  ┌──────────────────────────────┐    │    │
│             │               │  │  │  FastAPI Application          │    │    │
│  Results    │               │  │  │                               │    │    │
│  Display    │               │  │  │  Routes ─► OCR Service        │    │    │
│             │               │  │  │         ─► Validation Service │    │    │
│             │               │  │  │              ├─ Extractors    │    │    │
│             │               │  │  │              ├─ Validators    │    │    │
│             │               │  │  │              └─ Rules         │    │    │
└─────────────┘               │  │  └──────────────────────────────┘    │    │
                              │  └──────────────────────────────────────┘    │
                              │  RapidOCR (ONNX Runtime) ← neural net OCR   │
                              └──────────────────────────────────────────────┘
```

The system is fully stateless — no database, no file persistence, no external API calls. Images are processed in memory and discarded. The entire application runs inside a single Docker container.

## Design Decisions

### OCR Engine: RapidOCR over Tesseract

The LLD specified Tesseract, but testing showed it struggled with stylized label fonts, curved text, and low-contrast backgrounds. RapidOCR uses PaddleOCR's neural network models through ONNX Runtime — significantly more accurate on real-world label images while remaining lightweight enough to run without GPU. No external API calls needed.

### Multi-Rotation OCR

Label images often contain vertical or sideways text (especially on bottle sides). The OCR service processes each image at 0 and 90 degree rotations, deduplicates the results, and aggregates all text. This catches text that would be missed in a single-pass scan.

### Multi-Image Aggregation

Instead of validating each image independently, the system aggregates OCR text from all uploaded images before running validation once. This reflects real-world usage where front and back labels contain different required fields (e.g., government warning is typically on the back).

### Fuzzy Matching for OCR Tolerance

OCR frequently introduces character-level errors (`l`→`1`, `O`→`0`, `rn`→`m`). The system uses:
- **Loose normalization**: lowercase, strip punctuation, collapse whitespace
- **Fuzzy token matching**: allows 1-character edit distance for words 5+ characters; requires exact match for shorter words to prevent false positives
- **Regex-based extraction**: handles format variations in ABV, net contents, and government warning

### Strategy Pattern for Beverage Types

Each beverage type has its own validator with a specific rule list. Rules are shared across validators via a registry — a rule is written once and reused. The `info_rule_ids` mechanism lets a rule run for all beverage types but only count as an error where it's legally required (e.g., ABV is mandatory for spirits, informational for beer/wine).

### Severity System (Error vs Info)

All fields are validated for all beverage types, but discrepancies are categorized:
- **error**: required for this beverage type, affects COMPLIANT/NON_COMPLIANT status
- **info**: shown to the analyst but doesn't fail the submission (e.g., ABV not detected on a beer label)

## Validation Rules

| Rule ID | Field | Description |
|---------|-------|-------------|
| `OCR_EMPTY_TEXT` | ocr | Fails if OCR produces no usable text |
| `BRAND_NAME_CONTAINS` | brand_name | Fuzzy check that brand name appears in OCR |
| `DESIGNATION_CONTAINS` | class_type_designation | Fuzzy check that class/type appears in OCR |
| `ALC_PERCENT_PRESENT` | alcohol_content | Checks ABV pattern detected on label |
| `ALC_PERCENT_MATCH_EXACT` | alcohol_content | Checks detected ABV matches submitted value |
| `NET_CONTENTS_PRESENT` | net_contents | Checks volume statement present and matches |
| `NAME_ADDRESS_CONTAINS` | name_address | Token-level match of producer name/address |
| `GOV_WARNING_EXACT` | government_warning | Checks "GOVERNMENT WARNING" header + key phrases |

## Project Structure

```
label-verification/
├── app/
│   ├── main.py                     # FastAPI app, static mount, router registration
│   ├── config.py                   # Template directory config
│   ├── routes/
│   │   ├── health.py               # GET /health
│   │   ├── analyze.py              # POST /analyze (JSON API)
│   │   └── pages.py                # GET / (form) + POST /submit (UI flow)
│   ├── models/
│   │   └── schemas.py              # Pydantic models (FormData, Discrepancy, etc.)
│   ├── services/
│   │   ├── ocr_service.py          # RapidOCR wrapper with rotation + preprocessing
│   │   └── validation_service.py   # Orchestrates the full validation pipeline
│   ├── validators/
│   │   ├── base_validator.py       # Shared interface + severity logic
│   │   ├── malt_validator.py       # Beer/malt rule set (ABV = info)
│   │   ├── spirits_validator.py    # Spirits rule set (all mandatory)
│   │   └── wine_validator.py       # Wine rule set (ABV = info)
│   ├── rules/
│   │   ├── rule_registry.py        # Maps rule ID strings → functions
│   │   ├── common_rules.py         # Brand, designation, net contents, address, gov warning
│   │   └── spirits_rules.py        # ABV presence + exact match
│   ├── extractors/
│   │   ├── extractor_registry.py   # Runs all extractors, caches results
│   │   └── common_extractors.py    # Regex extraction: ABV, net contents, gov warning
│   └── utils/
│       ├── text_normalization.py   # Loose/strict/warning normalization + fuzzy matching
│       ├── file_validation.py      # Image file type validation
│       └── gov_warning_text.py     # Canonical warning text constant
├── templates/
│   ├── form.html                   # Beverage selection + field input + image upload
│   └── results.html                # Field-by-field verification results
├── static/
│   └── style.css                   # UI styling
├── tests/
│   └── unit/
│       ├── test_text_normalization.py   # Normalization + fuzzy matching tests
│       ├── test_extractors.py           # Regex extractor tests
│       ├── test_rules.py                # Individual rule tests with crafted contexts
│       └── test_validation_service.py   # End-to-end pipeline tests
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API

### POST /analyze

Programmatic JSON API for validation.

**Request** (multipart/form-data):
| Field | Type | Description |
|-------|------|-------------|
| `beverage_type` | string | `malt`, `spirits`, or `wine` |
| `form_data` | JSON string | `{"brand_name": "...", "class_type_designation": "...", ...}` |
| `images` | file(s) | PNG, JPG, or JPEG label images |

**Response** (JSON):
```json
{
  "beverage_type": "spirits",
  "status": "COMPLIANT",
  "discrepancies": [],
  "image_results": [
    {"image_name": "front.jpg", "ocr_text_excerpt": "..."}
  ]
}
```

### GET /health

Returns system status and OCR engine availability.

## Assumptions and Scope

### Prototype Scope

This prototype demonstrates feasibility and architectural direction. It is intentionally constrained:

- **Standalone operation** — no integration with COLA or other internal agency systems
- **Stateless processing** — uploaded images are processed in memory and discarded; no persistent storage
- **Regex-based validation only** — uses regular expressions and substring matching, not ML-based semantic understanding
- **Common mandatory fields only** — validates the fields required across all beverage types (brand name, class/type, net contents, name/address, government warning, alcohol content)

### What's Not Covered (Production Scope)

The following would be needed for production deployment:

- **Authentication and authorization** — role-based access for compliance analysts
- **COLA integration** — form data would come from the existing COLA system rather than manual entry
- **Persistent storage** — submission history, audit trails, document retention policies
- **Layout/geometry checks** — "same field of vision" requirement, bold styling detection (OCR cannot reliably detect text styling)
- **Conditional rules** — sulfites disclosure, Yellow #5, country of origin for imports, formula requirements
- **Batch processing** — processing 200-300 applications from large importers in a single submission
- **FedRAMP/security compliance** — federal security certification, PII handling, restricted network deployment

### Known Limitations

1. **OCR accuracy depends on image quality** — blurry, low-contrast, or heavily stylized labels may produce poor OCR results. The system handles this gracefully (marks as non-compliant with `OCR_EMPTY_TEXT`) but cannot fix bad input.

2. **Government warning check is forgiving** — rather than requiring exact character-by-character match (which OCR makes nearly impossible), the system checks for the "GOVERNMENT WARNING" header in caps and the presence of key warning phrases (surgeon, general, pregnancy, birth defects, impairs, machinery, health). This is intentionally permissive to avoid false negatives from OCR noise.

3. **Bold styling cannot be verified** — the government warning must appear in bold on the physical label, but OCR extracts only text content, not formatting. This limitation is inherent to all text-extraction approaches.

4. **Name/address matching is token-based** — checks that key words from the submitted name/address appear in the OCR text. This is effective for catching completely wrong or missing information but won't catch subtle differences in address formatting.

5. **No layout awareness** — the system validates text presence, not spatial positioning. It cannot verify that required elements are in the correct location or "same field of vision."

### Production Vision

In production, this system would evolve into a backend validation microservice:
- Phase 1 (Assisted Review): All applications reviewed by analysts with system providing automated pre-screening
- Phase 2 (Conditional Auto-Approval): High-confidence validations auto-approved; edge cases flagged for human review

The human-in-the-loop model ensures regulatory accuracy while the automation handles the routine matching work that currently occupies ~50% of analyst time.

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.11 | Rich ML/OCR ecosystem, fast prototyping |
| Web Framework | FastAPI | Async support, automatic validation, OpenAPI docs |
| HTTP Server | Uvicorn | Lightweight ASGI server |
| OCR Engine | RapidOCR (ONNX Runtime) | Neural net accuracy without GPU dependency |
| Image Processing | Pillow | Preprocessing before OCR |
| Templating | Jinja2 | Server-rendered HTML for clean analyst-facing UI |
| Container | Docker | Portable, reproducible deployment |
| Hosting | AWS EC2 (t3.large) | Prototype hosting; cloud-agnostic design |

## Deployment

The prototype is deployed on AWS EC2 with Docker:

```bash
# Build and run
docker build -t label-verification .
docker run -d -p 8000:8000 --name label-verification --restart unless-stopped label-verification
```

The system requires no outbound internet access, no external APIs, and no cloud-specific services. It can run on any Docker-compatible host.
