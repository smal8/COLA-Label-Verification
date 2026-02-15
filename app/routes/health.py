from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    """Health endpoint — confirms FastAPI is running and RapidOCR is importable."""
    ocr_status = _check_ocr()
    return {
        "status": "healthy",
        "ocr_engine": ocr_status,
    }


def _check_ocr() -> dict:
    """Try importing RapidOCR to verify it's installed and loadable."""
    try:
        from rapidocr_onnxruntime import RapidOCR
        return {"available": True, "engine": "RapidOCR (ONNX Runtime)"}
    except ImportError as e:
        return {"available": False, "engine": "RapidOCR", "error": str(e)}
