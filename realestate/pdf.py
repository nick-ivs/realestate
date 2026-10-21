"""Fill a flat (non-fillable) PDF by drawing text over the original page.

The original page is kept byte-for-byte as content; the values are drawn on a
transparent layer merged on top, so the result looks exactly like the source
form with the blanks filled in.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

FONT = "Helvetica"
FONT_SIZE = 10.0
MIN_FONT_SIZE = 6.5
INK = (0.05, 0.10, 0.30)  # dark navy: reads as filled-in, prints like black


@dataclass(frozen=True)
class Field:
    """A blank on the form.

    Coordinates are PDF points measured from the TOP-left of the page (the way
    a PDF inspector shows them), which keeps the layout easy to check against
    the form: ``baseline`` is where the text sits, ``x0``..``x1`` the usable width.
    """

    name: str
    label: str
    x0: float
    x1: float
    baseline: float
    page: int = 0


def fit_font_size(text: str, width: float) -> float | None:
    """Largest size, down to MIN_FONT_SIZE, at which ``text`` fits ``width``."""
    size = FONT_SIZE
    while size >= MIN_FONT_SIZE:
        if stringWidth(text, FONT, size) <= width:
            return size
        size -= 0.25
    return None


def overflowing(fields: list[Field], values: dict[str, str]) -> list[str]:
    """Describe each value that is too long for its blank, even at the smallest size."""
    return [
        f"{f.label}: \"{values[f.name].strip()}\" is too long for the space on the form"
        for f in fields
        if values.get(f.name, "").strip() and fit_font_size(values[f.name].strip(), f.x1 - f.x0) is None
    ]


def fill(template: str, fields: list[Field], values: dict[str, str]) -> tuple[bytes, list[str]]:
    """Draw ``values`` into ``fields`` on ``template``.

    Returns the filled PDF and a list of problems (values too long to fit).
    """
    reader = PdfReader(template)
    if reader.is_encrypted:
        reader.decrypt("")
    problems: list[str] = []
    writer = PdfWriter()

    for page_no, page in enumerate(reader.pages):
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(width, height))
        c.setFillColorRGB(*INK)
        for f in fields:
            text = values.get(f.name, "").strip()
            if f.page != page_no or not text:
                continue
            available = f.x1 - f.x0
            size = fit_font_size(text, available)
            if size is None:
                problems.append(f"{f.label}: \"{text}\" is too long for the space on the form")
                size = MIN_FONT_SIZE
            c.setFont(FONT, size)
            c.drawString(f.x0, height - f.baseline, text)
        c.save()
        overlay = PdfReader(io.BytesIO(buf.getvalue())).pages[0]
        writer.add_page(page).merge_page(overlay)

    writer.add_metadata({"/Title": reader.metadata.title if reader.metadata and reader.metadata.title else "Filled form"})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue(), problems
