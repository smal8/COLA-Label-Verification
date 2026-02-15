import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.models.schemas import AnalyzeResponse, Discrepancy, FormData, ImageOCRResult
from app.services.ocr_service import OCRService
from app.services.validation_service import validate_image
from app.utils.file_validation import validate_file_type

router = APIRouter()

VALID_BEVERAGE_TYPES = {"malt", "spirits", "wine"}
OCR_EXCERPT_LENGTH = 500

# Thread pool for parallel OCR — process multiple label images concurrently
_executor = ThreadPoolExecutor(max_workers=4)


def _ocr_single_image(image_bytes: bytes) -> str:
    """Run OCR on one image. Runs in a thread."""
    return OCRService.extract_text(image_bytes)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_labels(
    beverage_type: str = Form(...),
    form_data: str = Form(...),
    images: list[UploadFile] = File(...),
):
    """Analyze uploaded label images against structured form data.

    OCR runs on each image in parallel, then text is aggregated across all
    images and validation runs once on the combined text.
    """
    if beverage_type not in VALID_BEVERAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid beverage_type '{beverage_type}'. Must be one of: {', '.join(VALID_BEVERAGE_TYPES)}",
        )

    try:
        parsed_form_data = json.loads(form_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="form_data is not valid JSON")

    try:
        form = FormData(**parsed_form_data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")

    # Read all image bytes and validate file types
    image_data = []
    for image_file in images:
        if not validate_file_type(image_file.filename or ""):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type for '{image_file.filename}'. Allowed: PNG, JPG, JPEG",
            )
        image_bytes = await image_file.read()
        image_data.append((image_file.filename or "unknown", image_bytes))

    # Run OCR on all images in parallel
    loop = asyncio.get_event_loop()
    ocr_tasks = [
        loop.run_in_executor(_executor, _ocr_single_image, img_bytes)
        for _, img_bytes in image_data
    ]
    ocr_texts = await asyncio.gather(*ocr_tasks)

    # Build per-image OCR excerpts for traceability
    image_results = []
    for (filename, _), ocr_text in zip(image_data, ocr_texts):
        image_results.append(ImageOCRResult(
            image_name=filename,
            ocr_text_excerpt=ocr_text[:OCR_EXCERPT_LENGTH] if ocr_text else None,
        ))

    # Aggregate OCR text from all images, then validate once
    combined_ocr = "\n".join(text for text in ocr_texts if text)
    validation_result = validate_image(beverage_type, form, combined_ocr)

    return AnalyzeResponse(
        beverage_type=beverage_type,
        status=validation_result["status"],
        discrepancies=[Discrepancy(**d) for d in validation_result["discrepancies"]],
        image_results=image_results,
    )
