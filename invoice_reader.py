"""GENMAR Fatura Onay Pro - Fatura Okuma Motoru V2 (CA)

Kaynak önceliği: XML -> HTML -> PDF.
Kritik muhasebe alanları mümkün olduğunca deterministik olarak okunur.
AI/Gemini yalnızca açıklama üretimi gibi yardımcı işler için ayrı katmanda kullanılacaktır.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import html as html_lib
import re
import xml.etree.ElementTree as ET


@dataclass
class InvoiceLine:
    line_no: str = ""
    description: str = ""
    quantity: Optional[float] = None
    unit_code: str = ""
    unit_price: Optional[float] = None
    line_total: Optional[float] = None
    currency: str = ""


@dataclass
class InvoiceData:
    source_type: str = ""
    invoice_no: str = ""
    issue_date: str = ""
    supplier_name: str = ""
    supplier_tax_id: str = ""
    customer_name: str = ""
    customer_tax_id: str = ""
    currency: str = "TRY"
    tax_total: Optional[float] = None
    payable_total: Optional[float] = None
    note: str = ""
    lines: list[InvoiceLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _local(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag


def _children(node, name):
    return [x for x in node.iter() if _local(x.tag) == name]


def _first_text(node, name, default=""):
    for x in node.iter():
        if _local(x.tag) == name and (x.text or '').strip():
            return (x.text or '').strip()
    return default


def _float(value):
    if value is None:
        return None
    s = str(value).strip().replace(' ', '')
    if not s:
        return None
    # UBL XML normalde nokta kullanır; TR gösterimlerini de tolere et.
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def _party(party_node):
    name = _first_text(party_node, 'Name') or _first_text(party_node, 'RegistrationName')
    tax_id = ''
    for ident in _children(party_node, 'ID'):
        scheme = (ident.attrib.get('schemeID') or '').upper()
        text = (ident.text or '').strip()
        if scheme in ('VKN', 'TCKN', 'TAX') and text:
            tax_id = text
            break
    if not tax_id:
        candidates = [(x.text or '').strip() for x in _children(party_node, 'ID')]
        tax_id = next((x for x in candidates if x.isdigit() and len(x) in (10, 11)), '')
    return name, tax_id


def read_xml(content: bytes | str) -> InvoiceData:
    if isinstance(content, bytes):
        root = ET.fromstring(content)
    else:
        root = ET.fromstring(content.encode('utf-8'))
    data = InvoiceData(source_type='xml')
    data.invoice_no = _first_text(root, 'ID')
    data.issue_date = _first_text(root, 'IssueDate')
    data.currency = _first_text(root, 'DocumentCurrencyCode', 'TRY')
    notes = [(x.text or '').strip() for x in _children(root, 'Note') if (x.text or '').strip()]
    data.note = ' | '.join(notes)

    suppliers = _children(root, 'AccountingSupplierParty')
    if suppliers:
        data.supplier_name, data.supplier_tax_id = _party(suppliers[0])
    customers = _children(root, 'AccountingCustomerParty')
    if customers:
        data.customer_name, data.customer_tax_id = _party(customers[0])

    tax_totals = _children(root, 'TaxTotal')
    if tax_totals:
        data.tax_total = _float(_first_text(tax_totals[0], 'TaxAmount'))
    legal = _children(root, 'LegalMonetaryTotal')
    if legal:
        data.payable_total = _float(_first_text(legal[0], 'PayableAmount'))

    for inv_line in _children(root, 'InvoiceLine'):
        line = InvoiceLine()
        line.line_no = _first_text(inv_line, 'ID')
        qty_nodes = _children(inv_line, 'InvoicedQuantity')
        if qty_nodes:
            line.quantity = _float(qty_nodes[0].text)
            line.unit_code = qty_nodes[0].attrib.get('unitCode', '')
        ext_nodes = _children(inv_line, 'LineExtensionAmount')
        if ext_nodes:
            line.line_total = _float(ext_nodes[0].text)
            line.currency = ext_nodes[0].attrib.get('currencyID', data.currency)
        items = _children(inv_line, 'Item')
        if items:
            line.description = _first_text(items[0], 'Description') or _first_text(items[0], 'Name')
        prices = _children(inv_line, 'Price')
        if prices:
            line.unit_price = _float(_first_text(prices[0], 'PriceAmount'))
        data.lines.append(line)

    _validate(data)
    return data


def read_html(content: bytes | str) -> InvoiceData:
    text = content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else content
    # HTML'i yalnızca güvenli fallback olarak düz metne indirgeriz; UBL XML varsa XML tercih edilir.
    text = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', ' ', text)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    text = html_lib.unescape(re.sub(r'\s+', ' ', text)).strip()
    data = InvoiceData(source_type='html')
    patterns = {
        'invoice_no': r'(?:Fatura\s*(?:No|Numarası)|Belge\s*No)\s*[:#]?\s*([A-Z0-9-]{6,})',
        'issue_date': r'(?:Fatura\s*Tarihi|Düzenleme\s*Tarihi)\s*[:#]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}-\d{2}-\d{2})',
        'supplier_tax_id': r'(?:VKN|Vergi\s*(?:No|Numarası))\s*[:#]?\s*(\d{10})',
    }
    for attr, pattern in patterns.items():
        m = re.search(pattern, text, flags=re.I)
        if m:
            setattr(data, attr, m.group(1).strip())
    data.note = text[:1000]
    _validate(data)
    return data


def read_invoice(path: str | Path) -> InvoiceData:
    path = Path(path)
    ext = path.suffix.lower()
    raw = path.read_bytes()
    if ext == '.xml':
        return read_xml(raw)
    if ext in ('.html', '.htm'):
        return read_html(raw)
    if ext == '.pdf':
        data = InvoiceData(source_type='pdf')
        data.warnings.append('PDF okuyucu ikinci aşamada mevcut PyPDF/PyMuPDF motoruyla bağlanacak; XML mevcutsa XML tercih edilmelidir.')
        return data
    raise ValueError(f'Desteklenmeyen fatura formatı: {ext}')


def _validate(data: InvoiceData):
    required = {
        'invoice_no': 'Fatura numarası okunamadı',
        'issue_date': 'Fatura tarihi okunamadı',
        'supplier_name': 'Satıcı firma adı okunamadı',
        'supplier_tax_id': 'Satıcı VKN/TCKN okunamadı',
        'payable_total': 'Ödenecek toplam okunamadı',
    }
    for attr, warning in required.items():
        value = getattr(data, attr)
        if value in ('', None):
            data.warnings.append(warning)
