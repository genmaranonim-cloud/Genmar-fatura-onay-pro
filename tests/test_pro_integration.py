from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
import pytest
from pypdf import PdfReader
from invoice_reader import read_xml, read_html, bundle_files
from pro_documents import text_pdf, digest


def xml(no='TST2026000000001', tax='1234567890'):
    return f'''<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:c="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
 xmlns:a="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
 <c:ID>{no}</c:ID><c:IssueDate>2026-09-20</c:IssueDate><c:DocumentCurrencyCode>TRY</c:DocumentCurrencyCode>
 <a:AccountingSupplierParty><a:Party><a:PartyIdentification><c:ID schemeID="VKN">{tax}</c:ID></a:PartyIdentification>
 <a:PartyName><c:Name>Örnek Test Tedarikçisi AŞ</c:Name></a:PartyName></a:Party></a:AccountingSupplierParty>
 <a:TaxTotal><c:TaxAmount>60.30</c:TaxAmount></a:TaxTotal>
 <a:LegalMonetaryTotal><c:PayableAmount>361.80</c:PayableAmount></a:LegalMonetaryTotal>
 <a:InvoiceLine><c:ID>1</c:ID><c:InvoicedQuantity unitCode="C62">2</c:InvoicedQuantity>
 <c:LineExtensionAmount>201.00</c:LineExtensionAmount><a:Item><c:Name>Pompa</c:Name></a:Item>
 <a:Price><c:PriceAmount>100.50</c:PriceAmount></a:Price></a:InvoiceLine>
 <a:InvoiceLine><c:ID>2</c:ID><c:InvoicedQuantity unitCode="C62">1</c:InvoicedQuantity>
 <c:LineExtensionAmount>100.50</c:LineExtensionAmount><a:Item><c:Name>Bağlantı parçası</c:Name></a:Item>
 <a:Price><c:PriceAmount>100.50</c:PriceAmount></a:Price></a:InvoiceLine></Invoice>'''.encode()


def pdf(no='TST2026000000001'):
    return text_pdf('Örnek test faturası', [f'Fatura No: {no}', 'Fatura Tarihi: 20.09.2026',
        'Satıcı: Örnek Test Tedarikçisi AŞ', 'VKN: 1234567890', 'Ödenecek Toplam: 361,80'])


def html(no='TST2026000000001'):
    return f'''<html><body><table><tr><td>Fatura No:</td><td>{no}</td></tr>
    <tr><td>Satıcı:</td><td>Örnek Test Tedarikçisi AŞ</td></tr>
    <tr><td>Fatura Tarihi:</td><td>20.09.2026</td></tr>
    <tr><td>VKN:</td><td>1234567890</td></tr>
    <tr><td>Ödenecek Toplam:</td><td>1.234,56</td></tr></table>
    <table><tr><th>Mal Hizmet</th><th>Miktar</th><th>Birim Fiyat</th><th>Tutar</th></tr>
    <tr><td>Pompa</td><td>2</td><td>100,50</td><td>201,00</td></tr></table>
    <script>alert('not executed')</script></body></html>'''.encode()


def upload(client, entries=None):
    entries = entries or [('test.pdf', pdf()), ('test.xml', xml())]
    return client.post('/api/upload', data={'dosyalar': [(BytesIO(raw), name) for name, raw in entries]},
                       content_type='multipart/form-data')


def created(client, entries=None):
    response = upload(client, entries)
    assert response.status_code == 200, response.json
    return response.json['ids'][0]


def approve(client, id, **fields):
    return client.post(f'/api/fatura/{id}/onayla', json={'durum':'onaylandi',
        'not_alani':'Türkçe onay notu: ölçü, bağlantı, şaft. ' * 20,
        'odeme_notu':'30 gün vade', **fields})


def test_xml_full_lines_and_decimals():
    data = read_xml(xml())
    assert data.invoice_no == 'TST2026000000001'
    assert data.supplier_tax_id == '1234567890'
    assert data.payable_total == '361.80'
    assert data.lines[0].quantity == '2'
    assert data.lines[1].description == 'Bağlantı parçası'
    assert data.lines[0].unit_price == '100.50'
    assert not data.warnings


def test_xml_header_id_is_not_line_id():
    data = read_xml(xml().replace(b'<c:ID>TST2026000000001</c:ID>', b''))
    assert data.invoice_no == ''
    assert data.warnings


def test_html_labels_lines_and_localized_amount():
    data = read_html(html())
    assert data.invoice_no == 'TST2026000000001'
    assert data.payable_total == '1234.56'
    assert data.supplier_name == 'Örnek Test Tedarikçisi AŞ'
    assert data.lines[0].quantity == '2'
    assert data.lines[0].unit_price == '100.50'


def test_bundle_xml_has_priority_and_all_documents_persist(module, client):
    id = created(client, [('f.xml', xml()), ('g.html', html()), ('h.pdf', pdf())])
    detail = client.get(f'/api/fatura/{id}/detay').json
    assert detail['tutar'] == 361.8
    assert detail['vkn'] == '1234567890'
    assert len(detail['satirlar']) == 2
    with module.app.app_context():
        row = module.db.session.get(module.Fatura, id)
        sources = json.loads(row.kaynak_belgeler)
        assert len(sources) == 3
        assert all(digest(module.store.read(d['key'])) == d['sha256'] for d in sources)
        assert row.satirlar[0].miktar == Decimal('2')


@pytest.mark.parametrize('suffix,raw', [('.xml',xml()), ('.html',html()), ('.pdf',pdf())], ids=['xml','html','pdf'])
def test_individual_formats_open(client, suffix, raw):
    id = created(client, [('single'+suffix, raw)])
    assert client.get(f'/api/fatura/{id}/pdf').data.startswith(b'%PDF')
    assert client.get(f'/fatura/{id}/goruntule').status_code == 200


def test_approval_verifies_saved_pdf_and_preserves_lines(module, client):
    id = created(client)
    with module.app.app_context():
        old = module.db.session.get(module.Fatura, id).dosya_adi
        original = module.store.read(old)
    response = approve(client, id, kullanici_id=99999)
    assert response.status_code == 200, response.json
    assert response.json['damga_dogrulandi']
    client.get('/logout')
    assert client.post('/login',data={'ad_soyad':'Dilek Kaya','sifre':'Only-local-test-489!'}).status_code == 302
    detail = client.get(f'/api/fatura/{id}/detay').json
    assert detail['durum'] == 'onaylandi'
    assert detail['onaylayan_ad'] == 'Dilek Kaya'
    assert len(detail['satirlar']) == 2
    raw = client.get(f'/api/fatura/{id}/pdf').data
    text = ''.join(p.extract_text() for p in PdfReader(BytesIO(raw)).pages)
    assert 'ONAYLANDI' in text
    assert 'Türkçe onay notu' in text
    with module.app.app_context():
        row = module.db.session.get(module.Fatura, id)
        assert row.dosya_adi != old
        assert module.store.read(old) == original
        assert digest(raw) == row.pdf_hash


@pytest.mark.parametrize('stage', ['stamp','verify','write','reread','commit'])
def test_failed_approval_never_approves(module, client, monkeypatch, stage):
    id = created(client)
    with module.app.app_context():
        row = module.db.session.get(module.Fatura, id)
        original = row.dosya_adi
        note = row.not_alani
    def fail(*args, **kwargs):
        raise OSError('injected failure')
    if stage == 'stamp':
        monkeypatch.setattr(module, 'make_approval', fail)
    elif stage == 'verify':
        monkeypatch.setattr(module, 'verify_approval', lambda *args: False)
    elif stage == 'write':
        monkeypatch.setattr(module.store, 'put', fail)
    elif stage == 'commit':
        monkeypatch.setattr(module.db.session, 'commit', fail)
    else:
        read = module.store.read
        monkeypatch.setattr(module.store, 'read', lambda key: read(key) if key == original else b'%PDF-corrupt')
    response = approve(client, id)
    assert response.status_code == 400
    with module.app.app_context():
        module.db.session.remove()
        row = module.db.session.get(module.Fatura, id)
        assert row.durum == 'bekliyor'
        assert row.onaylayan_id is None
        assert row.onay_kimligi is None
        assert row.dosya_adi == original
        assert row.not_alani == note
        assert len(row.satirlar) == 2


def test_approved_record_is_immutable(client):
    id = created(client)
    assert approve(client,id).status_code == 200
    assert approve(client,id).status_code == 409
    assert client.post(f'/api/fatura/{id}/bilgi',json={'firma_adi':'bad'}).status_code == 409
    assert client.post(f'/api/fatura/{id}/aktar',json={'hedef_kullanici_id':1}).status_code == 409
    assert upload(client).status_code == 400
    assert client.get(f'/api/fatura/{id}/detay').json['firma_adi'] == 'Örnek Test Tedarikçisi AŞ'


@pytest.mark.parametrize('entries', [
    [('same.xml',xml()),('same.pdf',pdf('TST2026000000099'))],
    [('a.xml',xml()),('b.pdf',pdf('TST2026000000099'))],
    [('bad.xml', b'<Invoice>')],
    [('bad.xml', b'<!DOCTYPE Invoice [<!ENTITY x SYSTEM "file:///secret">]><Invoice>&x;</Invoice>')],
    [('same.xml',xml()),('other.xml',xml())],
    [('bad.pdf', b'not a pdf')],
    [('bad.exe', b'bad')],
])
def test_invalid_or_ambiguous_upload_is_atomic(module, client, entries):
    response = upload(client, entries)
    assert response.status_code == 400, response.json
    with module.app.app_context():
        assert module.Fatura.query.count() == 0
    assert list(module.store.root.iterdir()) == []


def test_filename_traversal_cannot_write_outside_store(module, client):
    created(client, [('../../unsafe.xml',xml())])
    assert all(p.parent == module.store.root for p in module.store.root.iterdir())
    assert not (module.DATA_DIR.parent / 'unsafe.xml').exists()


def test_cross_origin_and_private_document_access(module, client):
    id = created(client)
    anonymous = module.app.test_client()
    assert anonymous.get(f'/api/fatura/{id}/pdf').status_code == 302
    assert anonymous.get('/api/yonetim/kullanicilar').status_code == 403
    assert client.post(f'/api/fatura/{id}/onayla',json={},headers={'Origin':'https://attacker.invalid'}).status_code == 403
    with module.app.app_context():
        key = module.db.session.get(module.Fatura, id).dosya_adi
    assert anonymous.get('/static/uploads/'+key).status_code == 404


def test_isolation_health_and_default_password(module):
    assert 'do-not-connect' not in module.app.config['SQLALCHEMY_DATABASE_URI']
    assert module.SUPABASE_URL == '' and module.BULUT_MOD is False
    client = module.app.test_client()
    assert client.get('/health').json['application'] == 'genmar-fatura-onay-pro'
    assert client.post('/login',data={'ad_soyad':'Dilek Kaya','sifre':'1'}).status_code == 200
    assert client.get('/gelen').status_code == 302
    assert client.post('/login',data={'ad_soyad':'','sifre':'Only-local-test-489!'}).status_code == 200


def test_concurrent_approval_has_one_winner(module, client):
    id = created(client)
    def run(_):
        c = module.app.test_client()
        with c.session_transaction() as session:
            session['kullanici_id'] = 1
        return approve(c,id).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))
    assert results.count(200) == 1, results
    assert all(code in (200, 409) for code in results)


def test_project_selection_survives_approval(module, client):
    id = created(client)
    with module.app.app_context():
        project = module.AnaProje.query.first()
        child = module.AltProje.query.filter_by(ana_proje_id=project.id).first()
        selection = {'ana_proje_id':project.id, 'alt_proje_id':child.id}
    response = approve(client,id,projeler=[selection])
    assert response.status_code == 200, response.json
    detail = client.get(f'/api/fatura/{id}/detay')
    assert detail.status_code == 200
    assert detail.json['projeler'][0]['alt_proje_id'] == selection['alt_proje_id']


def test_private_assignment_hides_pdf_and_detail(module, client):
    id = created(client)
    with module.app.app_context():
        hidden = module.Kullanici(ad_soyad='Test Özel',atanan_faturalari_gizle=True)
        other = module.Kullanici(ad_soyad='Test Başka')
        module.db.session.add_all([hidden,other])
        module.db.session.flush()
        row = module.db.session.get(module.Fatura,id)
        row.atanan_id = hidden.id
        key, other_id = row.dosya_adi, other.id
        module.db.session.commit()
    other_client = module.app.test_client()
    with other_client.session_transaction() as session:
        session['kullanici_id'] = other_id
    for path in (f'/api/fatura/{id}/pdf',f'/api/fatura/{id}/detay',f'/uploads/{key}'):
        assert other_client.get(path).status_code == 404


def test_reader_ignores_line_tax_when_header_tax_missing():
    raw = xml().replace(b'<a:TaxTotal><c:TaxAmount>60.30</c:TaxAmount></a:TaxTotal>',b'')
    raw = raw.replace(b'<a:InvoiceLine>',b'<a:InvoiceLine><a:TaxTotal><c:TaxAmount>40.20</c:TaxAmount></a:TaxTotal>',1)
    assert read_xml(raw).tax_total is None
