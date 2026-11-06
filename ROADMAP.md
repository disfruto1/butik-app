# Butik App Yol Haritası

Teknoloji: FastAPI + SQLAlchemy + PostgreSQL (backend), Expo / React Native + React Navigation (frontend).

Durum işaretleri: `[x]` bitti, `[ ]` yapılacak.

---

## Faz 0 — Temel düzeltmeler (güvenlik ve yapılandırma)

- [x] `SECRET_KEY` koddan çıkarıldı, `.env` dosyasından okunuyor (eski anahtar repoda açıkta olduğu için **değiştirilmeli**)
- [x] API adresi tek yerde (`frontend/src/config.js`), `EXPO_PUBLIC_API_URL` ile ayarlanabiliyor
- [x] CORS izinli adresler `.env` ile ayarlanıyor (`ALLOWED_ORIGINS`)
- [x] Sipariş adedi ve şifre doğrulaması (adet 0 veya negatif olamaz)
- [x] Stok kontrolünde satır kilidi (aynı anda gelen siparişlerde fazla satışı önler)
- [x] Kullanılmayan `Kivy` ve bağımlılıkları `requirements.txt`'den çıkarıldı
- [x] `create_admin.py` ile ilk yönetici hesabı oluşturma
- [x] README, `.env.example` dosyaları
- [x] `AGENTS.md` projenin gerçek durumuna (React Navigation) uyduruldu

## Faz 1 — Müşteri akışı (frontend)

- [x] React Navigation ile ekran yapısı (giriş yapılmamış / giriş yapılmış)
- [x] Kayıt ol ekranı
- [x] Ürün listesi: yenileme, hata durumu, stok bilgisi
- [x] Ürün detay: adet seçimi, sepete ekle
- [x] Sepet: adet artır/azalt, kaldır, toplam, kargo adresi
- [x] Sipariş oluşturma ve "Siparişlerim" ekranı
- [x] Süresi dolan oturumda otomatik çıkış (401)

## Faz 2 — Ürün deneyimi

- [x] Kategori filtresi ve arama (backend: `GET /urunler?kategori_id=&q=`)
- [x] Ürün görselleri (yönetici görsel **bağlantısı** girer; dosya yükleme/depolama henüz yok)
- [x] Sayfalama (backend `limit/offset`, frontend sonsuz kaydırma)
- [x] Sepetin telefonda kalıcı olması (AsyncStorage)
- [x] Favoriler
- [x] Adres defteri (kayıtlı adresler, varsayılan adres, sepette seçim). Sipariş adresin metnini kopyalar, adres silinse de eski siparişler etkilenmez

## Faz 3 — Yönetici paneli

- [x] Yönetici rolüne özel ekranlar (rol bilgisi `/ben` ile alınır)
- [x] Ürün ekle / düzenle / pasife al, stok güncelle
- [x] Kategori yönetimi
- [x] Sipariş listesi ve durum güncelleme (`PATCH /siparisler/{id}/durum`)
- [x] Basit satış özeti (günlük sipariş sayısı ve ciro)

## Faz 4 — Ödeme ve kargo

- [x] PayTR kart ödemesi backend'i: ödeme başlatma, imzalı bildirim, süre aşımında iptal (`backend/paytr.py`). Gerçek PayTR ile henüz denenmedi
- [x] Sipariş durumunun ödeme sonucuna göre güncellenmesi (`odeme_bekliyor` → `odendi`)
- [x] Uygulamada kart ödeme ekranı (WebView) ve telefon alanı. Android'de sahte PayTR ile denendi; gerçek PayTR ve iOS'ta akış henüz denenmedi. **Havale/EFT** de duruyor: `ODEME_BILGISI` doluysa ödeme ekranında gösterilir, yönetici elle "Ödendi" yapar
- [ ] Yönetici panelinde ödeme sorunları ekranı (backend: `GET /yonetim/odeme-sorunlari`) ve iadenin PayTR API'siyle yapılması
- [x] Kargo takip numarası alanı ve müşteriye gösterimi
- [x] İptal ve iade akışı (stoğun geri eklenmesi)

## Faz 5 — Kalite ve yayına hazırlık

- [ ] Veritabanı değişiklikleri için Alembic migration'ları (şimdilik `backend/migrate.py` eksik kolonları ekliyor)
- [x] Backend testleri (pytest, 112 test; 11 eşzamanlılık testi yalnızca PostgreSQL'de çalışır, CI'da henüz atlanıyor). Frontend testleri henüz yok
- [ ] Refresh token veya daha uzun oturum stratejisi
- [x] Giriş denemesi koruması: 15 dakikada aynı IP'den aynı hesaba 5, aynı IP'den toplam 30 başarısız deneme (`backend/giris_siniri.py`)
- [ ] Genel istek sınırlama (kayıt ve diğer uçlar için rate limit)
- [x] Şifre sıfırlama (e-postayla 8 haneli kod, SMTP ile). Yayında çalışması için `SMTP_*` ayarları ve e-posta servisi gerekir
- [ ] Docker ile backend, HTTPS'li sunucuya yayın. Kurulum hazır ve CI'da deneniyor (`deploy/`), sunucu seçimi ve gerçek yayın bekliyor
- [x] CI (GitHub Actions): backend testleri çalışıyor (`.github/workflows/ci.yml`). Lint ve frontend kontrolleri henüz yok
- [ ] EAS ile Android/iOS build, mağaza hazırlığı
- [ ] Hata izleme (ör. Sentry)

## Faz 6 — Sonrası

- [ ] Push bildirimleri (sipariş durumu)
- [ ] Kupon ve kampanyalar
- [ ] Ürün yorumları ve puanlama
- [ ] Çoklu dil (TR/EN)

---

## Bilinen riskler

- Eski `SECRET_KEY` repo geçmişinde duruyor. Yerel `.env`'deki anahtar ondan farklı; yayın sunucusunda da mutlaka yeni bir anahtar üretilmeli.
- Sepet ve favoriler telefonda saklanır (hesaba bağlı değil), çıkış yapınca silinir. Fiyat ve stok her zaman sunucudan doğrulanır.
- Ödeme otomatik değil: yönetici havaleyi kontrol edip siparişi elle "Ödendi" yapmalı.
- Giriş sınırı IP adresine bakar. `deploy/` kurulumu bunu çözer (Caddy gerçek IP'yi okur, uygulama yalnızca Caddy'ye güvenir). Backend başka bir proxy arkasında çalıştırılırsa aynı ayar yapılmalı; yoksa tüm müşteriler aynı IP'den geliyor görünür ve birbirinin sınırını doldurur.
- Çok sayıda farklı IP'den tek hesaba yapılan denemeleri giriş sınırı durdurmaz. Yayında proxy veya servis sağlayıcı katmanında da koruma düşünülmeli.
- PayTR mağazası web sitesiyle paylaşılıyor. Paneldeki Bildirim URL'si değiştirilirse web sitesinin siparişleri onaylanmayabilir. Panelde ikinci adres tanımlanabiliyor, ama bildirimin hangi adrese gittiği henüz bilinmiyor; her bildirim ikisine de gidiyorsa uygulamanın web sitesi siparişlerine verdiği 404 düzeltilmeli. Uygulama siparişleri `BUTIK` önekiyle başlar, böylece bildirimler ayırt edilebilir.
- `PAYTR_TEST_MODU=1` iken para alınmaz ama sipariş "Ödendi" olur. Yayında 0 olmalı, yoksa ürün parası alınmadan kargolanabilir.
- Kart denenip vazgeçilen sipariş 45 dakika sonra iptal olur. Müşteri aynı siparişi sonradan havaleyle ödemek isterse yeni sipariş vermelidir.
- Yönetici "Ödendi" siparişi iptal ederse kart ücreti otomatik iade edilmez, PayTR panelinden iade gerekir.
- Şifre sıfırlama kodu e-posta servisi ayarlanana kadar gitmez: `SMTP_*` ayarları boşsa müşteri kod alamaz, uygulama yine de "gönderildi" der (hesap varlığı sızmasın diye). Yayından önce ayarlanmalı.
