"""Persistent V2 invoice header and line models.

The factory receives the application's existing Flask-SQLAlchemy instance so
the V2 models stay isolated from application startup and avoid circular
imports.  Existing table and relationship names are preserved.
"""
from datetime import datetime


def register_models(db):
    class Fatura(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        dosya_adi = db.Column(db.String(255), nullable=False)
        fatura_no = db.Column(db.String(50))
        firma_adi = db.Column(db.String(200))
        fatura_tarihi = db.Column(db.String(20))
        tutar = db.Column(db.Float)
        para_birimi = db.Column(db.String(5), default='TRY')
        durum = db.Column(db.String(20), default='bekliyor')
        kaynak = db.Column(db.String(20), default='upload')
        yuklenme_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
        not_alani = db.Column(db.Text)
        odeme_notu = db.Column(db.Text)
        onaylayan_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=True)
        onay_tarihi = db.Column(db.DateTime, nullable=True)
        departman_id = db.Column(db.Integer, db.ForeignKey('departman.id'), nullable=True)
        atanan_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=True)
        atama_tamamlandi = db.Column(db.Boolean, default=False, nullable=False)
        ana_proje_id = db.Column(db.Integer, db.ForeignKey('ana_proje.id'), nullable=True)
        alt_proje_id = db.Column(db.Integer, db.ForeignKey('alt_proje.id'), nullable=True)
        onaylayan = db.relationship('Kullanici', foreign_keys=[onaylayan_id])
        atanan = db.relationship('Kullanici', foreign_keys=[atanan_id])
        departman = db.relationship('Departman')
        ana_proje = db.relationship('AnaProje')
        alt_proje = db.relationship('AltProje')
        vkn = db.Column(db.String(20))
        belge_uuid = db.Column(db.String(80))
        kimlik = db.Column(db.String(160), unique=True)
        kdv = db.Column(db.Numeric(20, 4))
        okuma_json = db.Column(db.Text)
        kaynak_belgeler = db.Column(db.Text)
        orijinal_pdf = db.Column(db.String(255))
        onay_kimligi = db.Column(db.String(40))
        onay_hash = db.Column(db.String(64))
        pdf_hash = db.Column(db.String(64))
        proje_satirlari = db.relationship(
            'FaturaProje', backref='fatura', cascade='all, delete-orphan')
        satirlar = db.relationship(
            'FaturaSatir', backref='fatura', cascade='all, delete-orphan',
            order_by='FaturaSatir.sira')

    class FaturaSatir(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        fatura_id = db.Column(db.Integer, db.ForeignKey('fatura.id'), nullable=False, index=True)
        sira = db.Column(db.Integer, nullable=False)
        aciklama = db.Column(db.Text, nullable=False)
        miktar = db.Column(db.Numeric(20, 6))
        birim = db.Column(db.String(20))
        birim_fiyat = db.Column(db.Numeric(20, 6))
        satir_tutar = db.Column(db.Numeric(20, 6))
        not_alani = db.Column(db.Text)

    return Fatura, FaturaSatir
