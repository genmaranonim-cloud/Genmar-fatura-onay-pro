"""UBL-TR e-Fatura XML okuyucu."""
from xml.etree import ElementTree as ET


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def _first(node, name):
    for item in node.iter():
        if _local(item.tag) == name and (item.text or '').strip():
            return (item.text or '').strip()
    return ''


def _number(value):
    if not value:
        return None
    value = value.strip().replace(' ', '')
    if ',' in value and '.' in value:
        value = value.replace('.', '').replace(',', '.')
    elif ',' in value:
        value = value.replace(',', '.')
    try:
        return float(value)
    except ValueError:
        return None


def read_ubl_invoice(xml_bytes):
    root = ET.fromstring(xml_bytes)
    result = {
        'fatura_no': _first(root, 'ID'),
        'fatura_tarihi': _first(root, 'IssueDate'),
        'para_birimi': _first(root, 'DocumentCurrencyCode') or 'TRY',
        'firma_adi': '',
        'vkn': '',
        'tutar': None,
        'kdv': None,
        'satirlar': [],
    }
    supplier = next((x for x in root.iter() if _local(x.tag) == 'AccountingSupplierParty'), None)
    if supplier is not None:
        result['firma_adi'] = _first(supplier, 'Name') or _first(supplier, 'RegistrationName')
        result['vkn'] = _first(supplier, 'CompanyID') or _first(supplier, 'ID')
    legal = next((x for x in root.iter() if _local(x.tag) == 'LegalMonetaryTotal'), None)
    if legal is not None:
        result['tutar'] = _number(_first(legal, 'PayableAmount'))
    tax = next((x for x in root.iter() if _local(x.tag) == 'TaxTotal'), None)
    if tax is not None:
        result['kdv'] = _number(_first(tax, 'TaxAmount'))
    for line in root.iter():
        if _local(line.tag) != 'InvoiceLine':
            continue
        item = next((x for x in line.iter() if _local(x.tag) == 'Item'), line)
        description = _first(item, 'Name') or _first(item, 'Description')
        if description:
            result['satirlar'].append(description)
    return result


def approval_description(data):
    lines = [x for x in data.get('satirlar', []) if x]
    if not lines:
        return ''
    preview = ', '.join(lines[:4])
    suffix = f" (+{len(lines)-4} kalem)" if len(lines) > 4 else ''
    return (preview + suffix)[:1000]
