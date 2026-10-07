"""XML-first invoice reader for UBL-TR invoices.

PDF-derived values may be supplied as a fallback, but a value found in the
XML always wins.  The returned dictionary intentionally keeps the legacy
keys used by ``app.py`` while also exposing explicit totals and rich lines.
"""
from __future__ import annotations

from copy import deepcopy
from xml.etree import ElementTree as ET


MAX_XML_BYTES = 10 * 1024 * 1024


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _children(node, name):
    if node is None:
        return []
    return [item for item in node.iter() if _local(item.tag) == name]


def _first(node, name):
    for item in _children(node, name):
        value = (item.text or "").strip()
        if value:
            return value
    return ""


def _first_node(node, name):
    return next(iter(_children(node, name)), None)


def _number(value):
    if value in (None, ""):
        return None
    value = str(value).strip().replace(" ", "")
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_root(xml_bytes):
    if not isinstance(xml_bytes, (bytes, bytearray)):
        raise TypeError("XML içeriği byte dizisi olmalıdır.")
    if len(xml_bytes) > MAX_XML_BYTES:
        raise ValueError("XML dosyası izin verilen boyutu aşıyor.")
    upper = bytes(xml_bytes[:4096]).upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("DTD ve harici varlık içeren XML kabul edilmez.")
    return ET.fromstring(xml_bytes)


def _supplier_identity(supplier):
    if supplier is None:
        return ""
    company_ids = _children(supplier, "CompanyID") + _children(supplier, "ID")
    for wanted in ("VKN", "TCKN"):
        for node in company_ids:
            if node.attrib.get("schemeID", "").upper() == wanted:
                return (node.text or "").strip()
    return next(((node.text or "").strip() for node in company_ids if (node.text or "").strip()), "")


def read_ubl_invoice(xml_bytes):
    """Read invoice headers and full line details from UBL/UBL-TR XML."""
    root = _safe_root(xml_bytes)
    supplier = _first_node(root, "AccountingSupplierParty")
    party = _first_node(supplier, "Party")
    if party is None:
        party = supplier
    party_name = _first_node(party, "PartyName")
    legal_entity = _first_node(party, "PartyLegalEntity")
    supplier_name = _first(party_name, "Name") or _first(legal_entity, "RegistrationName")
    supplier_tax_id = _supplier_identity(supplier)

    legal_total = _first_node(root, "LegalMonetaryTotal")
    payable_total = _number(_first(legal_total, "PayableAmount"))
    tax_total_node = _first_node(root, "TaxTotal")
    tax_total = _number(_first(tax_total_node, "TaxAmount"))
    currency = _first(root, "DocumentCurrencyCode") or "TRY"

    lines = []
    for position, line in enumerate(_children(root, "InvoiceLine"), start=1):
        item = _first_node(line, "Item")
        if item is None:
            item = line
        quantity_node = _first_node(line, "InvoicedQuantity")
        price_node = _first_node(line, "Price")
        line_tax_node = _first_node(line, "TaxTotal")
        description = _first(item, "Name") or _first(item, "Description")
        lines.append({
            "line_no": _first(line, "ID") or str(position),
            "description": description,
            "quantity": _number(quantity_node.text if quantity_node is not None else None),
            "unit_code": quantity_node.attrib.get("unitCode", "") if quantity_node is not None else "",
            "unit_price": _number(_first(price_node, "PriceAmount")),
            "line_extension_amount": _number(_first(line, "LineExtensionAmount")),
            "tax_amount": _number(_first(line_tax_node, "TaxAmount")),
            "currency": (
                (_first_node(line, "LineExtensionAmount").attrib.get("currencyID", "")
                 if _first_node(line, "LineExtensionAmount") is not None else "")
                or currency
            ),
        })

    invoice_number = _first(root, "ID")
    issue_date = _first(root, "IssueDate")
    return {
        "fatura_no": invoice_number,
        "fatura_tarihi": issue_date,
        "firma_adi": supplier_name,
        "vkn": supplier_tax_id,
        "vkn_tckn": supplier_tax_id,
        "para_birimi": currency,
        "kdv": tax_total,
        "tutar": payable_total,
        "toplam": payable_total,
        "satirlar": lines,
        "kaynak": "xml",
    }


def read_invoice(*, xml_bytes=None, pdf_data=None):
    """Return invoice data with XML values taking priority over PDF fallback.

    ``pdf_data`` is a mapping populated by the existing PDF extractor.  This
    separation keeps the XML parser deterministic and easy to test.
    """
    result = deepcopy(pdf_data or {})
    result.setdefault("satirlar", [])
    result.setdefault("kaynak", "pdf")
    if xml_bytes is not None:
        xml_data = read_ubl_invoice(xml_bytes)
        for key, value in xml_data.items():
            if value not in (None, "", []):
                result[key] = value
        result["kaynak"] = "xml"
    result.setdefault("para_birimi", "TRY")
    return result


def approval_description(data):
    """Build the short legacy approval note from rich or string line data."""
    descriptions = []
    for line in data.get("satirlar", []):
        value = line.get("description", "") if isinstance(line, dict) else str(line)
        if value:
            descriptions.append(value)
    if not descriptions:
        return ""
    preview = ", ".join(descriptions[:4])
    suffix = f" (+{len(descriptions) - 4} kalem)" if len(descriptions) > 4 else ""
    return (preview + suffix)[:1000]
