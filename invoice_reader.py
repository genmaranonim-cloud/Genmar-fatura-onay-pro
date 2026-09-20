"""Deterministic V2 reader. XML is authoritative; unrecognized fields stay empty."""
from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import unicodedata
from defusedxml import ElementTree as ET
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO


def normalized(value):
    value = unicodedata.normalize('NFKD', str(value)).casefold().replace('ı', 'i')
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in value if not unicodedata.combining(c)))


def number(value, localized=False):
    if value is None or not str(value).strip():
        return None
    s = re.sub(r'[^0-9,.\-]', '', str(value))
    if localized:
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        elif re.fullmatch(r'-?\d{1,3}(\.\d{3})+', s):
            s = s.replace('.', '')
    try:
        n = Decimal(s)
        return str(n) if n.is_finite() else None
    except InvalidOperation:
        return None


@dataclass
class InvoiceLine:
    line_no: str = ''
    description: str = ''
    quantity: str | None = None
    unit_code: str = ''
    unit_price: str | None = None
    line_total: str | None = None
    currency: str = ''


@dataclass
class InvoiceData:
    source_type: str = ''
    invoice_no: str = ''
    uuid: str = ''
    issue_date: str = ''
    supplier_name: str = ''
    supplier_tax_id: str = ''
    currency: str = 'TRY'
    tax_total: str | None = None
    payable_total: str | None = None
    lines: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def _nodes(node, name):
    return [c for c in node.iter() if _local(c.tag) == name] if node is not None else []


def _child(node, name):
    return next((c for c in node if _local(c.tag) == name), None) if node is not None else None


def _text(node, name):
    child = _child(node, name)
    return (child.text or '').strip() if child is not None else ''


def validate(data):
    data.warnings = [label + ' okunamadı; kontrol edin.' for key, label in (
        ('invoice_no', 'Fatura numarası'), ('issue_date', 'Fatura tarihi'),
        ('supplier_name', 'Satıcı firma'), ('supplier_tax_id', 'VKN/TCKN'),
        ('payable_total', 'Ödenecek toplam')) if getattr(data, key) in ('', None)]
    return data


def read_xml(content):
    root = ET.fromstring(content)
    if _local(root.tag) != 'Invoice':
        raise ValueError('UBL Invoice kökü bulunamadı.')
    data = InvoiceData(source_type='xml', invoice_no=_text(root, 'ID'),
                       uuid=_text(root, 'UUID'), issue_date=_text(root, 'IssueDate'),
                       currency=_text(root, 'DocumentCurrencyCode') or 'TRY')
    supplier = _child(root, 'AccountingSupplierParty')
    names = _nodes(supplier, 'PartyName') or _nodes(supplier, 'PartyLegalEntity')
    if names:
        data.supplier_name = _text(names[0], 'Name') or _text(names[0], 'RegistrationName')
    identifiers = _nodes(supplier, 'ID') + _nodes(supplier, 'CompanyID')
    data.supplier_tax_id = next(((n.text or '').strip() for n in identifiers
        if n.attrib.get('schemeID', '').upper() in ('VKN', 'TCKN')), '')
    if not data.supplier_tax_id:
        data.supplier_tax_id = next(((n.text or '').strip() for n in identifiers
            if re.fullmatch(r'\d{10,11}', (n.text or '').strip())), '')
    totals = [number(_text(n, 'TaxAmount')) for n in root if _local(n.tag) == 'TaxTotal']
    data.tax_total = str(sum(Decimal(n) for n in totals if n is not None)) if totals else None
    data.payable_total = number(_text(_child(root, 'LegalMonetaryTotal'), 'PayableAmount'))
    for node in root:
        if _local(node.tag) != 'InvoiceLine':
            continue
        item = _child(node, 'Item')
        qty = _child(node, 'InvoicedQuantity')
        data.lines.append(InvoiceLine(
            line_no=_text(node, 'ID'),
            description=_text(item, 'Name') or _text(item, 'Description'),
            quantity=number(qty.text) if qty is not None else None,
            unit_code=qty.attrib.get('unitCode', '') if qty is not None else '',
            unit_price=number(_text(_child(node, 'Price'), 'PriceAmount')),
            line_total=number(_text(node, 'LineExtensionAmount')), currency=data.currency))
    return validate(data)


def read_text(text, source='pdf'):
    data = InvoiceData(source_type=source)
    rules = {
        'invoice_no': r'(?:Fatura\s*(?:No|Numarası)|Belge\s*No)\s*[:#]?\s*([A-Z0-9][A-Z0-9-]{5,})',
        'uuid': r'(?:ETTN|UUID)\s*:?\s*([a-f0-9-]{36})',
        'issue_date': r'(?:Fatura\s*Tarihi|Düzenleme\s*Tarihi)\s*:?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{4})',
        'supplier_tax_id': r'(?:Satıcı\s*)?(?:VKN|TCKN|Vergi\s*No)\s*:?\s*(\d{10,11})\b',
        'supplier_name': r'(?:Satıcı|Firma\s*(?:Adı|Ünvanı))\s*:\s*([^\n]+)',
        'payable_total': r'(?:Ödenecek\s*(?:Tutar|Toplam)|Genel\s*Toplam)\s*:?\s*([\d.,]+)',
        'tax_total': r'(?:KDV\s*(?:Tutarı|Toplamı)|Toplam\s*KDV)\s*:?\s*([\d.,]+)',
        'currency': r'(?:Para\s*Birimi)\s*:?\s*(TRY|TL|EUR|USD|GBP)',
    }
    for attr, rule in rules.items():
        match = re.search(rule, text, re.I)
        if match:
            value = match.group(1).strip()
            setattr(data, attr, number(value, True) if attr.endswith('_total') else value)
    if data.currency == 'TL':
        data.currency = 'TRY'
    return validate(data)


def read_html(content):
    soup = BeautifulSoup(content, 'html.parser')
    for node in soup(['script', 'style', 'iframe', 'object']):
        node.decompose()
    # Keep each table row together for label/value recognition.
    row_text = []
    for row in soup.find_all('tr'):
        cells = row.find_all(['td', 'th'], recursive=False)
        if len(cells) == 2:
            row_text.append(' '.join(c.get_text(' ', strip=True) for c in cells))
    data = read_text('\n'.join(row_text) + '\n' + soup.get_text('\n', strip=True), 'html')
    aliases = {
        'description': {'malhizmet', 'malhizmetaciklamasi', 'aciklama', 'urunhizmet', 'urunadi'},
        'quantity': {'miktar'}, 'unit_price': {'birimfiyat', 'birimfiyati'},
        'line_total': {'malhizmettutari', 'satirtutari', 'tutar'}, 'unit_code': {'birim'},
    }
    for table in soup.find_all('table'):
        mapping = None
        for row in table.find_all('tr'):
            values = [c.get_text(' ', strip=True) for c in row.find_all(['td', 'th'], recursive=False)]
            headers = {key: i for i, value in enumerate(values)
                       for key, names in aliases.items() if normalized(value) in names}
            if 'description' in headers:
                mapping = headers
                continue
            if not mapping or len(values) <= max(mapping.values()):
                continue
            fields = {key: values[i] for key, i in mapping.items()}
            if not fields.get('description'):
                continue
            for key in ('quantity', 'unit_price', 'line_total'):
                if key in fields:
                    fields[key] = number(fields[key], True)
            data.lines.append(InvoiceLine(line_no=str(len(data.lines)+1), currency=data.currency, **fields))
    return validate(data)


def read_bytes(name, content):
    ext = Path(name).suffix.lower()
    if ext == '.xml':
        return read_xml(content)
    if ext in ('.html', '.htm'):
        return read_html(content)
    if ext == '.pdf':
        reader = PdfReader(BytesIO(content))
        if not reader.pages or reader.is_encrypted or len(reader.pages) > 100:
            raise ValueError('PDF boş, şifreli veya 100 sayfadan fazla.')
        return read_text('\n'.join(page.extract_text() or '' for page in reader.pages))
    raise ValueError('Yalnızca PDF, XML ve HTML yüklenebilir.')


def bundle_files(files):
    """Match strong identities first, exact stem second; never pair by upload order."""
    groups = []
    for name, raw in files:
        data = read_bytes(name, raw)
        stem = normalized(Path(name).stem)
        candidates = []
        for group in groups:
            for item in group:
                other = item['data']
                identity = ((data.uuid and other.uuid and data.uuid.casefold() == other.uuid.casefold()) or
                            (data.invoice_no and other.invoice_no and data.invoice_no == other.invoice_no))
                same_stem = stem == item['stem']
                if identity or same_stem:
                    # A repeated number across suppliers is not sufficient evidence.
                    if data.supplier_tax_id and other.supplier_tax_id and data.supplier_tax_id != other.supplier_tax_id:
                        if same_stem or (data.uuid and data.uuid == other.uuid):
                            raise ValueError('Eşleşen belgelerde satıcı VKN çelişkisi var.')
                        continue
                    if same_stem and data.invoice_no and other.invoice_no and data.invoice_no != other.invoice_no:
                        raise ValueError('Aynı adlı belgelerde fatura numaraları farklı.')
                    if data.uuid and other.uuid and data.uuid.casefold() != other.uuid.casefold():
                        raise ValueError('Eşleşen belgelerde ETTN çelişkisi var.')
                    candidates.append(group)
                    break
        if len(candidates) > 1:
            raise ValueError('Belge eşleştirmesi belirsiz; faturaları ayrı yükleyin.')
        group = candidates[0] if candidates else []
        if any(i['data'].source_type == data.source_type for i in group):
            raise ValueError('Aynı faturanın aynı formatta iki belgesi seçildi.')
        group.append({'name': name, 'raw': raw, 'data': data, 'stem': stem})
        if not candidates:
            groups.append(group)
    # Refuse partial XML/HTML+PDF batches; require explicit identity/stem correspondence.
    if any(any(i['data'].source_type == 'pdf' for i in g) for g in groups) and any(
            all(i['data'].source_type != 'pdf' for i in g) for g in groups):
        raise ValueError('PDF ile XML/HTML eşleşmedi. Fatura numarasını veya dosya adlarını kontrol edin; tek başına belge yüklemek için ayrı seçin.')
    return groups
