import importlib
import os
import sys


def test_login_and_invoice_screen_smoke(tmp_path):
    os.environ['DATABASE_URL'] = f"sqlite:///{tmp_path / 'smoke.db'}"
    sys.modules.pop('app', None)
    module = importlib.import_module('app')
    module.app.config.update(TESTING=True)
    client = module.app.test_client()

    login_page = client.get('/login')
    assert login_page.status_code == 200
    assert 'V0.2 – TEST'.encode() in login_page.data

    response = client.post('/login', data={'ad_soyad': 'Dilek Kaya', 'sifre': '1'},
                           follow_redirects=True)
    assert response.status_code == 200
    assert 'Gelen Faturalar'.encode() in response.data
    assert 'V0.2 – TEST'.encode() in response.data
