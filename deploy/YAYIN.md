# Yayın rehberi

Kurulum: internet → (Cloudflare) → Caddy (HTTPS) → uygulama → PostgreSQL. Üçü de aynı sunucuda Docker ile çalışır, dışarıya yalnızca Caddy açıktır.

## 1. Sunucu

- Ubuntu 24.04, en az 2 GB RAM, root erişimi. 80 ve 443 portları açık olmalı.
- Docker kurulumu: <https://docs.docker.com/engine/install/ubuntu/>
- Sunucuda SSH'ı parola yerine anahtarla kullanın.

## 2. DNS

`api.yulamoda.com` için sitenin bağlı olduğu Cloudflare hesabına tek kayıt eklenir:

| Tür | Ad | Değer | Proxy |
|---|---|---|---|
| A | `api` | sunucunun IP'si | **DNS only** (gri bulut) |

**Neden gri bulut:** turuncu bulutta Cloudflare'in güvenlik kuralları PayTR bildirimini engelleyebilir ve alanın SSL modu "Flexible" ise sonsuz yönlendirme olur. Bu SSL ayarı tüm alanı etkilediği için sitenin kendisi için değiştirmek riskli.

**Sonradan turuncuya geçmek isterseniz:** kurulum değişmeden çalışır, müşteri IP'si `CF-Connecting-IP`'den doğru okunur. Önce şunlar sağlanmalı: SSL modu "Full (strict)", `/odeme/paytr/bildirim` için WAF ve bot korumasından muafiyet. Cloudflare adres listesi `Caddyfile` içinde sabittir, turuncudayken ara sıra <https://www.cloudflare.com/ips> ile karşılaştırın.

Alan adının nameserver'larına dokunmayın: alan adı `grant`/`miki` sunucularında, site oradan çalışıyor.

## 3. Kurulum

```bash
git clone https://github.com/disfruto1/butik-app.git
cd butik-app/deploy
cp .env.example .env
chmod 600 .env
nano .env
```

`.env` içinde `POSTGRES_PASSWORD`, `SECRET_KEY`, `SMTP_SIFRE`, `ODEME_BILGISI` doldurulur. `SECRET_KEY` yerel makinedekinden farklı olmalı. PayTR alanları ilk açılışta boş kalabilir, kart ödemesi kapalı başlar.

```bash
docker compose up -d --build
docker compose ps
curl https://api.yulamoda.com/
```

İlk açılışta sertifika alınması bir dakika sürebilir. Sorun olursa: `docker compose logs caddy` veya `docker compose logs app`.

İlk yönetici hesabı (şifre gizli sorulur):

```bash
docker compose exec app python create_admin.py e-posta@adresiniz.com "Ad Soyad"
```

Yerel veritabanındaki veriler taşınacaksa, uygulama hiç kullanılmadan önce:

```bash
gunzip -c yedek.sql.gz | docker compose exec -T db psql -U butik butik_db
```

## 4. Yedek

Sunucuda `crontab -e` ile her gece 03:30 yedeği:

```
30 3 * * * /home/KULLANICI/butik-app/deploy/yedekle.sh >> /home/KULLANICI/butik-yedek.log 2>&1
```

Yedekler `deploy/yedekler/` altında 14 gün kalır. **Sunucu giderse bunlar da gider:** düzenli olarak başka bir yere de kopyalayın ve en az bir kez geri yüklemeyi deneyin.

## 5. E-posta kontrolü

1. Resend panelinde `yulamoda.com` "Verified" görünmeli.
2. Uygulamada "Şifremi unuttum" deneyin; kod gelen kutusuna düşmeli, spam'e bakın.

## 6. PayTR'a geçiş

Web sitesinin ödemeleri aynı mağazadan geçiyor. **Paneldeki mevcut Bildirim URL'sini değiştirmeyin.**

1. PayTR'dan öğrenin: iki bildirim adresi olunca bildirim hangisine gidiyor? Her bildirim ikisine de gidiyorsa, uygulamanın web sitesi siparişlerine verdiği 404 cevabı düzeltilmeden açmayın.
2. İkinci adres olarak ekleyin: `https://api.yulamoda.com/odeme/paytr/bildirim`
3. `.env` içine `PAYTR_MERCHANT_ID`, `PAYTR_MERCHANT_KEY`, `PAYTR_MERCHANT_SALT` yazın, `PAYTR_TEST_MODU=1` bırakın, `docker compose up -d` çalıştırın.
4. Telefonda PayTR'ın test kartıyla baştan sona deneyin: başarılı ödeme, reddedilen kart, vazgeçme. Sipariş "Ödendi" olmalı, web sitesinin ödemeleri etkilenmemeli.
5. Her şey doğruysa `PAYTR_TEST_MODU=0` yapın, `docker compose up -d` çalıştırın ve küçük tutarlı gerçek bir ödemeyle deneyip iade edin.

Test modunda sipariş "Ödendi" olur ama para alınmaz. Test siparişlerini kargolamayın, gerçek satışa `0` yapmadan başlamayın.

## 7. Uygulama

`frontend/.env` içinde `EXPO_PUBLIC_API_URL=https://api.yulamoda.com` ile build alınır (EAS ve mağaza hazırlığı ayrı iştir, bkz. ROADMAP). Android ve iOS mağaza süreci başlamadan önce gizlilik politikası ve mesafeli satış sözleşmesi gerekir.

## Yayın öncesi kontrol

- [ ] `SECRET_KEY` yeni üretildi, `.env` izinleri 600
- [ ] `EPOSTA_KONSOLA_YAZ` ve `PAYTR_YEREL_IP` boş
- [ ] `ODEME_BILGISI` gerçek IBAN'ı gösteriyor
- [ ] `https://api.yulamoda.com/` cevap veriyor, HTTP adresi HTTPS'e yönleniyor
- [ ] Sunucudan dışarıya 5432 ve 8000 portları kapalı (başka bir makineden deneyin)
- [ ] Şifre sıfırlama e-postası geliyor
- [ ] Yedek alındı ve geri yüklemesi denendi
- [ ] PayTR test ödemesi tamamlandı, web sitesi ödemeleri etkilenmedi
- [ ] Gerçek satışta `PAYTR_TEST_MODU=0`

## Güncelleme ve geri alma

Güncelleme öncesi yedek alın:

```bash
cd butik-app/deploy
./yedekle.sh
git pull
docker compose up -d --build
```

Sorun çıkarsa önceki commit'e dönün (`git checkout <commit>` ve `docker compose up -d --build`). Uygulama açılırken yalnızca eksik tablo ve kolon ekler, eski sürüm bunlarla çalışmaya devam eder.

## Bilinen sınırlar

- `deploy/duman_testi.sh` bu kurulumu GitHub Actions'ta her push'ta dener: imaj, PostgreSQL, HTTPS, gerçek IP okuma, sahte başlıklar. Gerçek Let's Encrypt sertifikası, gerçek Cloudflare ve gerçek PayTR bu testin dışındadır; sunucuda bu rehberle denenmelidir. **`duman_testi.sh` veriyi siler, sunucuda çalıştırmayın.**
- Tek sunucu, tek uygulama süreci: sunucu kapanırsa uygulama da kapanır. Butik ölçeği için yeterli.
