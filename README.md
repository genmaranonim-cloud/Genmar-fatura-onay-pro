# GENMAR Fatura Onay Pro (CA)

Mevcut GENMAR Fatura Onay uygulamasının çalışan sürümüne dokunmadan geliştirilen yeni sürüm.

## V1 hedefi
- Kullanıcı girişi ve rol/yetki yapısı
- Gelen faturalar
- Kullanıcı/departman atama
- Ana/alt ve çoklu proje seçimi
- PDF görüntüleme
- Onay/red akışı
- PDF üzerine onay damgası
- Muhasebe kontrolü
- Yönetici tarafından süreç sonlandırma
- İşlem geçmişi (audit log)
- Sonlandırılan faturalar
- Arama/filtreleme
- Excel aktarımı

## Korunacak mevcut özellikler
- PostgreSQL / lokal SQLite desteği
- Supabase Storage ve eski Cloudinary kayıt uyumluluğu
- PDF not alanından kullanıcı eşleştirme
- Türkçe karakter desteği
- Standart proje kırılımları
- Çoklu proje satırları

## Değişiklik ilkesi
Eski `genmaranonim-cloud/fatura-onay` repository'si ve Railway'deki çalışan uygulama değiştirilmez. Yeni geliştirmeler yalnızca bu repository'de yapılır.

## Durum
V1 başlangıç yapısı oluşturuldu — 15.09.2026.
