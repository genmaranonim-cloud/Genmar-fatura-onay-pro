from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_visible_test_version_is_present_on_base_and_login():
    base = (ROOT / 'templates' / 'base.html').read_text(encoding='utf-8')
    login = (ROOT / 'templates' / 'login.html').read_text(encoding='utf-8')
    assert '{{ app_version }}' in base
    assert '{{ app_version }}' in login


def test_approval_does_not_advance_and_stamp_button_is_removed():
    page = (ROOT / 'templates' / 'gelen.html').read_text(encoding='utf-8')
    approval = page.split('async function onayla(durum)', 1)[1].split('// ─── AKTAR', 1)[0]
    assert 'sonrakiFatura()' not in approval
    assert 'faturaDamgaBtn' not in page
    assert 'Fatura Satırları (XML / HTML)' in page


def test_invoice_view_does_not_auto_stamp_pdf():
    source = (ROOT / 'app.py').read_text(encoding='utf-8')
    view = source.split('def fatura_goruntule', 1)[1].split('# ─── MUHASEBE', 1)[0]
    assert 'fatura_onay_damgasi_uygula' not in view

