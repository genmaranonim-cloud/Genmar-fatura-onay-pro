import importlib
import os
import sys


def test_login_and_invoice_screen_smoke(module):
    client = module.app.test_client()

    login_page = client.get('/login')
    assert login_page.status_code == 200
    assert 'V0.2 – TEST'.encode() in login_page.data

    response = client.post('/login', data={'ad_soyad': 'Dilek Kaya', 'sifre': 'Only-local-test-489!'},
                           follow_redirects=True)
    assert response.status_code == 200
    assert 'Gelen Faturalar'.encode() in response.data
    assert 'V0.2 – TEST'.encode() in response.data
