import unittest

from invoice_reader import approval_description, read_invoice, read_ubl_invoice


SAMPLE_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cbc:ID>INV-2026-42</cbc:ID><cbc:IssueDate>2026-10-07</cbc:IssueDate>
 <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
 <cac:AccountingSupplierParty><cac:Party>
  <cac:PartyIdentification><cbc:ID schemeID="VKN">1234567890</cbc:ID></cac:PartyIdentification>
  <cac:PartyName><cbc:Name>Örnek Satıcı A.Ş.</cbc:Name></cac:PartyName>
 </cac:Party></cac:AccountingSupplierParty>
 <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">36.00</cbc:TaxAmount></cac:TaxTotal>
 <cac:LegalMonetaryTotal><cbc:PayableAmount currencyID="EUR">236.00</cbc:PayableAmount></cac:LegalMonetaryTotal>
 <cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode="C62">2</cbc:InvoicedQuantity>
  <cbc:LineExtensionAmount currencyID="EUR">200.00</cbc:LineExtensionAmount>
  <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">36.00</cbc:TaxAmount></cac:TaxTotal>
  <cac:Item><cbc:Name>Motor parçası</cbc:Name></cac:Item>
  <cac:Price><cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount></cac:Price>
 </cac:InvoiceLine>
</Invoice>'''.encode("utf-8")


class InvoiceReaderTests(unittest.TestCase):
    def test_reads_headers_totals_identity_and_rich_lines(self):
        data = read_ubl_invoice(SAMPLE_XML)
        self.assertEqual(data["fatura_no"], "INV-2026-42")
        self.assertEqual(data["fatura_tarihi"], "2026-10-07")
        self.assertEqual(data["firma_adi"], "Örnek Satıcı A.Ş.")
        self.assertEqual(data["vkn_tckn"], "1234567890")
        self.assertEqual(data["para_birimi"], "EUR")
        self.assertEqual(data["kdv"], 36.0)
        self.assertEqual(data["toplam"], 236.0)
        self.assertEqual(data["satirlar"][0]["description"], "Motor parçası")
        self.assertEqual(data["satirlar"][0]["quantity"], 2.0)
        self.assertEqual(data["satirlar"][0]["unit_price"], 100.0)

    def test_xml_values_override_pdf_fallback(self):
        data = read_invoice(xml_bytes=SAMPLE_XML, pdf_data={
            "fatura_no": "PDF-1", "firma_adi": "PDF Satıcı", "tutar": 1.0,
        })
        self.assertEqual(data["fatura_no"], "INV-2026-42")
        self.assertEqual(data["firma_adi"], "Örnek Satıcı A.Ş.")
        self.assertEqual(data["tutar"], 236.0)
        self.assertEqual(data["kaynak"], "xml")

    def test_approval_description_accepts_rich_lines(self):
        data = read_ubl_invoice(SAMPLE_XML)
        self.assertEqual(approval_description(data), "Motor parçası")

    def test_rejects_dtd(self):
        with self.assertRaisesRegex(ValueError, "DTD"):
            read_ubl_invoice(b'<!DOCTYPE x [<!ENTITY a "x">]><Invoice/>')


if __name__ == "__main__":
    unittest.main()
