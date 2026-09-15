from __future__ import annotations

import os
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

from invoice_reader import read_invoice
from pdf_stamp import is_stamped, stamp_pdf

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
database_url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'genmar.db'}")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
db = SQLAlchemy(app)


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(80), index=True)
    invoice_date = db.Column(db.Date)
    supplier_name = db.Column(db.String(240))
    tax_number = db.Column(db.String(20))
    currency = db.Column(db.String(8), default="TRY")
    subtotal = db.Column(db.Numeric(18, 4))
    tax_total = db.Column(db.Numeric(18, 4))
    grand_total = db.Column(db.Numeric(18, 4))
    description = db.Column(db.Text)
    status = db.Column(db.String(30), default="kontrol_bekliyor", index=True)
    source_type = db.Column(db.String(10))
    source_path = db.Column(db.Text)
    pdf_path = db.Column(db.Text)
    stamped_pdf_path = db.Column(db.Text)
    warnings = db.Column(db.Text)
    approved_by = db.Column(db.String(120))
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    lines = db.relationship("InvoiceLine", cascade="all, delete-orphan", backref="invoice")
    logs = db.relationship("AuditLog", cascade="all, delete-orphan", backref="invoice")


class InvoiceLine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Numeric(18, 4))
    unit = db.Column(db.String(20))
    unit_price = db.Column(db.Numeric(18, 4))
    line_total = db.Column(db.Numeric(18, 4))


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    action = db.Column(db.String(60), nullable=False)
    actor = db.Column(db.String(120), nullable=False)
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


@app.before_request
def initialize_database():
    db.create_all()


@app.get("/")
def index():
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template("index.html", invoices=invoices)


@app.post("/upload")
def upload():
    files = [f for f in request.files.getlist("documents") if f and f.filename]
    if not files:
        flash("En az bir PDF, XML veya HTML dosyası seçin.", "error")
        return redirect(url_for("index"))
    allowed = {".pdf", ".xml", ".html", ".htm"}
    saved: list[tuple[Path, object]] = []
    for file in files:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in allowed:
            flash(f"Desteklenmeyen dosya: {file.filename}", "error")
            continue
        path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        file.save(path)
        saved.append((path, file))
    if not saved:
        return redirect(url_for("index"))
    preferred = next((p for p, _ in saved if p.suffix.lower() == ".xml"), None)
    preferred = preferred or next((p for p, _ in saved if p.suffix.lower() in {".html", ".htm"}), None)
    preferred = preferred or saved[0][0]
    data = read_invoice(preferred)
    pdf = next((p for p, _ in saved if p.suffix.lower() == ".pdf"), None)
    invoice = Invoice(
        invoice_number=data.invoice_number, invoice_date=data.invoice_date,
        supplier_name=data.supplier_name, tax_number=data.tax_number,
        currency=data.currency, subtotal=data.subtotal, tax_total=data.tax_total,
        grand_total=data.grand_total, source_type=data.source,
        source_path=str(preferred), pdf_path=str(pdf) if pdf else None,
        warnings="\n".join(data.warnings),
    )
    for position, line in enumerate(data.lines, 1):
        invoice.lines.append(InvoiceLine(position=position, description=line.description,
            quantity=line.quantity, unit=line.unit, unit_price=line.unit_price, line_total=line.line_total))
    db.session.add(invoice)
    db.session.flush()
    db.session.add(AuditLog(invoice_id=invoice.id, action="yuklendi", actor="Dilek Kaya", detail=data.source.upper()))
    db.session.commit()
    flash("Fatura okundu. Sarı uyarılı alanları kontrol edin.", "success")
    return redirect(url_for("detail", invoice_id=invoice.id))


@app.route("/invoice/<int:invoice_id>", methods=["GET", "POST"])
def detail(invoice_id: int):
    invoice = db.get_or_404(Invoice, invoice_id)
    if request.method == "POST" and invoice.status != "onaylandi":
        invoice.invoice_number = request.form.get("invoice_number", "").strip()
        invoice.supplier_name = request.form.get("supplier_name", "").strip()
        invoice.tax_number = request.form.get("tax_number", "").strip()
        invoice.currency = request.form.get("currency", "TRY").strip().upper()
        invoice.description = request.form.get("description", "").strip()
        for field in ("subtotal", "tax_total", "grand_total"):
            raw = request.form.get(field, "").replace(",", ".").strip()
            setattr(invoice, field, Decimal(raw) if raw else None)
        db.session.add(AuditLog(invoice_id=invoice.id, action="alanlar_guncellendi", actor="Dilek Kaya"))
        db.session.commit()
        flash("Fatura bilgileri kaydedildi.", "success")
        return redirect(url_for("detail", invoice_id=invoice.id))
    previous = Invoice.query.filter(Invoice.id < invoice.id).order_by(Invoice.id.desc()).first()
    following = Invoice.query.filter(Invoice.id > invoice.id).order_by(Invoice.id.asc()).first()
    return render_template("detail.html", invoice=invoice, previous=previous, following=following)


@app.post("/invoice/<int:invoice_id>/approve")
def approve(invoice_id: int):
    invoice = db.get_or_404(Invoice, invoice_id)
    if invoice.status == "onaylandi":
        flash("Bu fatura zaten onaylanmış.", "error")
        return redirect(url_for("detail", invoice_id=invoice.id))
    if not invoice.pdf_path:
        flash("Damga için eşleştirilmiş PDF gerekli. Fatura onaylanmadı.", "error")
        return redirect(url_for("detail", invoice_id=invoice.id))
    invoice.status = "onay_isleniyor"
    db.session.commit()
    try:
        target = UPLOAD_DIR / f"approved_{invoice.id}_{Path(invoice.pdf_path).name}"
        approver = request.form.get("approver", "Dilek Kaya").strip() or "Dilek Kaya"
        stamp_pdf(invoice.pdf_path, target, approver, invoice.description or "")
        if not is_stamped(target):
            raise RuntimeError("Damga doğrulanamadı")
        invoice.stamped_pdf_path = str(target)
        invoice.status = "onaylandi"
        invoice.approved_by = approver
        invoice.approved_at = datetime.utcnow()
        db.session.add(AuditLog(invoice_id=invoice.id, action="onaylandi", actor=approver,
                                detail="Damgalı PDF doğrulandı; otomatik geçiş yapılmadı."))
        db.session.commit()
        flash("Fatura onaylandı ve damga doğrulandı. Sonraki faturaya geçmek için → tuşunu kullanın.", "success")
    except Exception as exc:
        invoice.status = "damga_hatasi"
        db.session.add(AuditLog(invoice_id=invoice.id, action="damga_hatasi", actor="Sistem", detail=str(exc)))
        db.session.commit()
        flash(f"Fatura onaylanmadı: {exc}", "error")
    return redirect(url_for("detail", invoice_id=invoice.id))


@app.get("/invoice/<int:invoice_id>/pdf")
def pdf(invoice_id: int):
    invoice = db.get_or_404(Invoice, invoice_id)
    path = invoice.stamped_pdf_path or invoice.pdf_path
    if not path or not Path(path).exists():
        return "PDF bulunamadı", 404
    return send_file(path, mimetype="application/pdf", as_attachment=False)


if __name__ == "__main__":
    app.run(debug=True)
