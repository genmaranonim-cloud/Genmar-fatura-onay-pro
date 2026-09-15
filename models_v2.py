"""V2 veri modeli taslağı.
Okunan fatura alanları PDF'den bağımsız kalıcı tutulur.
"""
from datetime import datetime


def register_v2_models(db):
    class FaturaSatir(db.Model):
        __tablename__ = 'fatura_satir'
        id = db.Column(db.Integer, primary_key=True)
        fatura_id = db.Column(db.Integer, db.ForeignKey('fatura.id'), nullable=False, index=True)
        sira_no = db.Column(db.String(30))
        aciklama = db.Column(db.Text)
        miktar = db.Column(db.Float)
        birim = db.Column(db.String(30))
        birim_fiyat = db.Column(db.Float)
        satir_toplam = db.Column(db.Float)
        para_birimi = db.Column(db.String(5))
        olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    class FaturaOkumaKaydi(db.Model):
        __tablename__ = 'fatura_okuma_kaydi'
        id = db.Column(db.Integer, primary_key=True)
        fatura_id = db.Column(db.Integer, db.ForeignKey('fatura.id'), nullable=False, index=True)
        kaynak_turu = db.Column(db.String(10), nullable=False)  # xml/html/pdf
        kaynak_hash = db.Column(db.String(64), index=True)
        okunan_json = db.Column(db.Text, nullable=False)
        uyari_json = db.Column(db.Text)
        okuma_tarihi = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    return FaturaSatir, FaturaOkumaKaydi
