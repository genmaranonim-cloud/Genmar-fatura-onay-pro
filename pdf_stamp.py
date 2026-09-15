from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

STAMP_KEY = "/GenmarOnayDamgasi"


def stamp_pdf(source: str | Path, target: str | Path, approver: str, note: str = "") -> None:
    reader = PdfReader(str(source))
    if not reader.pages:
        raise ValueError("PDF sayfa içermiyor.")
    first = reader.pages[0]
    width, height = float(first.mediabox.width), float(first.mediabox.height)
    overlay_bytes = BytesIO()
    c = canvas.Canvas(overlay_bytes, pagesize=(width, height))
    c.setStrokeColor(HexColor("#B91C1C"))
    c.setFillColor(HexColor("#B91C1C"))
    c.setLineWidth(2)
    x, y, w, h = 32, 30, min(260, width - 64), 92
    c.roundRect(x, y, w, h, 7, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(x + w / 2, y + h - 23, "ONAYLANDI")
    c.setFont("Helvetica", 8)
    c.drawString(x + 10, y + h - 43, f"Onaylayan: {approver[:45]}")
    c.drawString(x + 10, y + h - 57, f"Tarih: {datetime.now():%d.%m.%Y %H:%M}")
    if note:
        c.drawString(x + 10, y + h - 72, f"Not: {note[:54]}")
    c.save()
    overlay_bytes.seek(0)
    first.merge_page(PdfReader(overlay_bytes).pages[0])
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    metadata = dict(reader.metadata or {})
    metadata[STAMP_KEY] = "1"
    writer.add_metadata({str(k): str(v) for k, v in metadata.items() if v is not None})
    with Path(target).open("wb") as handle:
        writer.write(handle)
    if not is_stamped(target):
        Path(target).unlink(missing_ok=True)
        raise RuntimeError("Damgalı PDF doğrulanamadı.")


def is_stamped(path: str | Path) -> bool:
    try:
        return str((PdfReader(str(path)).metadata or {}).get(STAMP_KEY, "")) == "1"
    except Exception:
        return False

