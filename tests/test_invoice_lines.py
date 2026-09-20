import importlib
import os
import sys


def test_xml_lines_are_stored_independently(module):

    with module.app.app_context():
        invoice = module.Fatura(dosya_adi='test.pdf')
        module.fatura_satirlarini_yenile(invoice, {'satirlar': ['Pompa', 'Hortum']})
        module.db.session.add(invoice)
        module.db.session.commit()
        saved = module.db.session.get(module.Fatura, invoice.id)
        assert [line.aciklama for line in saved.satirlar] == ['Pompa', 'Hortum']
