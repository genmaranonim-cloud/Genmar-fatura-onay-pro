"""Persistent invoice header and line models.

The models are registered through a small factory so the legacy application
can keep owning its existing Flask-SQLAlchemy ``db`` object without circular
imports.
"""
from datetime import datetime


def register_models(db):
    class InvoiceDetail(db.Model):
        __tablename__ = "invoice_detail"

        id = db.Column(db.Integer, primary_key=True)
        fatura_id = db.Column(
            db.Integer, db.ForeignKey("fatura.id", ondelete="CASCADE"),
            nullable=False, unique=True, index=True,
        )
        invoice_number = db.Column(db.String(50), index=True)
        issue_date = db.Column(db.String(20))
        supplier_name = db.Column(db.String(200))
        supplier_tax_id = db.Column(db.String(20), index=True)
        currency = db.Column(db.String(5), nullable=False, default="TRY")
        tax_total = db.Column(db.Float)
        payable_total = db.Column(db.Float)
        source = db.Column(db.String(20), nullable=False, default="xml")
        created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
        updated_at = db.Column(
            db.DateTime, nullable=False, default=datetime.utcnow,
            onupdate=datetime.utcnow,
        )
        lines = db.relationship(
            "InvoiceLine", backref="invoice_detail", lazy="select",
            cascade="all, delete-orphan", order_by="InvoiceLine.position",
        )

    class InvoiceLine(db.Model):
        __tablename__ = "invoice_line"

        id = db.Column(db.Integer, primary_key=True)
        invoice_detail_id = db.Column(
            db.Integer, db.ForeignKey("invoice_detail.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
        position = db.Column(db.Integer, nullable=False)
        line_no = db.Column(db.String(50))
        description = db.Column(db.Text)
        quantity = db.Column(db.Float)
        unit_code = db.Column(db.String(20))
        unit_price = db.Column(db.Float)
        line_extension_amount = db.Column(db.Float)
        tax_amount = db.Column(db.Float)
        currency = db.Column(db.String(5))

    return InvoiceDetail, InvoiceLine


def upsert_invoice_data(db, InvoiceDetail, InvoiceLine, fatura_id, data):
    """Create/update a normalized invoice snapshot and replace its lines."""
    detail = InvoiceDetail.query.filter_by(fatura_id=fatura_id).first()
    if detail is None:
        detail = InvoiceDetail(fatura_id=fatura_id)
        db.session.add(detail)

    detail.invoice_number = data.get("fatura_no") or None
    detail.issue_date = data.get("fatura_tarihi") or None
    detail.supplier_name = data.get("firma_adi") or None
    detail.supplier_tax_id = data.get("vkn_tckn") or data.get("vkn") or None
    detail.currency = data.get("para_birimi") or "TRY"
    detail.tax_total = data.get("kdv")
    detail.payable_total = data.get("toplam", data.get("tutar"))
    detail.source = data.get("kaynak") or "xml"

    detail.lines.clear()
    for position, line in enumerate(data.get("satirlar") or [], start=1):
        if not isinstance(line, dict):
            line = {"description": str(line)}
        detail.lines.append(InvoiceLine(
            position=position,
            line_no=line.get("line_no") or str(position),
            description=line.get("description") or None,
            quantity=line.get("quantity"),
            unit_code=line.get("unit_code") or None,
            unit_price=line.get("unit_price"),
            line_extension_amount=line.get("line_extension_amount"),
            tax_amount=line.get("tax_amount"),
            currency=line.get("currency") or detail.currency,
        ))
    return detail
