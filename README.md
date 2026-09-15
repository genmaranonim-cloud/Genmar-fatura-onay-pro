# GENMAR Fatura Onay Pro (CA)

Eski `fatura-onay` uygulamasından bağımsız geliştirilen yeni sürüm.

## İlk çalışan paket

- PDF, UBL-TR XML ve HTML yükleme
- XML öncelikli alan ve fatura satırı okuma
- Okunan veriyi PDF'den bağımsız SQLite/PostgreSQL modelinde saklama
- Kullanıcı kontrolü için düzenlenebilir fatura ekranı
- Onay sonrası aynı faturada kalma
- Sol/sağ yön tuşlarıyla önceki/sonraki faturaya geçiş
- Onay damgasını üretme ve damgalı dosyayı doğrulama
- İşlem günlüğü

## Yerel çalıştırma

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
flask --app app run --debug
```

Tarayıcı: `http://127.0.0.1:5000`

## Ortam değişkenleri

- `DATABASE_URL`: Railway PostgreSQL bağlantısı (yoksa SQLite)
- `SECRET_KEY`: oturum güvenliği
- `UPLOAD_DIR`: belge dizini (varsayılan `uploads`)

> Üretimde kalıcı dosya saklama servisi bağlanmalıdır. İlk pakette dosyalar yerel diskte tutulur.

