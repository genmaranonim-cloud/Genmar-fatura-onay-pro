from io import BytesIO
from pathlib import Path

from reportlab.pdfgen import canvas


def _pdf_bytes(tmp_path: Path) -> bytes:
    path = tmp_path / "invoice.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(50, 780, "Fatura No: TEST2026001")
    pdf.save()
    return path.read_bytes()


def test_approval_stays_on_invoice_and_creates_verified_stamp(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    import importlib
    import app as module
    module = importlib.reload(module)
    module.app.config.update(TESTING=True)

    with module.app.test_client() as client:
        upload = client.post("/upload", data={"documents": (BytesIO(_pdf_bytes(tmp_path)), "invoice.pdf")},
                             content_type="multipart/form-data")
        assert upload.status_code == 302
        detail_url = upload.headers["Location"]
        approval = client.post(f"{detail_url}/approve", data={"approver": "Dilek Kaya"})
        assert approval.status_code == 302
        assert approval.headers["Location"].endswith(detail_url)
        with module.app.app_context():
            invoice = module.Invoice.query.one()
            assert invoice.status == "onaylandi"
            assert Path(invoice.stamped_pdf_path).exists()
