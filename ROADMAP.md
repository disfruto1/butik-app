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
- [ ] Adres defteri (kayıtlı adresler). Şimdilik adres her siparişte elle yazılıyor

## Faz 3 — Yönetici paneli

- [x] Yönetici rolüne özel ekranlar (rol bilgisi `/ben` ile alınır)
- [x] Ürün ekle / düzenle / pasife al, stok güncelle
- [x] Kategori yönetimi
- [x] Sipariş listesi ve durum güncelleme (`PATCH /siparisler/{id}/durum`)
- [x] Basit satış özeti (günlük sipariş sayısı ve ciro)

## Faz 4 — Ödeme ve kargo

- [ ] Kart ile ödeme: sağlayıcı seçimi (Türkiye için iyzico veya PayTR) ve entegrasyonu. Şimdilik **havale/EFT**: sipariş sonrası `ODEME_BILGISI` gösteriliyor, yönetici ödemeyi elle "Ödendi" yapıyor
- [ ] Sipariş durumunun ödeme sonucuna göre güncellenmesi (`odeme_bekliyor` → `odendi`)
- [x] Kargo takip numarası alanı ve müşteriye gösterimi
- [x] İptal ve iade akışı (stoğun geri eklenmesi)

## Faz 5 — Kalite ve yayına hazırlık

- [ ] Veritabanı değişiklikleri için Alembic migration'ları (şimdilik `backend/migrate.py` eksik kolonları ekliyor)
- [x] Backend testleri (pytest, 16 test). Frontend testleri henüz yok
- [ ] Refresh token veya daha uzun oturum stratejisi
- [ ] İstek sınırlama (rate limit), giriş denemesi koruması
- [ ] Şifre sıfırlama (e-posta ile)
- [ ] Docker ile backend, HTTPS'li sunucuya yayın
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

- Eski `SECRET_KEY` repo geçmişinde duruyor. Yeni bir anahtar üretilmeli, eskisiyle imzalanmış tüm tokenlar geçersiz sayılır.
- Sepet ve favoriler telefonda saklanır (hesaba bağlı değil), çıkış yapınca silinir. Fiyat ve stok her zaman sunucudan doğrulanır.
- Ödeme otomatik değil: yönetici havaleyi kontrol edip siparişi elle "Ödendi" yapmalı.
- Girişte deneme sınırı (rate limit) yok. Yayına çıkmadan eklenmeli (Faz 5).
