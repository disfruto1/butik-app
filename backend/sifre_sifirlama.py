"""E-postayla gelen kodla sifre sifirlama.

Kod rastgele ve 8 hanelidir, 15 dakika gecerlidir, 5 yanlis denemede iptal olur ve
veritabaninda yalnizca HMAC ozeti saklanir. Ayni e-postaya 15 dakikada en fazla 3 kod
gonderilir (baskasinin posta kutusu doldurulamasin). 15 dakikada en fazla 15 tahmin ve
100 milyon olasilikla kod tahmin etmek pratik degildir.
"""
import hashlib
import hmac
import secrets
import time

from sqlalchemy.orm import Session

from auth import SECRET_KEY
from models import SifreSifirlamaKodu

KOD_SURESI_SANIYE = 15 * 60
KOD_DENEME_SINIRI = 5


def _simdi() -> int:
    return int(time.time())


def _ozet(kullanici_id: int, kod: str) -> str:
    return hmac.new(SECRET_KEY.encode(), f"{kullanici_id}:{kod}".encode(), hashlib.sha256).hexdigest()


def kod_olustur(db: Session, kullanici_id: int) -> str:
    """Yeni kod uretir, kullanicinin onceki kodunu gecersiz kilar."""
    kod = f"{secrets.randbelow(100_000_000):08d}"
    kayit = db.query(SifreSifirlamaKodu).filter(SifreSifirlamaKodu.kullanici_id == kullanici_id).with_for_update().first()
    if kayit is None:
        kayit = SifreSifirlamaKodu(kullanici_id=kullanici_id)
        db.add(kayit)
    kayit.kod_ozeti = _ozet(kullanici_id, kod)
    kayit.son_kullanma = _simdi() + KOD_SURESI_SANIYE
    kayit.yanlis_deneme = 0
    db.commit()
    return kod


def kodu_dogrula_ve_harca(db: Session, kullanici_id: int, kod: str) -> bool:
    """Kod dogruysa kaydi siler ve True doner. Commit etmez: sifre degisikligiyle ayni islemde yazilir.
    Yanlissa sayaci kendi commit'iyle arttirir. Satir kilidi ayni anda gelen tahminlerin siniri asmasini onler."""
    kayit = db.query(SifreSifirlamaKodu).filter(SifreSifirlamaKodu.kullanici_id == kullanici_id).with_for_update().first()
    if kayit is None:
        db.rollback()
        return False
    if kayit.son_kullanma <= _simdi() or kayit.yanlis_deneme >= KOD_DENEME_SINIRI:
        db.delete(kayit)
        db.commit()
        return False
    if not hmac.compare_digest(kayit.kod_ozeti, _ozet(kullanici_id, kod)):
        kayit.yanlis_deneme += 1
        if kayit.yanlis_deneme >= KOD_DENEME_SINIRI:
            db.delete(kayit)
        db.commit()
        return False
    db.delete(kayit)
    return True
