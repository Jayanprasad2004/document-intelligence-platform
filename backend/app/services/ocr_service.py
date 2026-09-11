"""
OCR / text-parsing layer.

Dataset finding: none of the "native" PDFs in scope actually have a
text layer (pdffonts shows zero embedded fonts across all Balance
Sheet / P&L / Cash Flow years) -- they are print-to-PDF scans. So
there is no fast "direct text extraction" path to try first; every
PDF page and every image must go through OCR. Keep the direct-text
attempt as a cheap first try (in case a genuinely native PDF is
submitted during evaluation) but always fall back to OCR, don't
assume it will succeed.

Also handles: photographed invoices with skew/rotation and cluttered
backgrounds (see 20251118_000612.jpg in the dataset) -- these get a
document-boundary detection + perspective-correction pass before OCR.
Flat scans (financial statements, receipts) have no separate
background to detect, so that step is skipped automatically and they
fall through to just contrast normalization.
"""
import io

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract
from PIL import Image, ImageOps

from app.core.config import settings
from app.core.exceptions import OCRProcessingError
from app.core.logging_config import logger

RENDER_DPI = 300  # higher than the 150 used for quick visual checks - OCR accuracy needs it
MIN_DOCUMENT_AREA_FRACTION = 0.35  # detected page must fill at least this much of the frame

# Windows in particular rarely has the tesseract binary on PATH after
# installing it -- point pytesseract at it explicitly if configured,
# rather than requiring a PATH edit + terminal restart.
if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def extract_text(file_bytes: bytes, content_type: str) -> list[dict]:
    """
    Returns a list of {"page_number": int, "text": str} blocks, one
    per page (images are always a single "page").
    """
    try:
        if content_type == "application/pdf":
            return _extract_from_pdf(file_bytes)
        return [{"page_number": 1, "text": _ocr_image(Image.open(io.BytesIO(file_bytes)))}]
    except Exception as exc:
        logger.error(f"OCR failed: {exc}")
        raise OCRProcessingError(str(exc)) from exc


def _extract_from_pdf(file_bytes: bytes) -> list[dict]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    blocks = []
    for page_number, page in enumerate(doc, start=1):
        native_text = page.get_text().strip()
        if native_text:
            # Genuinely native PDF page -- use the text layer directly.
            blocks.append({"page_number": page_number, "text": native_text})
            continue

        # No text layer (the common case for this dataset) -- rasterize
        # the page and OCR it.
        pix = page.get_pixmap(dpi=RENDER_DPI)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        blocks.append({"page_number": page_number, "text": _ocr_image(image)})

    return blocks


def _ocr_image(image: Image.Image) -> str:
    image = _preprocess(image)
    return pytesseract.image_to_string(image)


def _preprocess(image: Image.Image) -> Image.Image:
    """
    Preprocessing pipeline, in order:
      1. Correct EXIF orientation (see comment below).
      2. Try to detect the document's own boundary as a quadrilateral
         and perspective-warp it flat, cropping out any background
         (phone-photographed invoices only -- scans have no separate
         background so this step is skipped when no confident
         boundary is found).
      3. Convert to grayscale.

    Deliberately NOT doing custom denoising or thresholding beyond
    grayscale: tested bilateral-filter denoise, adaptive threshold,
    Otsu global threshold, and CLAHE contrast enhancement against the
    dataset's photographed invoice, and every one of them measurably
    *degraded* OCR output versus plain grayscale (e.g. "Shankar" read
    correctly on grayscale, became "Shankgzn"/"Shani" after adaptive
    threshold). Tesseract's own internal binarization already handles
    this better than a hand-tuned threshold step did here -- don't
    re-add thresholding without re-testing against real samples first,
    since it looks like an obvious improvement but measured worse.
    """
    # Phone photos carry an EXIF orientation tag (e.g. "rotate 90") that
    # PIL does NOT auto-apply on open, unlike cv2.imread. Without this,
    # the pixel data stays in the camera sensor's raw orientation and
    # every downstream angle/contour calculation is wrong.
    image = ImageOps.exif_transpose(image)
    cv_image = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)

    warped = _detect_and_warp_document(cv_image)
    working = warped if warped is not None else cv_image

    gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
    return Image.fromarray(gray)


def _detect_and_warp_document(cv_image: np.ndarray):
    """
    Finds the largest convex 4-point contour that covers a large
    majority of the frame, and perspective-warps it to a flat,
    top-down rectangle. Returns None (caller falls back to the
    un-warped image) when no such contour is found -- e.g. flat scans
    with no distinct background, or a photo where the page edge isn't
    clearly separable from the background.
    """
    h, w = cv_image.shape[:2]
    scale = 1000 / max(h, w)
    small = cv2.resize(cv_image, (int(w * scale), int(h * scale)))
    small_area = small.shape[0] * small.shape[1]

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 30, 100)
    edges = cv2.dilate(edges, np.ones((7, 7), np.uint8), iterations=2)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    doc_contour = None
    for c in contours:
        if cv2.contourArea(c) < MIN_DOCUMENT_AREA_FRACTION * small_area:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            doc_contour = approx
            break

    if doc_contour is None:
        return None

    pts = _order_points(doc_contour.astype("float32") / scale)
    (tl, tr, br, bl) = pts
    max_width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    max_height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    if max_width == 0 or max_height == 0:
        return None

    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(pts, dst)
    return cv2.warpPerspective(cv_image, matrix, (max_width, max_height))


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Orders 4 points as top-left, top-right, bottom-right, bottom-left."""
    pts = pts.reshape(4, 2)
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect