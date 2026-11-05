"""Basarisiz giris denemelerini sinirlar (sifre deneme saldirilarina karsi).

Iki sayac tutulur, biri dolunca o istek reddedilir:
  - hesap + IP: ayni IP'den ayni hesaba deneme. Sadece e-postaya gore sayilsaydi,
    herhangi biri baskasinin hesabini yanlis sifreyle kilitleyebilirdi.
  - IP: ayni IP'den farkli hesaplara deneme (sizdirilmis sifre listeleri).

Sayaclar veritabaninda durur: sunucu yeniden baslasa da silinmez, birden fazla
worker ayni sayaci gorur. Anahtarlar hash'lidir, cunku kullanicilar e-posta
alanina yanlislikla sifre de yazabilir; bunlar duz metin saklanmamali.
Yalnizca basarisiz denemeler sayilir, ayni IP'yi paylasan normal musteriler
(ornegin mobil operator agi) basarili girislerle etkilenmez.
"""
import hashlib
import time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import GirisDenemesi

PENCERE_SANIYE = 15 * 60
HESAP_SINIRI = 5
IP_SINIRI = 30


def _simdi() -> int:
    return int(time.time())


def _anahtar(tur: str, deger: str) -> str:
    return hashlib.sha256(f"{tur}:{deger}".encode()).hexdigest()


def _hesap_anahtari(e_posta: str, ip: str) -> str:
    return _anahtar("hesap", f"{e_posta}|{ip}")


def _sayaclar(e_posta: str, ip: str) -> list[tuple[str, int]]:
    return [(_hesap_anahtari(e_posta, ip), HESAP_SINIRI), (_anahtar("ip", ip), IP_SINIRI)]


def kilit_suresi(db: Session, e_posta: str, ip: str) -> int:
    """Kilit varsa kac saniye kaldigini, yoksa 0 dondurur."""
    simdi = _simdi()
    kalan = 0
    for anahtar, sinir in _sayaclar(e_posta, ip):
        kayit = db.get(GirisDenemesi, anahtar)
        if kayit and kayit.sayi >= sinir:
            kalan = max(kalan, kayit.pencere_basi + PENCERE_SANIYE - simdi)
    return max(kalan, 0)


def _sayaclari_arttir(db: Session, e_posta: str, ip: str) -> None:
    simdi = _simdi()
    for anahtar, _ in _sayaclar(e_posta, ip):
        kayit = db.query(GirisDenemesi).filter(GirisDenemesi.anahtar == anahtar).with_for_update().first()
        if kayit is None:
            db.add(GirisDenemesi(anahtar=anahtar, sayi=1, pencere_basi=simdi))
            db.flush()
        elif kayit.pencere_basi + PENCERE_SANIYE <= simdi:
            kayit.sayi = 1
            kayit.pencere_basi = simdi
        else:
            kayit.sayi += 1
    db.flush()  # autoflush kapali: yenilenen sayaclar yazilmadan silme calisirsa onlari da siler
    # Suresi dolan kayitlar tablo buyumesin diye silinir
    db.query(GirisDenemesi).filter(GirisDenemesi.pencere_basi + PENCERE_SANIYE <= simdi).delete(synchronize_session=False)
    db.commit()


def basarisiz_giris(db: Session, e_posta: str, ip: str) -> None:
    try:
        _sayaclari_arttir(db, e_posta, ip)
    except IntegrityError:
        # Ayni anda gelen baska bir istek kaydi once acti: var olan kayit uzerinden tekrar say
        db.rollback()
        _sayaclari_arttir(db, e_posta, ip)


def basarili_giris(db: Session, e_posta: str, ip: str) -> None:
    """Hesap sayacini sifirlar. IP sayaci kalir: yoksa saldirgan kendi hesabina girerek onu sifirlayabilirdi."""
    db.query(GirisDenemesi).filter(GirisDenemesi.anahtar == _hesap_anahtari(e_posta, ip)).delete(synchronize_session=False)
    db.commit()
