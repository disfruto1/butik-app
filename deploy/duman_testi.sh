#!/usr/bin/env bash
# Yayin kurulumunu uctan uca dener: imaj, PostgreSQL, HTTPS ve gercek IP okuma.
# GitHub Actions'ta calisir. Veriyi siler, gercek sunucuda CALISTIRMAYIN.
set -euo pipefail

cd "$(dirname "$0")"

if [ -e .env ]; then
  echo "deploy/.env zaten var. Bu test gercek kurulumun yaninda calistirilmamali." >&2
  exit 1
fi

PROJE=butik-test
AG="${PROJE}_ic"
CURL_IMAJ=curlimages/curl:8.11.1
YABANCI="${PROJE}-yabanci"
CADDY_IMAJ=caddy:2.10-alpine
compose() { docker compose -p "$PROJE" -f docker-compose.yml -f docker-compose.test.yml "$@"; }

kapat() {
  sonuc=$?
  if [ "$sonuc" -ne 0 ]; then
    compose logs --tail=50 || true
  fi
  docker rm -f "$YABANCI" > /dev/null 2>&1 || true
  compose down -v --remove-orphans || true
  rm -f .env
  exit "$sonuc"
}
trap kapat EXIT

cat > .env <<EOF
ALAN_ADI=localhost
POSTGRES_PASSWORD=$(openssl rand -hex 24)
SECRET_KEY=$(openssl rand -hex 48)
EOF

basarisiz() {
  echo "BASARISIZ: $1" >&2
  exit 1
}

# Yanlis sifreyle giris dener, HTTP kodunu yazar.
# Test makinesinden gelir: bu kurulumda "Cloudflare" sayilan adres.
guvenilirden_giris() { # hesap, curl argumanlari...
  hesap=$1
  shift
  curl -4 -sk -o /dev/null -w '%{http_code}' --resolve localhost:443:127.0.0.1 \
    "$@" -d "username=$hesap&password=yanlis-sifre" https://localhost/giris
}

# Ag icindeki baska bir kapsayicidan gelir: guvenilir OLMAYAN adres. Sayac IP'ye bagli oldugu icin
# tum denemeler ayni kapsayicidan yapilir (her "docker run" yeni IP alabilir).
yabancidan_giris() { # hesap, adres, curl argumanlari...
  hesap=$1
  adres=$2
  shift 2
  docker exec "$YABANCI" curl -sk -o /dev/null -w '%{http_code}' \
    --resolve localhost:443:172.30.0.10 "$@" -d "username=$hesap&password=yanlis-sifre" "$adres"
}

echo "== Yapilandirma"
docker run --rm -e ALAN_ADI=localhost -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" "$CADDY_IMAJ" \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
caddy_json=$(docker run --rm -e ALAN_ADI=localhost -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" "$CADDY_IMAJ" \
  caddy adapt --config /etc/caddy/Caddyfile --adapter caddyfile 2>/dev/null)
for aralik in 173.245.48.0/20 131.0.72.0/22 2400:cb00::/32 2c0f:f248::/32; do
  case "$caddy_json" in
    *"\"$aralik\""*) ;;
    *) basarisiz "Cloudflare araligi Caddy ayarinda yok: $aralik" ;;
  esac
done

echo "== Kurulum"
compose up -d --build --wait --wait-timeout 180
docker run -d --name "$YABANCI" --network "$AG" --entrypoint sleep "$CURL_IMAJ" 600 > /dev/null

echo "== HTTPS uzerinden API"
curl -4 -skf --retry 10 --retry-all-errors --retry-delay 1 --resolve localhost:443:127.0.0.1 https://localhost/ \
  | grep -q calisiyor || basarisiz "API cevap vermedi"
kod=$(curl -4 -s -o /dev/null -w '%{http_code}' --resolve localhost:80:127.0.0.1 http://localhost/)
case "$kod" in
  30*) ;;
  *) basarisiz "HTTP adresi HTTPS'e yonlenmedi (kod $kod)" ;;
esac

echo "== PostgreSQL'e kayit ve giris"
kod=$(curl -4 -sk -o /dev/null -w '%{http_code}' --resolve localhost:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"ad":"Duman Testi","e_posta":"duman@yulamoda.com","sifre":"duman-sifre-123"}' https://localhost/kayit)
[ "$kod" = 200 ] || basarisiz "kayit olmadi (kod $kod)"
kod=$(curl -4 -sk -o /dev/null -w '%{http_code}' --resolve localhost:443:127.0.0.1 \
  -d 'username=duman@yulamoda.com&password=duman-sifre-123' https://localhost/giris)
[ "$kod" = 200 ] || basarisiz "giris olmadi (kod $kod)"

echo "== Cloudflare'den gelen farkli musteriler birbirini engellemez"
for i in 1 2 3 4 5 6 7; do
  kod=$(guvenilirden_giris musteri@ornek.com -H "CF-Connecting-IP: 203.0.113.$i")
  [ "$kod" = 401 ] || basarisiz "$i. musteri 401 yerine $kod aldi: gercek IP okunmuyor"
done

echo "== Cloudflare'den gelen ayni musteri X-Forwarded-For ile sinirdan kacamaz"
for i in 1 2 3 4 5; do
  kod=$(guvenilirden_giris xff@ornek.com -H 'CF-Connecting-IP: 203.0.113.100' -H "X-Forwarded-For: 198.51.100.$i")
  [ "$kod" = 401 ] || basarisiz "$i. deneme 401 yerine $kod aldi"
done
kod=$(guvenilirden_giris xff@ornek.com -H 'CF-Connecting-IP: 203.0.113.100' -H 'X-Forwarded-For: 198.51.100.6')
[ "$kod" = 429 ] || basarisiz "X-Forwarded-For ile sinir asildi (kod $kod)"

echo "== Cloudflare disindan sahte baslikla Caddy'ye gelen sinirdan kacamaz"
for i in 1 2 3 4 5; do
  kod=$(yabancidan_giris sahte@ornek.com https://localhost/giris -H "CF-Connecting-IP: 198.51.100.$i" -H "X-Forwarded-For: 198.51.100.$i")
  [ "$kod" = 401 ] || basarisiz "$i. deneme 401 yerine $kod aldi"
done
kod=$(yabancidan_giris sahte@ornek.com https://localhost/giris -H 'CF-Connecting-IP: 198.51.100.6' -H 'X-Forwarded-For: 198.51.100.6')
[ "$kod" = 429 ] || basarisiz "sahte CF-Connecting-IP ile sinir asildi (kod $kod)"

echo "== Caddy'yi atlayip uygulamaya gelen sahte baslik da gecmez"
for i in 1 2 3 4 5; do
  kod=$(yabancidan_giris dogrudan@ornek.com http://app:8000/giris -H "X-Forwarded-For: 198.51.100.$i")
  [ "$kod" = 401 ] || basarisiz "$i. deneme 401 yerine $kod aldi"
done
kod=$(yabancidan_giris dogrudan@ornek.com http://app:8000/giris -H 'X-Forwarded-For: 198.51.100.6')
[ "$kod" = 429 ] || basarisiz "uygulamaya dogrudan sahte baslikla sinir asildi (kod $kod)"

echo "== Disariya yalnizca Caddy acik, imaj temiz"
for port in 8000 5432; do
  # 7: baglanti reddedildi, 28: zaman asimi. Baska her sonuc portta birinin dinledigini gosterir.
  durum=0
  curl -4 -s -o /dev/null --connect-timeout 2 "http://127.0.0.1:$port/" || durum=$?
  case "$durum" in
    7|28) ;;
    *) basarisiz "$port portu disariya acik (curl sonucu $durum)" ;;
  esac
done
[ "$(compose exec -T app id -u)" != 0 ] || basarisiz "uygulama root olarak calisiyor"
compose exec -T app sh -c 'test ! -e .env && test ! -e tests' || basarisiz "imajda olmamasi gereken dosya var"

echo "TUM KONTROLLER GECTI"
