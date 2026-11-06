import asyncio
import ipaddress
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import SessionLocal, engine
import models
from migrate import kolonlari_tamamla
from models import Adres, Kullanici, KullaniciRol, PaytrDurum, PaytrOdeme, Urun, Kategori, Siparis, SiparisKalemi, SiparisDurum
from schemas import (
    OdemeBaslat, OdemeBaslatCevap, OdemeDurumCevap, OdemeSorunuCevap,
    AdresOlustur, AdresCevap,
    SifirlamaIstek, SifirlamaTamamla,
    KullaniciOlustur, KullaniciCevap, Token,
    KategoriOlustur, KategoriCevap,
    UrunOlustur, UrunCevap, AktifGuncelle,
    SiparisOlustur, SiparisCevap, SiparisDurumGuncelle,
)
from auth import sifreyi_hashle, giris_sifresini_dogrula, token_olustur, tokeni_coz
import eposta
import giris_siniri
import paytr
import sifre_sifirlama
import yasal_metinler

models.Base.metadata.create_all(bind=engine)
kolonlari_tamamla(engine)

log = logging.getLogger("butik.odeme")

TEMIZLIK_ARALIGI_SANIYE = 5 * 60
# PayTR odeme sayfasinin suresi + gec gelen bildirimler icin pay
ODEME_ZAMAN_ASIMI_SANIYE = (paytr.ODEME_SURESI_DAKIKA + 15) * 60


async def _odeme_temizleyici():
    while True:
        await asyncio.sleep(TEMIZLIK_ARALIGI_SANIYE)
        try:
            await asyncio.to_thread(_odeme_temizligi_calistir)
        except Exception:
            log.exception("Suresi dolan odemeler temizlenemedi")


@asynccontextmanager
async def _yasam_dongusu(_: FastAPI):
    ayar = paytr.ayarlar()
    if ayar and ayar.test_modu:
        log.warning("PayTR TEST MODUNDA: odemeler gercek para almaz ama siparisler 'odendi' olur")
    gorev = asyncio.create_task(_odeme_temizleyici())
    yield
    gorev.cancel()


app = FastAPI(title="Butik App API", version="3.0.0", lifespan=_yasam_dongusu)

# Izinli adresler .env'de virgulle ayrilarak verilir. Bos ise yerel gelistirme adresleri kullanilir.
# Mobil uygulama (React Native) tarayici kullanmadigi icin CORS'tan etkilenmez; sadece web icin gerekir.
_izinli = [a.strip() for a in os.getenv("ALLOWED_ORIGINS", "").split(",") if a.strip()]
if not _izinli:
    _izinli = ["http://localhost:8081", "http://127.0.0.1:8081", "http://localhost:19006"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_izinli,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="giris")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def aktif_kullanici_getir(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Kullanici:
    e_posta, token_surumu = tokeni_coz(token)
    if not e_posta:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token", headers={"WWW-Authenticate": "Bearer"})
    kullanici = db.query(Kullanici).filter(Kullanici.e_posta == e_posta).first()
    if not kullanici or not kullanici.aktif or kullanici.token_surumu != token_surumu:
        # Silinmis/pasif kullanicinin veya sifre degismeden onceki token: oturum gecersiz sayilir (uygulama otomatik cikis yapar)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanici bulunamadi", headers={"WWW-Authenticate": "Bearer"})
    return kullanici


def yonetici_gerektir(kullanici: Kullanici = Depends(aktif_kullanici_getir)) -> Kullanici:
    if kullanici.rol != KullaniciRol.YONETICI:
        raise HTTPException(status_code=403, detail="Yonetici yetkisi gerekli")
    return kullanici


# ----------------------------------------------------------------- Genel

@app.get("/", tags=["Genel"])
def ana_sayfa():
    return {"mesaj": "Butik App API calisiyor", "versiyon": "3.0.0"}


@app.get("/ayarlar", tags=["Genel"])
def ayarlar():
    """Uygulamanin gosterecegi genel bilgiler (ornegin havale/EFT odeme bilgisi)."""
    return {"odeme_bilgisi": os.getenv("ODEME_BILGISI", ""), "kart_odeme": paytr.ayarlar() is not None}


@app.get("/yasal/kayit", tags=["Genel"])
def yasal_kayit_metinleri():
    """Uyelik ekraninda gosterilen metinler ve kayit sirasinda geri gonderilecek surum."""
    return {
        "aydinlatma": yasal_metinler.AYDINLATMA,
        "eposta_izni": yasal_metinler.EPOSTA_IZNI,
        "sms_izni": yasal_metinler.SMS_IZNI,
        "izin_notu": yasal_metinler.IZIN_NOTU,
        "surum": yasal_metinler.SURUM,
    }


# ----------------------------------------------------------------- Auth

@app.post("/kayit", response_model=KullaniciCevap, tags=["Auth"])
def kullanici_kayit(veri: KullaniciOlustur, request: Request, db: Session = Depends(get_db)):
    if not veri.aydinlatma_okundu:
        raise HTTPException(status_code=400, detail="Uyelik icin KVKK Aydinlatma Metni okunmalidir")
    if veri.metin_surumu != yasal_metinler.SURUM:
        # Musteri eski metni gormus olabilir; yeni metin gosterilmeden onay kaydedilmez
        raise HTTPException(status_code=409, detail="Metinler guncellendi, lutfen yeniden okuyun")
    telefon = veri.telefon.strip() if veri.telefon else None
    if veri.sms_izni and not telefon:
        raise HTTPException(status_code=400, detail="SMS izni icin telefon numarasi gerekli")
    e_posta = veri.e_posta.strip().lower()
    mevcut = db.query(Kullanici).filter(func.lower(Kullanici.e_posta) == e_posta).first()
    if mevcut:
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayitli")
    yeni = Kullanici(ad=veri.ad.strip(), e_posta=e_posta, sifre_hash=sifreyi_hashle(veri.sifre), telefon=telefon)
    db.add(yeni)
    db.flush()  # onaylar hesapla ayni islemde yazilir: onaysiz hesap olusamaz
    db.add_all(
        yasal_metinler.kayit_onaylarini_olustur(
            yeni.id, e_posta, telefon, veri.eposta_izni, veri.sms_izni, request.client.host if request.client else "bilinmiyor"
        )
    )
    db.commit()
    db.refresh(yeni)
    return yeni


@app.post("/giris", response_model=Token, tags=["Auth"])
def kullanici_giris(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    e_posta = form.username.strip().lower()
    ip = request.client.host if request.client else "bilinmiyor"

    kalan = giris_siniri.deneme_baslat(db, e_posta, ip)
    if kalan:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Cok fazla basarisiz deneme. Lutfen daha sonra tekrar deneyin.",
            headers={"Retry-After": str(kalan)},
        )

    kullanici = db.query(Kullanici).filter(func.lower(Kullanici.e_posta) == e_posta).first()
    sifre_dogru = giris_sifresini_dogrula(form.password, kullanici.sifre_hash if kullanici else None)
    if not sifre_dogru or not kullanici.aktif:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya sifre yanlis")

    giris_siniri.basarili_giris(db, e_posta, ip)
    token = token_olustur({"sub": kullanici.e_posta, "tv": kullanici.token_surumu})
    return {"access_token": token, "token_type": "bearer"}


def _cok_fazla_istek(kalan: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Cok fazla deneme. Lutfen daha sonra tekrar deneyin.",
        headers={"Retry-After": str(kalan)},
    )


def _sifirlama_kodu_gonder(alici: str, kod: str):
    eposta.gonder(
        alici,
        "Butik App şifre sıfırlama kodunuz",
        f"Şifre sıfırlama kodunuz: {kod}\n\n"
        "Kod 15 dakika geçerlidir. Bu isteği siz yapmadıysanız bu e-postayı yok sayabilirsiniz; şifreniz değişmez.",
    )


@app.post("/sifre-sifirlama/iste", tags=["Auth"])
def sifirlama_iste(veri: SifirlamaIstek, request: Request, arka_plan: BackgroundTasks, db: Session = Depends(get_db)):
    """Yanit her zaman aynidir: hangi e-postalarin kayitli oldugu anlasilmasin. E-posta arka planda
    gonderilir, boylece yanit suresi de hesabin var olup olmadigini ele vermez."""
    e_posta = veri.e_posta.strip().lower()
    ip = request.client.host if request.client else "bilinmiyor"
    kalan = giris_siniri.sifirlama_istegi_say(db, e_posta, ip)
    if kalan:
        raise _cok_fazla_istek(kalan)
    kullanici = db.query(Kullanici).filter(func.lower(Kullanici.e_posta) == e_posta).first()
    if kullanici and kullanici.aktif:
        kod = sifre_sifirlama.kod_olustur(db, kullanici.id)
        arka_plan.add_task(_sifirlama_kodu_gonder, kullanici.e_posta, kod)
    return {"mesaj": "Bu e-posta kayitliysa sifirlama kodu gonderildi."}


@app.post("/sifre-sifirlama/tamamla", tags=["Auth"])
def sifirlama_tamamla(veri: SifirlamaTamamla, request: Request, db: Session = Depends(get_db)):
    e_posta = veri.e_posta.strip().lower()
    ip = request.client.host if request.client else "bilinmiyor"
    kalan = giris_siniri.sifirlama_denemesi_say(db, ip)
    if kalan:
        raise _cok_fazla_istek(kalan)
    kullanici = db.query(Kullanici).filter(func.lower(Kullanici.e_posta) == e_posta).first()
    if not kullanici or not kullanici.aktif or not sifre_sifirlama.kodu_dogrula_ve_harca(db, kullanici.id, veri.kod):
        raise HTTPException(status_code=400, detail="Kod gecersiz veya suresi dolmus")
    kullanici.sifre_hash = sifreyi_hashle(veri.yeni_sifre)
    kullanici.token_surumu += 1  # eski oturumlar kapanir (telefonu calinan biri icin onemli)
    giris_siniri.hesap_sayacini_sifirla(db, e_posta, ip)
    db.commit()
    return {"mesaj": "Sifreniz degistirildi."}


@app.get("/ben", response_model=KullaniciCevap, tags=["Auth"])
def benim_bilgilerim(kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    return kullanici


# ----------------------------------------------------------------- Adresler
# Siparis adresin metnini kopyalar, bu yuzden adres silinse de eski siparisler etkilenmez.

ADRES_SINIRI = 20


def _adresleri_kilitle(db: Session, kullanici: Kullanici) -> None:
    """Ayni kullanicinin adres degisikliklerini sira ile yaptirir: ayni anda gelen istekler
    birden fazla varsayilan adres olusturamaz, adres sinirini asamaz."""
    db.query(Kullanici.id).filter(Kullanici.id == kullanici.id).with_for_update().first()


def _kendi_adresi(db: Session, adres_id: int, kullanici: Kullanici) -> Adres:
    # Baskasinin adresini "yok" gibi goster (varligini sizdirma)
    adres = db.query(Adres).filter(Adres.id == adres_id, Adres.kullanici_id == kullanici.id).first()
    if not adres:
        raise HTTPException(status_code=404, detail="Adres bulunamadi")
    return adres


@app.get("/adresler", response_model=list[AdresCevap], tags=["Adresler"])
def adresleri_listele(db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    """Varsayilan adres en ustte."""
    return (
        db.query(Adres)
        .filter(Adres.kullanici_id == kullanici.id)
        .order_by(Adres.varsayilan.desc(), Adres.id.desc())
        .all()
    )


@app.post("/adresler", response_model=AdresCevap, tags=["Adresler"])
def adres_ekle(veri: AdresOlustur, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    _adresleri_kilitle(db, kullanici)
    adet = db.query(Adres).filter(Adres.kullanici_id == kullanici.id).count()
    if adet >= ADRES_SINIRI:
        raise HTTPException(status_code=400, detail=f"En fazla {ADRES_SINIRI} adres kaydedebilirsiniz")
    # Ilk adres otomatik varsayilan olur
    yeni = Adres(kullanici_id=kullanici.id, baslik=veri.baslik.strip(), adres=veri.adres.strip(), varsayilan=adet == 0)
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return yeni


@app.put("/adresler/{adres_id}", response_model=AdresCevap, tags=["Adresler"])
def adres_guncelle(adres_id: int, veri: AdresOlustur, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    adres = _kendi_adresi(db, adres_id, kullanici)
    adres.baslik = veri.baslik.strip()
    adres.adres = veri.adres.strip()
    db.commit()
    db.refresh(adres)
    return adres


@app.post("/adresler/{adres_id}/varsayilan", response_model=AdresCevap, tags=["Adresler"])
def adresi_varsayilan_yap(adres_id: int, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    _adresleri_kilitle(db, kullanici)
    adres = _kendi_adresi(db, adres_id, kullanici)
    db.query(Adres).filter(Adres.kullanici_id == kullanici.id, Adres.id != adres.id).update({Adres.varsayilan: False})
    adres.varsayilan = True
    db.commit()
    db.refresh(adres)
    return adres


@app.delete("/adresler/{adres_id}", tags=["Adresler"])
def adres_sil(adres_id: int, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    _adresleri_kilitle(db, kullanici)
    adres = _kendi_adresi(db, adres_id, kullanici)
    varsayilandi = adres.varsayilan
    db.delete(adres)
    db.flush()
    if varsayilandi:
        # Adres kaldiysa kullanici varsayilansiz kalmasin
        siradaki = db.query(Adres).filter(Adres.kullanici_id == kullanici.id).order_by(Adres.id.desc()).first()
        if siradaki:
            siradaki.varsayilan = True
    db.commit()
    return {"mesaj": "Adres silindi"}


# ----------------------------------------------------------------- Kategoriler

@app.get("/kategoriler", response_model=list[KategoriCevap], tags=["Kategoriler"])
def kategorileri_listele(db: Session = Depends(get_db)):
    return db.query(Kategori).filter(Kategori.aktif == True).order_by(Kategori.ad).all()  # noqa: E712


@app.post("/kategoriler", response_model=KategoriCevap, tags=["Kategoriler"])
def kategori_ekle(veri: KategoriOlustur, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    mevcut = db.query(Kategori).filter(Kategori.ad == veri.ad.strip()).first()
    if mevcut:
        raise HTTPException(status_code=400, detail="Bu kategori zaten mevcut")
    yeni = Kategori(ad=veri.ad.strip(), aciklama=veri.aciklama)
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return yeni


@app.put("/kategoriler/{kategori_id}", response_model=KategoriCevap, tags=["Kategoriler"])
def kategori_guncelle(kategori_id: int, veri: KategoriOlustur, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    kategori = db.query(Kategori).filter(Kategori.id == kategori_id).first()
    if not kategori:
        raise HTTPException(status_code=404, detail="Kategori bulunamadi")
    cakisan = db.query(Kategori).filter(Kategori.ad == veri.ad.strip(), Kategori.id != kategori_id).first()
    if cakisan:
        raise HTTPException(status_code=400, detail="Bu isimde baska bir kategori var")
    kategori.ad = veri.ad.strip()
    kategori.aciklama = veri.aciklama
    db.commit()
    db.refresh(kategori)
    return kategori


@app.delete("/kategoriler/{kategori_id}", tags=["Kategoriler"])
def kategori_sil(kategori_id: int, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    kategori = db.query(Kategori).filter(Kategori.id == kategori_id).first()
    if not kategori:
        raise HTTPException(status_code=404, detail="Kategori bulunamadi")
    kategori.aktif = False  # urunler silinmez, sadece kategori gizlenir
    db.commit()
    return {"mesaj": "Kategori pasife alindi"}


# ----------------------------------------------------------------- Urunler

def _urun_sorgusu_filtrele(sorgu, q: Optional[str], kategori_id: Optional[int]):
    if q and q.strip():
        desen = f"%{q.strip()}%"
        sorgu = sorgu.filter(or_(Urun.ad.ilike(desen), Urun.aciklama.ilike(desen)))
    if kategori_id:
        sorgu = sorgu.filter(Urun.kategori_id == kategori_id)
    return sorgu


def _kategori_kontrol(db: Session, kategori_id: Optional[int]):
    if kategori_id is not None and not db.query(Kategori).filter(Kategori.id == kategori_id).first():
        raise HTTPException(status_code=400, detail="Kategori bulunamadi")


@app.get("/urunler", response_model=list[UrunCevap], tags=["Urunler"])
def urunleri_listele(
    q: Optional[str] = Query(None, max_length=100),
    kategori_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    sorgu = db.query(Urun).filter(Urun.aktif == True)  # noqa: E712
    sorgu = _urun_sorgusu_filtrele(sorgu, q, kategori_id)
    return sorgu.order_by(Urun.id.desc()).offset(offset).limit(limit).all()


@app.get("/urunler/{urun_id}", response_model=UrunCevap, tags=["Urunler"])
def urun_getir(urun_id: int, db: Session = Depends(get_db)):
    urun = db.query(Urun).filter(Urun.id == urun_id, Urun.aktif == True).first()  # noqa: E712
    if not urun:
        raise HTTPException(status_code=404, detail="Urun bulunamadi")
    return urun


@app.post("/urunler", response_model=UrunCevap, tags=["Urunler"])
def urun_ekle(veri: UrunOlustur, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    _kategori_kontrol(db, veri.kategori_id)
    yeni = Urun(
        ad=veri.ad.strip(), aciklama=veri.aciklama, fiyat=veri.fiyat, stok=veri.stok,
        gorsel_url=(veri.gorsel_url or None), kategori_id=veri.kategori_id,
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return yeni


@app.put("/urunler/{urun_id}", response_model=UrunCevap, tags=["Urunler"])
def urun_guncelle(urun_id: int, veri: UrunOlustur, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    urun = db.query(Urun).filter(Urun.id == urun_id).first()
    if not urun:
        raise HTTPException(status_code=404, detail="Urun bulunamadi")
    _kategori_kontrol(db, veri.kategori_id)
    urun.ad = veri.ad.strip()
    urun.aciklama = veri.aciklama
    urun.fiyat = veri.fiyat
    urun.stok = veri.stok
    urun.gorsel_url = veri.gorsel_url or None
    urun.kategori_id = veri.kategori_id
    db.commit()
    db.refresh(urun)
    return urun


@app.patch("/urunler/{urun_id}/aktif", response_model=UrunCevap, tags=["Urunler"])
def urun_aktiflik_degistir(urun_id: int, veri: AktifGuncelle, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    urun = db.query(Urun).filter(Urun.id == urun_id).first()
    if not urun:
        raise HTTPException(status_code=404, detail="Urun bulunamadi")
    urun.aktif = veri.aktif
    db.commit()
    db.refresh(urun)
    return urun


@app.delete("/urunler/{urun_id}", tags=["Urunler"])
def urun_sil(urun_id: int, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    urun = db.query(Urun).filter(Urun.id == urun_id).first()
    if not urun:
        raise HTTPException(status_code=404, detail="Urun bulunamadi")
    urun.aktif = False
    db.commit()
    return {"mesaj": "Urun pasife alindi"}


@app.get("/yonetim/urunler", response_model=list[UrunCevap], tags=["Yonetim"])
def yonetim_urunleri_listele(
    q: Optional[str] = Query(None, max_length=100),
    kategori_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: Kullanici = Depends(yonetici_gerektir),
):
    """Pasife alinmis urunler dahil tum urunler."""
    sorgu = _urun_sorgusu_filtrele(db.query(Urun), q, kategori_id)
    return sorgu.order_by(Urun.id.desc()).offset(offset).limit(limit).all()


# ----------------------------------------------------------------- Siparisler

def _stok_iade_et(db: Session, siparis: Siparis):
    """Iptal edilen siparisin stoklarini geri ekler."""
    for kalem in siparis.kalemler:
        if kalem.urun_id is None:
            continue
        urun = db.query(Urun).filter(Urun.id == kalem.urun_id).with_for_update().first()
        if urun is not None and urun.stok is not None:
            urun.stok += kalem.adet


@app.post("/siparisler", response_model=SiparisCevap, tags=["Siparisler"])
def siparis_olustur(veri: SiparisOlustur, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    toplam = Decimal("0")
    kalemler = []
    for k in veri.kalemler:
        # Satir kilidi: ayni urune ayni anda gelen siparisler stogu fazla dusuremesin
        urun = db.query(Urun).filter(Urun.id == k.urun_id, Urun.aktif == True).with_for_update().first()  # noqa: E712
        if not urun:
            raise HTTPException(status_code=404, detail=f"Urun bulunamadi: {k.urun_id}")
        if urun.stok is not None and urun.stok < k.adet:
            raise HTTPException(status_code=400, detail=f"Yetersiz stok: {urun.ad}")
        toplam += urun.fiyat * k.adet
        kalemler.append(SiparisKalemi(urun_id=urun.id, urun_adi=urun.ad, birim_fiyat=urun.fiyat, adet=k.adet))
        if urun.stok is not None:
            urun.stok -= k.adet
    siparis = Siparis(kullanici_id=kullanici.id, toplam_tutar=toplam, kargo_adres=veri.kargo_adres.strip(), kalemler=kalemler)
    db.add(siparis)
    db.commit()
    db.refresh(siparis)
    return siparis


@app.get("/siparisler", response_model=list[SiparisCevap], tags=["Siparisler"])
def siparisleri_listele(
    durum: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(aktif_kullanici_getir),
):
    sorgu = db.query(Siparis)
    if kullanici.rol != KullaniciRol.YONETICI:
        sorgu = sorgu.filter(Siparis.kullanici_id == kullanici.id)
    if durum:
        sorgu = sorgu.filter(Siparis.durum == durum)
    return sorgu.order_by(Siparis.id.desc()).offset(offset).limit(limit).all()


@app.get("/siparisler/{siparis_id}", response_model=SiparisCevap, tags=["Siparisler"])
def siparis_getir(siparis_id: int, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    siparis = db.query(Siparis).filter(Siparis.id == siparis_id).first()
    # Baskasinin siparisini "yok" gibi goster (varligini sizdirma)
    if not siparis or (kullanici.rol != KullaniciRol.YONETICI and siparis.kullanici_id != kullanici.id):
        raise HTTPException(status_code=404, detail="Siparis bulunamadi")
    return siparis


@app.post("/siparisler/{siparis_id}/iptal", response_model=SiparisCevap, tags=["Siparisler"])
def siparis_iptal_et(siparis_id: int, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    """Musteri, odemesi yapilmamis kendi siparisini iptal eder."""
    siparis = db.query(Siparis).filter(Siparis.id == siparis_id).with_for_update().first()
    if not siparis or siparis.kullanici_id != kullanici.id:
        raise HTTPException(status_code=404, detail="Siparis bulunamadi")
    if siparis.durum != SiparisDurum.ODEME_BEKLIYOR:
        raise HTTPException(status_code=400, detail="Sadece odeme bekleyen siparisler iptal edilebilir")
    siparis.durum = SiparisDurum.IPTAL_EDILDI
    _stok_iade_et(db, siparis)
    db.commit()
    db.refresh(siparis)
    return siparis


@app.patch("/siparisler/{siparis_id}/durum", response_model=SiparisCevap, tags=["Siparisler"])
def siparis_durum_guncelle(siparis_id: int, veri: SiparisDurumGuncelle, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    siparis = db.query(Siparis).filter(Siparis.id == siparis_id).with_for_update().first()
    if not siparis:
        raise HTTPException(status_code=404, detail="Siparis bulunamadi")
    izinli = SiparisDurum.GECISLER.get(siparis.durum, [])
    if veri.durum not in izinli:
        raise HTTPException(status_code=400, detail=f"'{siparis.durum}' durumundan '{veri.durum}' durumuna gecilemez")
    if veri.durum == SiparisDurum.IPTAL_EDILDI:
        _stok_iade_et(db, siparis)
    if veri.takip_no is not None and veri.takip_no.strip():
        siparis.takip_no = veri.takip_no.strip()
    siparis.durum = veri.durum
    db.commit()
    db.refresh(siparis)
    return siparis


# ----------------------------------------------------------------- Kart odemesi (PayTR)

def _odeme_ip(request: Request, ayar: paytr.Ayarlar) -> str:
    """PayTR musterinin dis IP'sini ister. Yerel denemede istemci IP'si dahili oldugu icin ayardan alinir."""
    ip = request.client.host if request.client else ""
    try:
        if ipaddress.ip_address(ip).is_private and ayar.yerel_ip:
            return ayar.yerel_ip
    except ValueError:
        pass
    return ip


@app.post("/siparisler/{siparis_id}/odeme/paytr", response_model=OdemeBaslatCevap, tags=["Odeme"])
def paytr_odeme_baslat(
    siparis_id: int,
    veri: OdemeBaslat,
    request: Request,
    db: Session = Depends(get_db),
    kullanici: Kullanici = Depends(aktif_kullanici_getir),
):
    ayar = paytr.ayarlar()
    if ayar is None:
        raise HTTPException(status_code=503, detail="Kart ile odeme su an kullanilamiyor")
    kalan = giris_siniri.odeme_baslatma_say(db, kullanici.id)
    if kalan:
        raise _cok_fazla_istek(kalan)

    # Durum kontrolu ve deneme kaydi kilit altinda; PayTR istegi kilit birakildiktan sonra.
    # Kilit acik kalsaydi yavas bir PayTR yaniti iptal ve bildirimleri de bekletirdi.
    siparis = db.query(Siparis).filter(Siparis.id == siparis_id).with_for_update().first()
    if not siparis or siparis.kullanici_id != kullanici.id:
        raise HTTPException(status_code=404, detail="Siparis bulunamadi")
    if siparis.durum != SiparisDurum.ODEME_BEKLIYOR:
        raise HTTPException(status_code=400, detail="Bu siparis icin odeme beklenmiyor")
    # Tutar sadece sunucudaki siparisten gelir, istemciden alinmaz
    tutar_kurus = paytr.kurusa_cevir(siparis.toplam_tutar)
    if tutar_kurus <= 0:
        raise HTTPException(status_code=400, detail="Bu siparis icin odeme alinamaz")
    telefon = veri.telefon.strip() if veri.telefon else kullanici.telefon
    if not telefon:
        raise HTTPException(status_code=400, detail="Kart ile odeme icin telefon numarasi gerekli")
    e_posta = kullanici.e_posta
    if not e_posta.isascii() or len(e_posta) > 100:
        raise HTTPException(status_code=400, detail="E-posta adresiniz kart odemesi icin uygun degil")

    merchant_oid = paytr.siparis_no_uret(siparis.id)
    sepet = paytr.sepet_kodla([(k.urun_adi, k.birim_fiyat, k.adet) for k in siparis.kalemler])
    ad, adres = kullanici.ad, siparis.kargo_adres or "Belirtilmedi"
    kullanici.telefon = telefon
    db.add(PaytrOdeme(merchant_oid=merchant_oid, siparis_id=siparis.id, tutar_kurus=tutar_kurus, test_modu=ayar.test_modu, olusturulma=int(time.time())))
    db.commit()

    try:
        token = paytr.token_iste(
            ayar,
            merchant_oid=merchant_oid,
            ip=_odeme_ip(request, ayar),
            e_posta=e_posta,
            tutar_kurus=tutar_kurus,
            sepet=sepet,
            ad=ad,
            adres=adres,
            telefon=telefon,
        )
    except paytr.PaytrHatasi as hata:
        log.error("Odeme baslatilamadi (%s): %s", merchant_oid, hata)
        db.query(PaytrOdeme).filter(PaytrOdeme.merchant_oid == merchant_oid, PaytrOdeme.durum == PaytrDurum.BEKLIYOR).update(
            {PaytrOdeme.durum: PaytrDurum.TOKEN_ALINAMADI}
        )
        db.commit()
        raise HTTPException(status_code=502, detail="Odeme baslatilamadi. Lutfen tekrar deneyin.") from hata
    return OdemeBaslatCevap(merchant_oid=merchant_oid, odeme_url=paytr.ODEME_SAYFASI + token, test_modu=ayar.test_modu)


async def _form_oku(request: Request):
    return await request.form()


def _bildirim_red(sebep: str, kod: int) -> PlainTextResponse:
    # "OK" donmedigimiz surece PayTR bildirimi teslim edilmemis sayar
    return PlainTextResponse(sebep, status_code=kod)


@app.post("/odeme/paytr/bildirim", response_class=PlainTextResponse, tags=["Odeme"])
def paytr_bildirim(form=Depends(_form_oku), db: Session = Depends(get_db)):
    """PayTR'in sunucudan sunucuya odeme sonucu bildirimi. Giris istemez, guven imzadan gelir."""
    ayar = paytr.ayarlar()
    if ayar is None:
        return _bildirim_red("yapilandirilmamis", 503)
    merchant_oid, durum, toplam, imza = (str(form.get(a, "")) for a in ("merchant_oid", "status", "total_amount", "hash"))
    if not (merchant_oid and imza) or not paytr.bildirim_gecerli(ayar, merchant_oid, durum, toplam, imza):
        log.warning("PayTR bildiriminde gecersiz imza")
        return _bildirim_red("gecersiz imza", 400)
    if durum not in ("success", "failed") or not toplam.isdigit():
        return _bildirim_red("gecersiz icerik", 400)

    kayit = db.query(PaytrOdeme.siparis_id).filter(PaytrOdeme.merchant_oid == merchant_oid).first()
    if not kayit:
        # Bizim degil. OK donulmez: baska bir sistemin bildirimiyse kaybolmasin, PayTR panelinde gorunsun
        log.error("Bilinmeyen PayTR bildirimi: %s", merchant_oid)
        return _bildirim_red("bilinmeyen siparis", 404)

    # Kilit sirasi her yerde once siparis: iptal ve ayni anda gelen tekrar bildirimlerle yarismaz
    siparis = db.query(Siparis).filter(Siparis.id == kayit.siparis_id).with_for_update().first()
    odeme = db.query(PaytrOdeme).filter(PaytrOdeme.merchant_oid == merchant_oid).with_for_update().first()
    if odeme.durum in (PaytrDurum.BASARILI, PaytrDurum.BASARISIZ):
        db.rollback()
        return PlainTextResponse("OK")  # tekrar gelen bildirim, ilki islendi

    if durum == "failed":
        odeme.durum = PaytrDurum.BASARISIZ
        odeme.hata_kodu = str(form.get("failed_reason_code", ""))[:20] or None
        odeme.hata_mesaji = str(form.get("failed_reason_msg", ""))[:255] or None
    else:
        odeme.durum = PaytrDurum.BASARILI
        odeme.odenen_kurus = int(toplam)
        odeme.inceleme_nedeni = _odeme_sorunu(odeme, siparis, form)
        if odeme.inceleme_nedeni:
            log.error("PayTR odemesi incelenmeli (%s): %s", merchant_oid, odeme.inceleme_nedeni)
        else:
            siparis.durum = SiparisDurum.ODENDI
    db.commit()
    return PlainTextResponse("OK")


def _odeme_sorunu(odeme: PaytrOdeme, siparis: Siparis, form) -> Optional[str]:
    """Basarili bildirim siparisi "odendi" yapmaya yetmiyorsa nedenini dondurur."""
    if str(form.get("test_mode", "")) == "1" and not odeme.test_modu:
        return "test_bildirimi"
    if odeme.odenen_kurus < odeme.tutar_kurus or str(form.get("currency", paytr.PARA_BIRIMI)) not in (paytr.PARA_BIRIMI, "TRY"):
        return "tutar_uyusmazligi"
    if siparis.durum == SiparisDurum.IPTAL_EDILDI:
        return "iptal_siparise_odeme"  # musteri veya zaman asimi iptal etmis, para iade edilmeli
    if siparis.durum != SiparisDurum.ODEME_BEKLIYOR:
        return "zaten_odenmis_siparis"  # ikinci deneme de odendi veya havale elle onaylandi
    return None


def _odeme_sonuc_sayfasi(baslik: str, metin: str) -> HTMLResponse:
    return HTMLResponse(
        '<!doctype html><html lang="tr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        f'<body style="font-family:sans-serif;text-align:center;padding:48px 16px"><h2>{baslik}</h2><p>{metin}</p></body></html>'
    )


# Bu sayfalar sadece musteriye bilgi verir, odemeyi onaylamaz. Onay yalnizca bildirimden gelir.
@app.get("/odeme/paytr/tamam", response_class=HTMLResponse, include_in_schema=False)
def paytr_tamam_sayfasi():
    return _odeme_sonuc_sayfasi("Ödemeniz alınıyor", "Uygulamaya dönebilirsiniz.")


@app.get("/odeme/paytr/hata", response_class=HTMLResponse, include_in_schema=False)
def paytr_hata_sayfasi():
    return _odeme_sonuc_sayfasi("Ödeme tamamlanamadı", "Uygulamaya dönüp tekrar deneyebilirsiniz.")


@app.get("/odeme/paytr/{merchant_oid}", response_model=OdemeDurumCevap, tags=["Odeme"])
def paytr_odeme_durumu(merchant_oid: str, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    odeme = db.query(PaytrOdeme).filter(PaytrOdeme.merchant_oid == merchant_oid).first()
    siparis = db.query(Siparis).filter(Siparis.id == odeme.siparis_id).first() if odeme else None
    if not siparis or (kullanici.rol != KullaniciRol.YONETICI and siparis.kullanici_id != kullanici.id):
        raise HTTPException(status_code=404, detail="Odeme bulunamadi")
    return OdemeDurumCevap(
        merchant_oid=odeme.merchant_oid,
        durum=odeme.durum,
        siparis_id=siparis.id,
        siparis_durum=siparis.durum,
        hata_mesaji=odeme.hata_mesaji,
    )


@app.get("/yonetim/odeme-sorunlari", response_model=list[OdemeSorunuCevap], tags=["Yonetim"])
def odeme_sorunlari(db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    """Para alinmis ama siparisi "odendi" yapilamamis denemeler. Iade veya elle kontrol gerekir."""
    return (
        db.query(PaytrOdeme)
        .filter(PaytrOdeme.inceleme_nedeni.is_not(None))
        .order_by(PaytrOdeme.olusturulma.desc())
        .limit(200)
        .all()
    )


def _suresi_dolanlar(db: Session, sinir: int):
    """Kart denenmis, son denemesi eskimis ve hic para alinmamis, hala odeme bekleyen siparisler.

    Hic kart denenmemis siparisler secilmez: havale gunler surebilir, otomatik iptal edilmemeli.
    """
    son_deneme = (
        db.query(PaytrOdeme.siparis_id)
        .filter(PaytrOdeme.durum != PaytrDurum.TOKEN_ALINAMADI)
        .group_by(PaytrOdeme.siparis_id)
        .having(func.max(PaytrOdeme.olusturulma) <= sinir)
    )
    para_alinan = db.query(PaytrOdeme.siparis_id).filter(PaytrOdeme.durum == PaytrDurum.BASARILI)
    return db.query(Siparis).filter(
        Siparis.durum == SiparisDurum.ODEME_BEKLIYOR,
        Siparis.id.in_(son_deneme),
        Siparis.id.not_in(para_alinan),
    )


def suresi_dolan_odemeleri_iptal_et(db: Session) -> int:
    """Terk edilen kart odemelerinin siparisini iptal eder, stok geri doner."""
    sinir = int(time.time()) - ODEME_ZAMAN_ASIMI_SANIYE
    adaylar = [s.id for s in _suresi_dolanlar(db, sinir).order_by(Siparis.id).limit(50).all()]
    db.rollback()
    iptal = 0
    for siparis_id in adaylar:
        # Kilit alindiktan sonra kosul tekrar sorgulanir: bu arada odenmis veya yeni deneme baslamis olabilir
        siparis = _suresi_dolanlar(db, sinir).filter(Siparis.id == siparis_id).with_for_update(skip_locked=True).first()
        if siparis is None:
            db.rollback()
            continue
        siparis.durum = SiparisDurum.IPTAL_EDILDI
        _stok_iade_et(db, siparis)
        db.commit()
        iptal += 1
    if iptal:
        log.info("Suresi dolan %d odeme iptal edildi", iptal)
    return iptal


def _odeme_temizligi_calistir():
    db = SessionLocal()
    try:
        suresi_dolan_odemeleri_iptal_et(db)
    finally:
        db.close()


# ----------------------------------------------------------------- Yonetim

@app.get("/yonetim/ozet", tags=["Yonetim"])
def yonetim_ozet(db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    bugun_basi = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    iptal_degil = Siparis.durum != SiparisDurum.IPTAL_EDILDI

    bugun_adet, bugun_tutar = db.query(
        func.count(Siparis.id), func.coalesce(func.sum(Siparis.toplam_tutar), 0)
    ).filter(iptal_degil, Siparis.olusturulma_tarihi >= bugun_basi).one()

    durum_sayilari = {d: s for d, s in db.query(Siparis.durum, func.count(Siparis.id)).group_by(Siparis.durum).all()}

    odenen_ciro = db.query(func.coalesce(func.sum(Siparis.toplam_tutar), 0)).filter(
        Siparis.durum.in_(SiparisDurum.ODENMIS)
    ).scalar()

    dusuk_stok = (
        db.query(Urun)
        .filter(Urun.aktif == True, Urun.stok.isnot(None), Urun.stok <= 5)  # noqa: E712
        .order_by(Urun.stok, Urun.id)
        .limit(20)
        .all()
    )

    return {
        "bugun_siparis_adedi": int(bugun_adet or 0),
        "bugun_tutar": float(bugun_tutar or 0),
        "odenmis_toplam_ciro": float(odenen_ciro or 0),
        "durum_sayilari": durum_sayilari,
        "dusuk_stok": [{"id": u.id, "ad": u.ad, "stok": u.stok} for u in dusuk_stok],
    }
