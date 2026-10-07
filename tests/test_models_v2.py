import unittest

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from models_v2 import register_models, upsert_invoice_data


class ModelsV2Tests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        self.db = SQLAlchemy(self.app)

        class Fatura(self.db.Model):
            __tablename__ = "fatura"
            id = self.db.Column(self.db.Integer, primary_key=True)

        self.Fatura = Fatura
        self.InvoiceDetail, self.InvoiceLine = register_models(self.db)
        self.context = self.app.app_context()
        self.context.push()
        self.db.create_all()

    def tearDown(self):
        self.db.session.remove()
        self.db.drop_all()
        self.context.pop()

    def test_upsert_persists_header_and_replaces_lines(self):
        invoice = self.Fatura()
        self.db.session.add(invoice)
        self.db.session.flush()
        first = {
            "fatura_no": "A-1", "fatura_tarihi": "2026-10-07",
            "firma_adi": "Satıcı", "vkn_tckn": "1234567890",
            "para_birimi": "TRY", "kdv": 20.0, "toplam": 120.0,
            "kaynak": "xml", "satirlar": [
                {"line_no": "1", "description": "Kalem 1", "quantity": 2.0},
                {"line_no": "2", "description": "Kalem 2", "quantity": 1.0},
            ],
        }
        upsert_invoice_data(self.db, self.InvoiceDetail, self.InvoiceLine, invoice.id, first)
        self.db.session.commit()
        detail = self.InvoiceDetail.query.one()
        self.assertEqual(detail.supplier_tax_id, "1234567890")
        self.assertEqual(len(detail.lines), 2)

        updated = dict(first, satirlar=[{"line_no": "3", "description": "Yeni"}])
        upsert_invoice_data(self.db, self.InvoiceDetail, self.InvoiceLine, invoice.id, updated)
        self.db.session.commit()
        self.assertEqual(self.InvoiceDetail.query.count(), 1)
        self.assertEqual(self.InvoiceLine.query.count(), 1)
        self.assertEqual(self.InvoiceLine.query.one().description, "Yeni")


if __name__ == "__main__":
    unittest.main()
