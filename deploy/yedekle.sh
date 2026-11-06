#!/usr/bin/env bash
# Veritabani yedegi alir, 14 gunden eski yedekleri siler. Gunluk cron icin: deploy/YAYIN.md
set -euo pipefail
umask 077

cd "$(dirname "$0")"
mkdir -p yedekler

dosya="yedekler/butik_$(date +%Y-%m-%d_%H%M).sql.gz"
docker compose exec -T db pg_dump -U butik butik_db | gzip > "$dosya.gecici"
mv "$dosya.gecici" "$dosya"

# Eskiler yalnizca yeni yedek basariyla alindiysa silinir (set -e)
find yedekler -name 'butik_*.sql.gz' -mtime +14 -delete
echo "Yedek alindi: $dosya"
