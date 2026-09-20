# GENMAR Fatura Onay Pro — V0.2 TEST

Bu sürüm, `genmaranonim-cloud/Genmar-fatura-onay-pro` deposunun `b952fc8` test dalından geliştirilmiştir. Eski `fatura-onay` deposunu, `fatura-onay-production` servisini, eski veritabanını ve belge deposunu kullanmaz. Logo entegrasyonu yoktur.

## Çalışan kapsam

- UBL XML okuyucu: fatura no, tarih, VKN/TCKN, para birimi, vergi/toplam ve satırların miktar, birim, fiyat, tutar bilgileri.
- HTML okuyucu: tanınan etiketler ve başlıklı satır tabloları. Tanınmayan alanlar uyarı olarak gösterilir; her tedarikçi şablonunun desteklendiği iddia edilmez.
- PDF metin katmanı okuyucu. Görüntü olarak taranmış PDF için OCR bulunmaz; kullanıcı eksik bilgileri tamamlar.
- ETTN/fatura no veya aynı dosya kökü ile PDF/XML/HTML eşleştirme. Çelişkili veya belirsiz toplu yükleme tamamen reddedilir. XML verisi önceliklidir.
- Orijinal belgeler ve yapılandırılmış satırlar ayrı, kalıcı saklanır. Aynı faturanın yeniden yüklenmesi mevcut kaydın üzerine yazmaz.
- XML/HTML tek başına yüklenebilir; görüntülemek için açıkça işaretlenmiş türetilmiş kontrol PDF'si üretilir.
- Onay, `onay_isleniyor → damga/not üret → doğrula → yeni dosyaya yaz → tekrar oku/doğrula → onaylandi` zinciridir. Hata, onay alanlarını ve durumu geri alır.
- İlk sayfada görünür damga, ek sayfalarda tam onay/ödeme notu ve onay kimliği. Orijinal PDF değişmez.
- Onay sonrası aynı fatura açık kalır; onaylı alanlar salt okunurdur. Sol/sağ tuş ve düğmeler manuel gezinir. Metin düzenlerken ok tuşları fatura değiştirmez.
- Mevcut GENMAR koyu ekran, fatura albümü, proje seçimi ve onay penceresi korunmuştur.

## İzole çalıştırma

Python 3.12 ile `pip install -r requirements.txt` ardından `python app.py` çalıştırılır. Yerel adres 127.0.0.1:5082'dir.

`PRO_DATA_DIR` yalnızca bu Pro uygulamasına ait boş/ayrı klasörü göstermelidir. Varsayılan `pro-data/` dizinidir. SQLite `genmar-pro.db`, orijinal belgeler, damgalı belgeler ve oturum anahtarı burada bulunur. Eski `DATABASE_URL`, Supabase ve Cloudinary değişkenleri kullanılmaz.

İlk kullanıcı Dilek Kaya'dır. `PRO_ADMIN_PASSWORD` ilk açılışta verilirse bu parola kullanılır. Verilmezse rastgele bir parola üretilir ve yalnızca veri klasöründeki `.initial-password` dosyasına yazılır; uygulama günlüklerine yazılmaz. Varsayılan `1` parolası kabul edilmez. Veri klasörü, parola ve oturum anahtarı Git'e/pakete dahil edilmez.

## Railway'de ayrı test yayını

1. Yeni, ayrı bir proje ve servis oluşturun; yalnızca bu depodaki `dev/pro-v02-integrated` dalını bağlayın.
2. Yeni bir kalıcı volume oluşturup `/data` konumuna bağlayın. Dockerfile `PRO_DATA_DIR=/data/genmar-pro` kullanır. Volume olmadan Railway'de uygulama başlamaz.
3. Yönetici için `PRO_ADMIN_PASSWORD` belirleyin; mevcut servisin değişkenlerini kopyalamayın. İlk kayıt oluştuktan sonra değişken değişikliği mevcut kullanıcı parolasını değiştirmez.
4. `/health` ve `/login` yanıtlarını, ardından giriş/yükleme/onay işlemini doğrulayın. Yeniden başlatma sonrasında kayıt ve belgeleri tekrar kontrol edin.
5. Bu kurulum tek servis/tek volume içindir. Yatay çoğaltma ve eski canlı verilerin aktarımı bu sürümün kapsamı dışındadır.

## Doğrulama

`pip install pytest` ve `python -m pytest -q`.

Testler yalnızca geçici veritabanları ve yapay faturalar kullanır. Okuyucu, dosya eşleştirme, kalıcı satırlar, belge bütünlüğü, uzun Türkçe notlar, onay hatalarında geri alma, eşzamanlı onay, tekrar yükleme, proje seçimi, özel fatura erişimi ve eski ortamdan izolasyon kapsanır.

20.09.2026 yerel tarayıcı kontrolünde: fatura penceresi, iki satırlı fatura, damganın görünmesi, onay sonrası aynı fatura, salt okunur alanlar, sağ/sol geçiş ve not alanında ok tuşlarının davranışı kontrol edildi. Güncel test sayısı test çıktısından doğrulanmalıdır.

Bu test sürümünde eski ağ klasörü tarama ve Excel ile mevcut belge üzerine yazma yolları kapalıdır. Eski canlıdaki faturalar, kullanıcılar ve projeler taşınmamıştır. Gerçek tedarikçi dosyalarıyla kabul testi ayrıca yapılmalıdır.
