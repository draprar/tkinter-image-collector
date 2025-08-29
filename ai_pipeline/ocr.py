"""
ocr.py
Simple OCR placeholder for Universal File Collector.

Later: integrate TensorFlow-based OCR model or lightweight alternatives.
"""

from pathlib import Path


def extract_text(image_path: Path) -> str:
    """
    Extract text from an image file.

    Args:
        image_path (Path): Path to the image.

    Returns:
        str: Extracted text (currently dummy).
    """
    # TODO: plug in real OCR later (TensorFlow/Keras model or easyocr)
    return f"[OCR placeholder] Processed: {image_path.name}"
