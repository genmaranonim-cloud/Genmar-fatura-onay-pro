from invoice_xml import approval_description, read_ubl_invoice


def test_ubl_xml_reads_supplier_totals_and_lines():
    xml = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
      xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
      xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
      <cbc:ID>GNS2026000001234</cbc:ID><cbc:IssueDate>2026-09-15</cbc:IssueDate>
      <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
      <cac:AccountingSupplierParty><cac:Party><cac:PartyName><cbc:Name>Test Tedarikci A.S.</cbc:Name></cac:PartyName>
      <cac:PartyTaxScheme><cac:TaxScheme><cbc:Name>VKN</cbc:Name></cac:TaxScheme><cbc:CompanyID>1234567890</cbc:CompanyID></cac:PartyTaxScheme>
      </cac:Party></cac:AccountingSupplierParty>
      <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">20.00</cbc:TaxAmount></cac:TaxTotal>
      <cac:LegalMonetaryTotal><cbc:PayableAmount currencyID="EUR">120.00</cbc:PayableAmount></cac:LegalMonetaryTotal>
      <cac:InvoiceLine><cbc:ID>1</cbc:ID><cac:Item><cbc:Name>Pompa</cbc:Name></cac:Item></cac:InvoiceLine>
      <cac:InvoiceLine><cbc:ID>2</cbc:ID><cac:Item><cbc:Description>Hortum</cbc:Description></cac:Item></cac:InvoiceLine>
    </Invoice>'''
    data = read_ubl_invoice(xml)
    assert data['fatura_no'] == 'GNS2026000001234'
    assert data['firma_adi'] == 'Test Tedarikci A.S.'
    assert data['vkn'] == '1234567890'
    assert data['para_birimi'] == 'EUR'
    assert data['tutar'] == 120.0
    assert data['kdv'] == 20.0
    assert data['satirlar'] == ['Pompa', 'Hortum']
    assert approval_description(data) == 'Pompa, Hortum'

