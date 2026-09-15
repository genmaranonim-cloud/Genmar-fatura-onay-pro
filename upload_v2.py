"""GENMAR Fatura Onay Pro - PDF/XML/HTML birlikte yükleme ve eşleştirme (CA)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import hashlib

from invoice_reader import read_xml, read_html, InvoiceData


@dataclass
class UploadedInvoiceBundle:
    pdf_name: str = ''
    pdf_bytes: bytes | None = None
    data_name: str = ''
    data_bytes: bytes | None = None
    data: InvoiceData | None = None
    source_hash: str = ''


def parse_uploaded_files(files: Iterable) -> list[UploadedInvoiceBundle]:
    """Aynı yüklemedeki PDF ile XML/HTML'yi dosya kökü/fatura no üzerinden eşleştirir."""
    raw = []
    for file in files:
        name = Path(file.filename).name
        ext = Path(name).suffix.lower()
        if ext not in ('.pdf', '.xml', '.html', '.htm'):
            continue
        content = file.read()
        raw.append((name, ext, content))

    data_docs = []
    pdf_docs = []
    for name, ext, content in raw:
        if ext == '.pdf':
            pdf_docs.append((name, content))
            continue
        try:
            parsed = read_xml(content) if ext == '.xml' else read_html(content)
            data_docs.append((name, content, parsed))
        except Exception:
            # Hatalı yardımcı belge ana PDF yüklemesini engellemez.
            continue

    bundles = []
    used_pdf = set()
    for data_name, data_bytes, parsed in data_docs:
        data_stem = _key(Path(data_name).stem)
        match_idx = None
        for i, (pdf_name, _) in enumerate(pdf_docs):
            if i in used_pdf:
                continue
            pdf_stem = _key(Path(pdf_name).stem)
            if data_stem == pdf_stem or (parsed.invoice_no and _key(parsed.invoice_no) in pdf_stem):
                match_idx = i
                break
        pdf_name = ''
        pdf_bytes = None
        if match_idx is not None:
            used_pdf.add(match_idx)
            pdf_name, pdf_bytes = pdf_docs[match_idx]
        bundles.append(UploadedInvoiceBundle(
            pdf_name=pdf_name, pdf_bytes=pdf_bytes,
            data_name=data_name, data_bytes=data_bytes, data=parsed,
            source_hash=hashlib.sha256(data_bytes).hexdigest(),
        ))

    for i, (pdf_name, pdf_bytes) in enumerate(pdf_docs):
        if i not in used_pdf:
            bundles.append(UploadedInvoiceBundle(
                pdf_name=pdf_name, pdf_bytes=pdf_bytes,
                source_hash=hashlib.sha256(pdf_bytes).hexdigest(),
            ))
    return bundles


def _key(value: str) -> str:
    return ''.join(ch.lower() for ch in str(value) if ch.isalnum())
