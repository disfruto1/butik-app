# Butik App

Butik mağaza uygulaması: FastAPI backend + Expo / React Native mobil uygulama.
Yol haritası için [ROADMAP.md](ROADMAP.md) dosyasına bakın.

## Backend

Gereksinimler: Python 3.11+, PostgreSQL.

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # sonra .env içindeki değerleri doldurun
```

`.env` içinde **SECRET_KEY zorunludur**, tanımlı değilse uygulama açılmaz. Üretmek için:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Veritabanını oluşturup (tablolar ilk çalıştırmada otomatik açılır) sunucuyu başlatın:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API dokümantasyonu: http://127.0.0.1:8000/docs

İlk yönetici hesabı (kayıt olan herkes "müşteri" olur):

```bash
python create_admin.py yonetici@ornek.com "Ad Soyad"
```

Bu komut, e-posta zaten kayıtlıysa o kullanıcıyı yönetici yapar.

**Eski bir veritabanınız varsa:** uygulama açılırken yeni kolonları (ürün görseli, kargo takip no) kendisi ekler
(`migrate.py`), mevcut verilere dokunmaz. Yine de ilk çalıştırmadan önce yedek almanız önerilir:

```bash
pg_dump butik_db > ~/butik_yedek.sql
```

**Havale/EFT bilgisi:** `.env` içindeki `ODEME_BILGISI` satırı, müşteriye sipariş sonrası gösterilir.
Ödeme otomatik doğrulanmaz, yönetici paneli > Siparişler ekranından siparişi elle "Ödendi" yaparsınız.

**Giriş sınırı:** 15 dakikada aynı IP'den aynı hesaba 5, aynı IP'den toplam 30 başarısız denemeden sonra giriş geçici olarak kapanır (`giris_siniri.py`). Backend bir proxy arkasında yayınlanacaksa [ROADMAP.md](ROADMAP.md) içindeki "Bilinen riskler" bölümüne bakın.

**Şifre sıfırlama:** kullanıcı "Şifremi unuttum" ile e-postasına 8 haneli kod alır (15 dakika geçerli, 5 yanlış denemede iptal). Şifre değişince o hesabın eski oturumları kapanır. E-posta göndermek için `.env` içindeki `SMTP_*` satırlarını doldurun. Doldurulmazsa kod gitmez; geliştirmede `EPOSTA_KONSOLA_YAZ=1` ile kodu sunucu çıktısında görebilirsiniz (yayında açmayın).

**Kart ödemesi (PayTR):** backend hazır, uygulama ekranı henüz yok. `.env` içindeki `PAYTR_*` satırları boşsa kart ödemesi kapalıdır. Sipariş yalnızca PayTR'ın imzalı bildirimiyle "Ödendi" olur (`POST /odeme/paytr/bildirim`). Bu adres PayTR panelindeki Bildirim URL'si olmalıdır; panel aynı mağazayı kullanan başka bir siteye bağlıysa **değiştirmeden önce** [ROADMAP.md](ROADMAP.md) içindeki "Bilinen riskler" bölümüne bakın. Son denemesinin üzerinden 45 dakika geçen ve para alınmamış kart siparişleri otomatik iptal olur, stok geri döner. Hiç kart denenmemiş siparişlere (havale) dokunulmaz. Para alınıp siparişe işlenemeyen ödemeler `GET /yonetim/odeme-sorunlari` ile listelenir; iade PayTR panelinden elle yapılır.

**Testler** (gerçek veritabanına dokunmaz, geçici SQLite kullanır):

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Eşzamanlılık testleri satır kilidi gerektirdiği için SQLite'ta atlanır. Hepsini PostgreSQL'de çalıştırmak için ayrı bir deneme veritabanı açın. Testler tabloları sildiği için adında "test" geçmeyen veritabanı reddedilir:

```bash
createdb butik_test
TEST_DATABASE_URL=postgresql+psycopg2:///butik_test python -m pytest -q
```

## Yönetici paneli

Yönetici hesabıyla girince ürün listesinde **Yönetim** bağlantısı görünür: bugünkü sipariş ve ciro özeti,
düşük stok uyarısı, sipariş durumu güncelleme (kargo takip no dahil), ürün ve kategori yönetimi.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env            # gerçek telefonda test için EXPO_PUBLIC_API_URL'i doldurun
npx expo start
```

Gerçek telefonda API adresi için `frontend/.env.example` içindeki açıklamalara bakın. Üretimde (yayında) HTTPS bir adres kullanılmalıdır.
