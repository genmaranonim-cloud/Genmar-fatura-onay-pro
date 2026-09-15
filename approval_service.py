"""GENMAR Fatura Onay Pro - güvenli onay/damga zinciri (CA).

Amaç:
1) Veritabanı alanlarını kaydet.
2) PDF'yi damgala.
3) Damgalı PDF'yi yeni bir storage nesnesine yaz.
4) Yazılan PDF'yi tekrar indirip damgayı doğrula.
5) Ancak doğrulama başarılıysa fatura dosya adresini kesinleştir.

Bu modül uygulamaya adaptör fonksiyonları verilerek bağlanır; böylece eski çalışan
repository değiştirilmeden yeni sürümde kullanılabilir.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Any


@dataclass
class ApprovalResult:
    ok: bool
    stamped: bool
    pdf_url: str = ""
    message: str = ""


def approve_and_stamp(
    *,
    invoice: Any,
    user: Any,
    payload: dict,
    db_session: Any,
    read_pdf: Callable[[Any], bytes],
    stamp_pdf: Callable[[bytes, dict], bytes],
    store_pdf: Callable[[bytes, Any], str],
    verify_stamp: Callable[[bytes], bool],
    read_stored_pdf: Callable[[str], bytes],
) -> ApprovalResult:
    """Onayı otomatik sonraki faturaya geçmeden güvenli biçimde kesinleştirir."""
    invoice.fatura_no = _text(payload.get('fatura_no')) or invoice.fatura_no
    invoice.firma_adi = _text(payload.get('firma_adi')) or invoice.firma_adi
    invoice.fatura_tarihi = _text(payload.get('fatura_tarihi')) or invoice.fatura_tarihi
    if payload.get('tutar') not in (None, ''):
        invoice.tutar = payload.get('tutar')
    invoice.not_alani = _text(payload.get('not_alani'))
    invoice.odeme_notu = _text(payload.get('odeme_notu'))
    invoice.onaylayan_id = getattr(user, 'id', None)
    invoice.departman_id = getattr(user, 'departman_id', None)
    invoice.onay_tarihi = datetime.utcnow()

    # Kritik fark: damga doğrulanmadan durum onaylandı olarak kesinleştirilmez.
    invoice.durum = 'onay_isleniyor'
    db_session.flush()

    original_pdf = read_pdf(invoice)
    stamp_info = _stamp_info(invoice, user, payload)
    stamped_pdf = stamp_pdf(original_pdf, stamp_info)
    if not verify_stamp(stamped_pdf):
        db_session.rollback()
        return ApprovalResult(False, False, message='Damga üretildi ancak PDF içinde doğrulanamadı.')

    new_url = store_pdf(stamped_pdf, invoice)
    stored_pdf = read_stored_pdf(new_url)
    if not verify_stamp(stored_pdf):
        db_session.rollback()
        return ApprovalResult(False, False, message='Damgalı PDF storage sonrasında doğrulanamadı.')

    invoice.dosya_adi = new_url
    invoice.durum = 'onaylandi'
    db_session.commit()
    return ApprovalResult(
        True, True, pdf_url=new_url,
        message='Fatura onaylandı. Damgalı PDF hazır; sonraki faturaya geçmek için sağ yön tuşunu kullanın.'
    )


def _stamp_info(invoice, user, payload):
    return {
        'projeler': payload.get('projeler') or [],
        'not_alani': getattr(invoice, 'not_alani', '') or '-',
        'odeme_notu': getattr(invoice, 'odeme_notu', '') or '-',
        'onaylayan_ad': getattr(user, 'ad_soyad', '-') or '-',
        'departman_kod': getattr(getattr(user, 'departman', None), 'kod', '-') or '-',
        'tarih': (getattr(invoice, 'onay_tarihi', None) or datetime.utcnow()).strftime('%d.%m.%Y %H:%M'),
        'kisaltma': getattr(user, 'kisaltma', '') or '',
    }


def _text(value):
    return '' if value is None else str(value).strip()
