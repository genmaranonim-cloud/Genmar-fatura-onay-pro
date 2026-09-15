import importlib
import os
import sys


def test_xml_lines_are_stored_independently(tmp_path):
    os.environ['DATABASE_URL'] = f"sqlite:///{tmp_path / 'test.db'}"
    sys.modules.pop('app', None)
    module = importlib.import_module('app')
    module.app.config.update(TESTING=True)

    with module.app.app_context():
        invoice = module.Fatura(dosya_adi='test.pdf')
        module.fatura_satirlarini_yenile(invoice, {'satirlar': ['Pompa', 'Hortum']})
        module.db.session.add(invoice)
        module.db.session.commit()
        saved = module.db.session.get(module.Fatura, invoice.id)
        assert [line.aciklama for line in saved.satirlar] == ['Pompa', 'Hortum']
