from pathlib import Path

from reportlab.pdfgen import canvas

from pdf_stamp import is_stamped, stamp_pdf


def test_stamp_is_written_and_verified(tmp_path: Path):
    source = tmp_path / "source.pdf"
    target = tmp_path / "approved.pdf"
    pdf = canvas.Canvas(str(source))
    pdf.drawString(50, 780, "Test invoice")
    pdf.save()

    stamp_pdf(source, target, "Dilek Kaya", "Kontrol edildi")

    assert target.exists()
    assert is_stamped(target)
