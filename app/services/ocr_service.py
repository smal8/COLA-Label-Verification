import io
import numpy as np
from PIL import Image, ImageFilter
from rapidocr_onnxruntime import RapidOCR


# Maximum width/height before resizing — larger images are scaled down
# to speed up OCR with minimal accuracy loss.
MAX_IMAGE_DIMENSION = 1024

# Rotations to try — 0 for normal text, 90 for vertical text on labels
ROTATIONS = [0, 90]


class OCRService:
    """Wraps RapidOCR to extract text from label images.

    RapidOCR uses PaddleOCR's neural network models but runs them through
    ONNX Runtime — more accurate than Tesseract, lighter than full PaddlePaddle.

    The engine is loaded once and reused across requests for performance.
    """

    _instance: RapidOCR | None = None

    @classmethod
    def _get_engine(cls) -> RapidOCR:
        """Lazy-initialize the RapidOCR engine on first use."""
        if cls._instance is None:
            cls._instance = RapidOCR()
        return cls._instance

    @staticmethod
    def _preprocess(image: Image.Image) -> Image.Image:
        """Resize and sharpen an image for OCR."""
        image = image.convert("RGB")
        w, h = image.size
        if max(w, h) > MAX_IMAGE_DIMENSION:
            ratio = MAX_IMAGE_DIMENSION / max(w, h)
            image = image.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        image = image.filter(ImageFilter.SHARPEN)
        return image

    @staticmethod
    def _ocr_image(image: Image.Image) -> str:
        """Run OCR on a preprocessed PIL image."""
        image_np = np.array(image)
        engine = OCRService._get_engine()
        result, _ = engine(image_np)
        if not result:
            return ""
        lines = [detection[1] for detection in result]
        return "\n".join(lines)

    @staticmethod
    def extract_text(image_bytes: bytes) -> str:
        """Run OCR on raw image bytes at multiple rotations and aggregate.

        Tries 0, 90, 180, 270 degree rotations to catch vertical/sideways
        text (common on bottle labels). All unique text is combined.

        Args:
            image_bytes: Raw bytes of a PNG or JPEG image.

        Returns:
            Aggregated text from all rotations, deduplicated by line.
        """
        image = Image.open(io.BytesIO(image_bytes))
        image = OCRService._preprocess(image)

        all_lines = []
        seen = set()

        for angle in ROTATIONS:
            if angle == 0:
                rotated = image
            else:
                rotated = image.rotate(angle, expand=True)

            text = OCRService._ocr_image(rotated)
            if text:
                for line in text.split("\n"):
                    line_stripped = line.strip()
                    # Deduplicate — same text from different rotations
                    line_lower = line_stripped.lower()
                    if line_lower and line_lower not in seen:
                        seen.add(line_lower)
                        all_lines.append(line_stripped)

        return "\n".join(all_lines)
