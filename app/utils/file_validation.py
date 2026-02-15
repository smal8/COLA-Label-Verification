# Allowed image extensions for label uploads.
# Only common raster formats that Tesseract/Pillow handle well.
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def validate_file_type(filename: str) -> bool:
    """Check that the uploaded file has an allowed image extension.

    Args:
        filename: Original filename from the upload (e.g., "label_front.jpg").

    Returns:
        True if the extension is in ALLOWED_EXTENSIONS, False otherwise.
    """
    # Extract extension and lowercase it so "Label.JPG" is accepted
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXTENSIONS
