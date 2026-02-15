import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.config import templates
from app.models.schemas import FormData
from app.services.ocr_service import OCRService
from app.services.validation_service import validate_image
from app.utils.file_validation import validate_file_type

router = APIRouter()

OCR_EXCERPT_LENGTH = 500

# Thread pool for parallel OCR processing — OCR is CPU-bound so we use
# threads to process multiple images concurrently.
_executor = ThreadPoolExecutor(max_workers=4)


def _ocr_single_image(image_bytes: bytes) -> str:
    """Run OCR on one image. Runs in a thread."""
    return OCRService.extract_text(image_bytes)


@router.get("/")
async def form_page(request: Request):
    """Serve the main label verification form."""
    return templates.TemplateResponse("form.html", {"request": request})


@router.post("/submit")
async def submit_form(
    request: Request,
    beverage_type: str = Form(...),
    brand_name: str = Form(...),
    class_type_designation: str = Form(...),
    net_contents: str = Form(...),
    name_address: str = Form(...),
    alcohol_content: str = Form(...),
    government_warning_expected: str = Form(""),
    images: list[UploadFile] = File(...),
):
    """Handle form submission — OCR runs in parallel, then results are aggregated."""
    form = FormData(
        brand_name=brand_name,
        class_type_designation=class_type_designation,
        net_contents=net_contents,
        name_address=name_address,
        alcohol_content=alcohol_content,
        government_warning_expected=government_warning_expected or None,
    )

    errors = []
    image_data = []

    # Read all image bytes upfront (async I/O), validate file types
    for image_file in images:
        filename = image_file.filename or "unknown"
        if not validate_file_type(filename):
            errors.append(f"Skipped '{filename}': unsupported file type (allowed: PNG, JPG, JPEG)")
            continue
        image_bytes = await image_file.read()
        image_data.append((filename, image_bytes))

    # Run OCR on all images in parallel
    ocr_tasks = []
    if image_data:
        loop = asyncio.get_event_loop()
        ocr_tasks = [
            loop.run_in_executor(_executor, _ocr_single_image, img_bytes)
            for _, img_bytes in image_data
        ]
    ocr_texts = await asyncio.gather(*ocr_tasks) if ocr_tasks else []

    # Build per-image OCR excerpts for display
    per_image_ocr = []
    for (filename, _), ocr_text in zip(image_data, ocr_texts):
        per_image_ocr.append({
            "image_name": filename,
            "ocr_text_excerpt": ocr_text[:OCR_EXCERPT_LENGTH] if ocr_text else "No text detected",
        })

    # Aggregate OCR text from all images and validate once
    combined_ocr = "\n".join(text for text in ocr_texts if text)
    validation_result = validate_image(beverage_type, form, combined_ocr)

    all_discrepancies = validation_result["discrepancies"]
    ocr_evidence = validation_result.get("ocr_evidence", {})

    # Build a lookup: field name -> discrepancy dict
    disc_by_field = {}
    for d in all_discrepancies:
        disc_by_field.setdefault(d["field"], d)

    # Build per-field summary for display
    checked_fields = [
        ("brand_name", "Brand Name", form.brand_name),
        ("class_type_designation", "Class/Type Designation", form.class_type_designation),
        ("alcohol_content", "Alcohol Content", form.alcohol_content),
        ("net_contents", "Net Contents", form.net_contents),
        ("name_address", "Name & Address", form.name_address),
        ("government_warning", "Government Warning", "Standard warning text"),
    ]

    field_results = []
    for field_key, label, value in checked_fields:
        disc = disc_by_field.get(field_key)
        evidence = ocr_evidence.get(field_key, "")
        if disc is None:
            field_results.append({
                "label": label,
                "value": value,
                "status": "matched",
                "message": "Found on label",
                "ocr_found": evidence or "",
            })
        elif disc.get("severity") == "info":
            field_results.append({
                "label": label,
                "value": value,
                "status": "info",
                "message": f"Not found on label — not required for {beverage_type}",
                "ocr_found": evidence or "Not detected",
            })
        else:
            field_results.append({
                "label": label,
                "value": value,
                "status": "error",
                "message": disc["message"],
                "ocr_found": evidence or "Not detected",
            })

    return templates.TemplateResponse("results.html", {
        "request": request,
        "beverage_type": beverage_type,
        "status": validation_result["status"],
        "field_results": field_results,
        "combined_ocr": combined_ocr,
        "per_image_ocr": per_image_ocr,
        "errors": errors,
    })
