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
SIFIRLAMA_EPOSTA_SINIRI = 3
SIFIRLAMA_IP_SINIRI = 10
SIFIRLAMA_DENEME_IP_SINIRI = 30
ODEME_BASLATMA_SINIRI = 10
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


def _dene(db: Session, sayaclar: list[tuple[str, int]]) -> int:
    simdi = _simdi()
    # Kilit sirasi her istekte ayni (ilki hesap, sonra IP): kilitlenme (deadlock) olmaz
    kayitlar =[(anahtar, sinir, _kilitli_getir(db, anahtar)) for anahtar, sinir in sayaclar]

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
    return _say(db, [(_hesap_anahtari(e_posta, ip), HESAP_SINIRI), (_ip_anahtari(ip), IP_SINIRI)])


def sifirlama_istegi_say(db: Session, e_posta: str, ip: str) -> int:
    """Kod isteklerini sayar. E-posta sayaci IP'den bagimsizdir: farkli IP'lerden de posta kutusu doldurulamaz."""
    return _say(db, [
        (_anahtar("sifirlama-eposta", e_posta), SIFIRLAMA_EPOSTA_SINIRI),
        (_anahtar("sifirlama-ip", ip), SIFIRLAMA_IP_SINIRI),
    ])


def sifirlama_denemesi_say(db: Session, ip: str) -> int:
    """Kod girme denemelerini IP'ye gore sayar: ayni IP'den cok sayida hesaba kod denenemesin."""
    return _say(db, [(_anahtar("sifirlama-deneme-ip", ip), SIFIRLAMA_DENEME_IP_SINIRI)])


def odeme_baslatma_say(db: Session, kullanici_id: int) -> int:
    """Odeme baslatmalarini kullaniciya gore sayar: her biri PayTR'a istek atar."""
    return _say(db, [(_anahtar("odeme-baslatma", str(kullanici_id)), ODEME_BASLATMA_SINIRI)])


def hesap_sayacini_sifirla(db: Session, e_posta: str, ip: str) -> None:
    """Sifre sifirlaninca kullanici eski sifre denemeleri yuzunden kilitli kalmasin. Commit etmez."""
    db.query(GirisDenemesi).filter(GirisDenemesi.anahtar == _hesap_anahtari(e_posta, ip)).delete(synchronize_session=False)


def _say(db: Session, sayaclar: list[tuple[str, int]]) -> int:
    for i in range(_TEKRAR):
        try:
            kalan = _dene(db, sayaclar)
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
