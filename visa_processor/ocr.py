"""OCR for passport images / PDFs using Tesseract."""
from pathlib import Path

from . import config


def ocr_file(path: str) -> str:
    # imported lazily so the rest of the package (and the tests) work without system OCR libs
    import pytesseract
    from PIL import Image, ImageOps

    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        images = [Image.open(path)]
    else:
        from pdf2image import convert_from_path

        images = convert_from_path(path, dpi=300, last_page=config.MAX_PDF_PAGES)

    pages = []
    for i, img in enumerate(images, start=1):
        img = ImageOps.autocontrast(ImageOps.grayscale(img))
        pages.append(f"Page {i}:\n{pytesseract.image_to_string(img, lang='eng')}")
    return "\n".join(pages)
