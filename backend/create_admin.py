"""Ilk yonetici hesabini olusturur (veya var olan bir kullaniciyi yonetici yapar).

Kullanim (backend klasorunden):
    python create_admin.py ornek@eposta.com "Ad Soyad"

Sifre komut satirina yazilmaz, istenince gizli girilir.
"""
import getpass
import sys

import models
from auth import sifreyi_hashle
from database import SessionLocal, engine
from models import Kullanici, KullaniciRol


def main():
    if len(sys.argv) < 2:
        print('Kullanim: python create_admin.py e_posta ["Ad Soyad"]')
        sys.exit(1)

    e_posta = sys.argv[1].strip().lower()
    ad = sys.argv[2] if len(sys.argv) > 2 else "Yonetici"

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        kullanici = db.query(Kullanici).filter(Kullanici.e_posta == e_posta).first()
        if kullanici:
            kullanici.rol = KullaniciRol.YONETICI
            db.commit()
            print(f"{e_posta} artik yonetici.")
            return

        sifre = getpass.getpass("Sifre (en az 6 karakter): ")
        if len(sifre) < 6 or len(sifre) > 72:
            print("Sifre 6-72 karakter arasinda olmali.")
            sys.exit(1)
        if sifre != getpass.getpass("Sifre (tekrar): "):
            print("Sifreler eslesmiyor.")
            sys.exit(1)

        db.add(Kullanici(ad=ad, e_posta=e_posta, sifre_hash=sifreyi_hashle(sifre), rol=KullaniciRol.YONETICI))
        db.commit()
        print(f"Yonetici olusturuldu: {e_posta}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
