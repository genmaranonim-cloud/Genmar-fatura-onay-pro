from pathlib import Path

from invoice_reader import read_xml


def test_reads_ubl_invoice(tmp_path: Path):
    xml = tmp_path / "invoice.xml"
    xml.write_text("""<?xml version='1.0' encoding='UTF-8'?>
    <Invoice xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'
      xmlns:cac='urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
      xmlns:cbc='urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'>
      <cbc:ID>GNS2026000001234</cbc:ID><cbc:IssueDate>2026-09-15</cbc:IssueDate><cbc:DocumentCurrencyCode>TRY</cbc:DocumentCurrencyCode>
      <cac:AccountingSupplierParty><cac:Party><cac:PartyIdentification><cbc:ID>1234567890</cbc:ID></cac:PartyIdentification><cac:PartyName><cbc:Name>Örnek A.Ş.</cbc:Name></cac:PartyName></cac:Party></cac:AccountingSupplierParty>
      <cac:TaxTotal><cbc:TaxAmount>200.00</cbc:TaxAmount></cac:TaxTotal>
      <cac:LegalMonetaryTotal><cbc:TaxExclusiveAmount>1000.00</cbc:TaxExclusiveAmount><cbc:PayableAmount>1200.00</cbc:PayableAmount></cac:LegalMonetaryTotal>
      <cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode='C62'>2</cbc:InvoicedQuantity><cbc:LineExtensionAmount>1000.00</cbc:LineExtensionAmount><cac:Item><cbc:Name>Servo bakım hizmeti</cbc:Name></cac:Item><cac:Price><cbc:PriceAmount>500.00</cbc:PriceAmount></cac:Price></cac:InvoiceLine>
    </Invoice>""", encoding="utf-8")
    result = read_xml(xml)
    assert result.invoice_number == "GNS2026000001234"
    assert result.supplier_name == "Örnek A.Ş."
    assert result.tax_number == "1234567890"
    assert result.grand_total == 1200
    assert result.lines[0].description == "Servo bakım hizmeti"
