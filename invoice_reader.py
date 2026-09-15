from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader


@dataclass
class InvoiceLineData:
    description: str = ""
    quantity: Decimal | None = None
    unit: str = ""
    unit_price: Decimal | None = None
    line_total: Decimal | None = None


@dataclass
class InvoiceData:
    invoice_number: str = ""
    invoice_date: date | None = None
    supplier_name: str = ""
    tax_number: str = ""
    currency: str = "TRY"
    subtotal: Decimal | None = None
    tax_total: Decimal | None = None
    grand_total: Decimal | None = None
    lines: list[InvoiceLineData] = field(default_factory=list)
    source: str = ""
    warnings: list[str] = field(default_factory=list)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(root: ET.Element, name: str) -> str:
    for node in root.iter():
        if _local(node.tag) == name and (node.text or "").strip():
            return (node.text or "").strip()
    return ""


def _decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    normalized = value.strip().replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


def read_xml(path: str | Path) -> InvoiceData:
    root = ET.parse(path).getroot()
    result = InvoiceData(source="xml")
    result.invoice_number = _first_text(root, "ID")
    result.invoice_date = _date(_first_text(root, "IssueDate"))
    result.currency = _first_text(root, "DocumentCurrencyCode") or "TRY"

    supplier = next((n for n in root.iter() if _local(n.tag) == "AccountingSupplierParty"), None)
    if supplier is not None:
        result.supplier_name = _first_text(supplier, "Name") or _first_text(supplier, "RegistrationName")
        # UBL-TR suppliers may place the VKN in PartyIdentification/ID or
        # PartyTaxScheme/CompanyID depending on the producing application.
        result.tax_number = _first_text(supplier, "CompanyID") or _first_text(supplier, "ID")

    monetary = next((n for n in root.iter() if _local(n.tag) == "LegalMonetaryTotal"), None)
    if monetary is not None:
        result.subtotal = _decimal(_first_text(monetary, "TaxExclusiveAmount"))
        result.grand_total = _decimal(_first_text(monetary, "PayableAmount"))
    tax_node = next((n for n in root.iter() if _local(n.tag) == "TaxTotal"), None)
    if tax_node is not None:
        result.tax_total = _decimal(_first_text(tax_node, "TaxAmount"))

    for node in root.iter():
        if _local(node.tag) != "InvoiceLine":
            continue
        item = next((n for n in node.iter() if _local(n.tag) == "Item"), node)
        quantity_node = next((n for n in node.iter() if _local(n.tag) == "InvoicedQuantity"), None)
        result.lines.append(InvoiceLineData(
            description=_first_text(item, "Name") or _first_text(item, "Description"),
            quantity=_decimal(quantity_node.text if quantity_node is not None else None),
            unit=quantity_node.attrib.get("unitCode", "") if quantity_node is not None else "",
            unit_price=_decimal(_first_text(node, "PriceAmount")),
            line_total=_decimal(_first_text(node, "LineExtensionAmount")),
        ))
    return _validate(result)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _from_text(text: str, source: str) -> InvoiceData:
    result = InvoiceData(source=source)
    patterns = {
        "invoice_number": r"(?:fatura\s*(?:no|numarası)|invoice\s*(?:no|number))\s*[:#]?\s*([A-Z0-9-]{5,})",
        "tax_number": r"(?:vkn|vergi\s*(?:no|numarası)|tax\s*(?:id|number))\s*[:#]?\s*(\d{10,11})",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.I)
        if match:
            setattr(result, key, match.group(1).strip())
    date_match = re.search(r"(?:tarih|date)\s*[:#]?\s*(\d{2}[./-]\d{2}[./-]\d{4}|\d{4}-\d{2}-\d{2})", text, re.I)
    if date_match:
        raw = date_match.group(1).replace(".", "-").replace("/", "-")
        parts = raw.split("-")
        result.invoice_date = _date(raw if len(parts[0]) == 4 else f"{parts[2]}-{parts[1]}-{parts[0]}")
    currency = re.search(r"\b(TRY|TL|USD|EUR|GBP)\b", text, re.I)
    if currency:
        result.currency = "TRY" if currency.group(1).upper() == "TL" else currency.group(1).upper()
    return _validate(result)


def read_html(path: str | Path) -> InvoiceData:
    parser = _TextExtractor()
    parser.feed(Path(path).read_text(encoding="utf-8", errors="replace"))
    return _from_text("\n".join(parser.parts), "html")


def read_pdf(path: str | Path) -> InvoiceData:
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages[:4])
    result = _from_text(text, "pdf")
    if not text.strip():
        result.warnings.append("PDF metin katmanı içermiyor; OCR gerekir.")
    return result


def read_invoice(path: str | Path) -> InvoiceData:
    suffix = Path(path).suffix.lower()
    if suffix == ".xml":
        return read_xml(path)
    if suffix in {".html", ".htm"}:
        return read_html(path)
    if suffix == ".pdf":
        return read_pdf(path)
    raise ValueError("Yalnız PDF, XML ve HTML dosyaları desteklenir.")


def _validate(result: InvoiceData) -> InvoiceData:
    if not result.invoice_number:
        result.warnings.append("Fatura numarası okunamadı.")
    if not result.supplier_name:
        result.warnings.append("Satıcı unvanı okunamadı; kontrol edin.")
    if result.source != "xml":
        result.warnings.append("XML dışındaki kaynaklarda alanları kullanıcı doğrulamalıdır.")
    return result
