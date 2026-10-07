def test_manager_sees_delete_button_and_can_delete_document(module, client):
    with module.app.app_context():
        key = module.store.put(b'%PDF-test')
        invoice = module.Fatura(dosya_adi=key, orijinal_pdf=key,
                                 fatura_no='DEL-1', firma_adi='Silinecek')
        module.db.session.add(invoice)
        module.db.session.commit()
        invoice_id = invoice.id
        path = module.store.path(key)

    page = client.get('/gelen?durum=tum')
    assert page.status_code == 200
    assert f'faturaSil({invoice_id}, event)'.encode() in page.data
    assert client.delete(f'/api/fatura/{invoice_id}').status_code == 200
    assert not path.exists()


def test_manager_can_authorize_user_for_multiple_departments(module, client):
    with module.app.app_context():
        departments = module.Departman.query.order_by(module.Departman.id).limit(3).all()
        assert len(departments) >= 3
        primary_id = departments[0].id
        user = module.Kullanici(ad_soyad='Yetki Test Kullanıcısı',
                                departman_id=primary_id)
        module.db.session.add(user)
        module.db.session.flush()
        user_id = user.id
        allowed_id, blocked_id = departments[1].id, departments[2].id
        allowed = module.Fatura(dosya_adi='allowed.pdf', fatura_no='ALLOW',
                                departman_id=allowed_id)
        blocked = module.Fatura(dosya_adi='blocked.pdf', fatura_no='BLOCK',
                                departman_id=blocked_id)
        module.db.session.add_all([allowed, blocked])
        module.db.session.commit()
        allowed_invoice_id, blocked_invoice_id = allowed.id, blocked.id

    response = client.post(f'/api/yonetim/kullanici-guncelle/{user_id}', json={
        'ad_soyad': 'Yetki Test Kullanıcısı', 'email': '',
        'departman_id': primary_id,
        'yetkili_departman_idleri': [allowed_id],
    })
    assert response.status_code == 200

    other = module.app.test_client()
    with other.session_transaction() as session:
        session['kullanici_id'] = user_id
    assert other.get(f'/api/fatura/{allowed_invoice_id}/detay').status_code == 200
    assert other.get(f'/api/fatura/{blocked_invoice_id}/detay').status_code == 404


def test_waiting_invoice_is_listed_in_accounting_and_line_note_persists(module, client):
    with module.app.app_context():
        invoice = module.Fatura(dosya_adi='waiting.pdf', fatura_no='WAIT-1',
                                 firma_adi='Bekleyen Firma', durum='bekliyor')
        invoice.satirlar.append(module.FaturaSatir(sira=1, aciklama='Pompa'))
        module.db.session.add(invoice)
        module.db.session.commit()
        invoice_id, line_id = invoice.id, invoice.satirlar[0].id

    accounting = client.get('/muhasebe')
    assert accounting.status_code == 200
    assert b'WAIT-1' in accounting.data
    assert 'Bekliyor'.encode() in accounting.data

    response = client.patch(f'/api/fatura/{invoice_id}/satir/{line_id}/not',
                            json={'not_alani': 'Ölçü kontrol edilecek'})
    assert response.status_code == 200
    detail = client.get(f'/api/fatura/{invoice_id}/detay').json
    assert detail['satirlar'][0]['not_alani'] == 'Ölçü kontrol edilecek'
