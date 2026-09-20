import importlib
import sys
import pytest


@pytest.fixture
def module(tmp_path, monkeypatch):
    monkeypatch.setenv('PRO_DATA_DIR', str(tmp_path / 'pro'))
    monkeypatch.setenv('PRO_ADMIN_PASSWORD', 'Only-local-test-489!')
    # Legacy environment must have no effect whatsoever.
    monkeypatch.setenv('DATABASE_URL', 'postgresql://do-not-connect.invalid/production')
    monkeypatch.setenv('SUPABASE_URL', 'https://do-not-connect.invalid')
    sys.modules.pop('app', None)
    m = importlib.import_module('app')
    m.app.config.update(TESTING=True)
    yield m
    with m.app.app_context():
        m.db.session.remove()
        m.db.engine.dispose()


@pytest.fixture
def client(module):
    client = module.app.test_client()
    response = client.post('/login', data={'ad_soyad': 'Dilek Kaya', 'sifre': 'Only-local-test-489!'})
    assert response.status_code == 302
    return client
