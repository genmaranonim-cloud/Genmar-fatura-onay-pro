"""Private, immutable document storage and verifiable approval PDFs."""
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import hashlib
import json
import os
import re
from xml.sax.saxutils import escape
from pypdf import PdfReader, PdfWriter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab


def font():
    if 'ProText' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('ProText', str(Path(reportlab.__file__).parent / 'fonts/Vera.ttf')))
    return 'ProText'


def text_pdf(title, paragraphs):
    out = BytesIO()
    style = ParagraphStyle('Pro', fontName=font(), fontSize=10, leading=16,
                           wordWrap='CJK', spaceAfter=9)
    story = [Paragraph(escape(title), style), Spacer(1, 12)]
    story += [Paragraph(escape(str(t)).replace('\n', '<br/>'), style) for t in paragraphs]
    SimpleDocTemplate(out, title=title).build(story)
    return out.getvalue()


def derived_pdf(data):
    return text_pdf('GENMAR — XML/HTML verisinden üretilen kontrol görünümü', [
        'Bu görünüm yüklenen belgeden oluşturulmuştur; orijinal fatura PDF’si değildir.',
        f'Fatura No: {data.invoice_no}', f'Fatura Tarihi: {data.issue_date}',
        f'Satıcı: {data.supplier_name}', f'VKN: {data.supplier_tax_id}',
        f'Ödenecek Toplam: {data.payable_total or "—"} {data.currency}',
        *[f'{i+1}. {l.description} | Miktar: {l.quantity or "—"} {l.unit_code} | '
          f'Birim fiyat: {l.unit_price or "—"} | Tutar: {l.line_total or "—"}'
          for i, l in enumerate(data.lines)]])


class DocumentStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key):
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ValueError('Geçersiz belge yolu')
        return path

    def put(self, raw, suffix='.pdf'):
        key = uuid4().hex + suffix
        path = self.path(key)
        with path.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return key

    def read(self, key):
        return self.path(key).read_bytes()

    def delete(self, key):
        self.path(key).unlink(missing_ok=True)


class R2DocumentStore:
    """Private document storage backed by Cloudflare R2's S3 API."""

    def __init__(self, endpoint, access_key_id, secret_access_key, bucket, prefix='documents'):
        import boto3

        self.bucket = bucket
        self.prefix = prefix.strip('/')
        self.client = boto3.client(
            's3', endpoint_url=endpoint, region_name='auto',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def object_key(self, key):
        if not re.fullmatch(r'[0-9a-f]{32}(?:\.[A-Za-z0-9]+)?', key or ''):
            raise ValueError('Geçersiz belge anahtarı')
        return f'{self.prefix}/{key}' if self.prefix else key

    def put(self, raw, suffix='.pdf'):
        if not re.fullmatch(r'\.[A-Za-z0-9]{1,10}', suffix or ''):
            raise ValueError('Geçersiz belge uzantısı')
        key = uuid4().hex + suffix.lower()
        self.client.put_object(
            Bucket=self.bucket,
            Key=self.object_key(key),
            Body=raw,
            ContentType={'.pdf': 'application/pdf', '.xml': 'application/xml',
                         '.html': 'text/html', '.htm': 'text/html'}.get(
                             suffix.lower(), 'application/octet-stream'),
        )
        return key

    def read(self, key):
        return self.client.get_object(
            Bucket=self.bucket, Key=self.object_key(key))['Body'].read()

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=self.object_key(key))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def make_approval(original, payload, overlay):
    token = uuid4().hex
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    payload_hash = digest(payload_json.encode())
    first = overlay(original, payload)
    appendix = text_pdf('GENMAR ONAYLANDI — Onay kaydı', [
        f'Onay Kimliği: {token}', f'Fatura No: {payload["fatura_no"]}',
        f'Onaylayan: {payload["onaylayan_ad"]}', f'Tarih: {payload["tarih"]}',
        f'Onay Notu: {payload["not_alani"]}', f'Ödeme Notu: {payload["odeme_notu"]}',
        *[f'Proje: {p["ana"]} / {p["alt"]}' for p in payload['projeler']]])
    writer = PdfWriter()
    for raw in (first, appendix):
        for page in PdfReader(BytesIO(raw)).pages:
            writer.add_page(page)
    writer.add_metadata({'/GenmarOnayDamgasi': '1', '/GenmarApprovalId': token,
                         '/GenmarApprovalHash': payload_hash})
    result = BytesIO()
    writer.write(result)
    return result.getvalue(), token, payload_hash


def verify_approval(raw, token, payload_hash, note):
    try:
        reader = PdfReader(BytesIO(raw))
        meta = reader.metadata or {}
        if meta.get('/GenmarApprovalId') != token or meta.get('/GenmarApprovalHash') != payload_hash:
            return False
        if 'ONAYLANDI' not in (reader.pages[0].extract_text() or ''):
            return False
        text = '\n'.join(p.extract_text() or '' for p in reader.pages)
        compact = lambda s: re.sub(r'\s+', '', s)
        return token in text and compact(note) in compact(text)
    except Exception:
        return False
