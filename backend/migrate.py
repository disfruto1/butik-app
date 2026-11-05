"""Mevcut PostgreSQL veritabanina sonradan eklenen kolonlari tamamlar.

`create_all` sadece eksik TABLOLARI olusturur, var olan tabloya yeni kolon eklemez.
Bu yuzden eski veritabani (ornegin butik_db) yeni surumle calissin diye kolonlar burada,
"IF NOT EXISTS" ile (tekrar tekrar calistirilsa da zarar vermeden) eklenir.
Ileride degisiklikler cogalirsa Alembic'e gecilmeli (bkz. ROADMAP.md).
"""
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

# (tablo, kolon, tip). Sadece sabit degerler, disaridan veri almaz.
EKLENECEK_KOLONLAR = [
    ("urunler", "gorsel_url", "VARCHAR(500)"),
    ("siparisler", "takip_no", "VARCHAR(100)"),
    ("kullanicilar", "token_surumu", "INTEGER NOT NULL DEFAULT 0"),
    ("kullanicilar", "telefon", "VARCHAR(20)"),
]


def kolonlari_tamamla(engine):
    if engine.dialect.name != "postgresql":
        return
    for tablo, kolon, tip in EKLENECEK_KOLONLAR:
        sql = f"ALTER TABLE {tablo} ADD COLUMN IF NOT EXISTS {kolon} {tip}"
        try:
            with engine.begin() as baglanti:
                baglanti.execute(text(sql))
        except ProgrammingError as hata:
            # Genelde tabloyu baska bir veritabani kullanicisi olusturmustur ("must be owner of table").
            raise RuntimeError(
                f"Veritabani guncellenemedi: '{sql}' calistirilamadi.\n"
                "Tablonun sahibi olan kullaniciyla su komutu elle calistirin, sonra uygulamayi tekrar baslatin:\n"
                f'  psql butik_db -c "{sql};"\n'
                f"Ayrinti: {hata.orig}"
            ) from hata
