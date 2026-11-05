"""Basarisiz giris denemelerini sinirlar (sifre deneme saldirilarina karsi).

Iki sayac tutulur, biri dolunca o istek reddedilir:
  - hesap + IP: ayni IP'den ayni hesaba deneme. Sadece e-postaya gore sayilsaydi,
    herhangi biri baskasinin hesabini yanlis sifreyle kilitleyebilirdi.
  - IP: ayni IP'den farkli hesaplara deneme (sizdirilmis sifre listeleri).

Sayac sifre kontrolunden ONCE ve satir kilidiyle arttirilir (deneme_baslat), basarili
giriste geri alinir (basarili_giris). Sonradan arttirilsaydi, ayni anda gelen istekler
sifre kontrolu suresince sayaci gormeden sinirin cok otesine gecebilirdi.

Sayaclar veritabaninda durur: sunucu yeniden baslasa da silinmez, birden fazla
worker ayni sayaci gorur. Anahtarlar hash'lidir, cunku kullanicilar e-posta
alanina yanlislikla sifre de yazabilir; bunlar duz metin saklanmamali.
Basarili girisler sayilmaz, ayni IP'yi paylasan normal musteriler (ornegin mobil
operator agi) birbirini etkilemez.
"""
import hashlib
import time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import GirisDenemesi

PENCERE_SANIYE = 15 * 60
HESAP_SINIRI = 5
IP_SINIRI = 30
_TEKRAR = 3  # ayni anda acilan ilk kayit carpismasi icin deneme sayisi


def _simdi() -> int:
    return int(time.time())


def _anahtar(tur: str, deger: str) -> str:
    return hashlib.sha256(f"{tur}:{deger}".encode()).hexdigest()


def _hesap_anahtari(e_posta: str, ip: str) -> str:
    return _anahtar("hesap", f"{e_posta}|{ip}")


def _ip_anahtari(ip: str) -> str:
    return _anahtar("ip", ip)


def _kilitli_getir(db: Session, anahtar: str):
    return db.query(GirisDenemesi).filter(GirisDenemesi.anahtar == anahtar).with_for_update().first()


def _dene(db: Session, e_posta: str, ip: str) -> int:
    simdi = _simdi()
    # Kilit sirasi her istekte ayni (hesap, sonra IP): kilitlenme (deadlock) olmaz
    sayaclar = [
        (_hesap_anahtari(e_posta, ip), HESAP_SINIRI),
        (_ip_anahtari(ip), IP_SINIRI),
    ]
    kayitlar = [(anahtar, sinir, _kilitli_getir(db, anahtar)) for anahtar, sinir in sayaclar]

    kalan = 0
    for _, sinir, kayit in kayitlar:
        if kayit and kayit.pencere_basi + PENCERE_SANIYE > simdi and kayit.sayi >= sinir:
            kalan = max(kalan, kayit.pencere_basi + PENCERE_SANIYE - simdi)
    if kalan:
        db.rollback()
        return kalan

    for anahtar, _, kayit in kayitlar:
        if kayit is None:
            db.add(GirisDenemesi(anahtar=anahtar, sayi=1, pencere_basi=simdi))
            db.flush()
        elif kayit.pencere_basi + PENCERE_SANIYE <= simdi:
            kayit.sayi = 1
            kayit.pencere_basi = simdi
        else:
            kayit.sayi += 1
    db.commit()
    return 0


def _eskileri_sil(db: Session) -> None:
    """Suresi dolan kayitlar tablo buyumesin diye silinir. Baska isteklerin tuttugu satirlari beklemez."""
    sinir = _simdi() - PENCERE_SANIYE
    eskiler = (
        db.query(GirisDenemesi.anahtar)
        .filter(GirisDenemesi.pencere_basi <= sinir)
        .limit(100)
        .with_for_update(skip_locked=True)
        .all()
    )
    if eskiler:
        db.query(GirisDenemesi).filter(GirisDenemesi.anahtar.in_([e[0] for e in eskiler])).delete(synchronize_session=False)
    db.commit()


def deneme_baslat(db: Session, e_posta: str, ip: str) -> int:
    """Denemeyi sayar ve devam edilebiliyorsa 0 dondurur. Sinir doluysa kac saniye kaldigini dondurur (sayaca eklemez)."""
    for i in range(_TEKRAR):
        try:
            kalan = _dene(db, e_posta, ip)
            break
        except IntegrityError:
            # Ayni anda gelen baska bir istek kaydi once acti: var olan kayit uzerinden tekrar say
            db.rollback()
            if i == _TEKRAR - 1:
                raise
    _eskileri_sil(db)
    return kalan


def basarili_giris(db: Session, e_posta: str, ip: str) -> None:
    """Hesap sayacini sifirlar, IP sayacindan bu denemeyi geri alir.

    Onceki basarisiz denemeler IP sayacinda kalir: yoksa saldirgan kendi hesabina
    girerek sayaci sifirlayabilirdi.
    """
    hesap = _kilitli_getir(db, _hesap_anahtari(e_posta, ip))
    if hesap:
        db.delete(hesap)
    ip_kaydi = _kilitli_getir(db, _ip_anahtari(ip))
    if ip_kaydi and ip_kaydi.sayi > 0:
        ip_kaydi.sayi -= 1
    db.commit()
