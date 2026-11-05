import os
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import SessionLocal, engine
import models
from migrate import kolonlari_tamamla
from models import Adres, Kullanici, KullaniciRol, Urun, Kategori, Siparis, SiparisKalemi, SiparisDurum
from schemas import (
    AdresOlustur, AdresCevap,
    KullaniciOlustur, KullaniciCevap, Token,
    KategoriOlustur, KategoriCevap,
    UrunOlustur, UrunCevap, AktifGuncelle,
    SiparisOlustur, SiparisCevap, SiparisDurumGuncelle,
)
from auth import sifreyi_hashle, giris_sifresini_dogrula, token_olustur, tokeni_coz
import giris_siniri

models.Base.metadata.create_all(bind=engine)
kolonlari_tamamla(engine)

app = FastAPI(title="Butik App API", version="3.0.0")

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
    e_posta = tokeni_coz(token)
    if not e_posta:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz token", headers={"WWW-Authenticate": "Bearer"})
    kullanici = db.query(Kullanici).filter(Kullanici.e_posta == e_posta).first()
    if not kullanici or not kullanici.aktif:
        # Silinmis/pasif kullanicinin eski token'i: oturum gecersiz sayilir (uygulama otomatik cikis yapar)
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
    return {"odeme_bilgisi": os.getenv("ODEME_BILGISI", "")}


# ----------------------------------------------------------------- Auth

@app.post("/kayit", response_model=KullaniciCevap, tags=["Auth"])
def kullanici_kayit(veri: KullaniciOlustur, db: Session = Depends(get_db)):
    e_posta = veri.e_posta.strip().lower()
    mevcut = db.query(Kullanici).filter(func.lower(Kullanici.e_posta) == e_posta).first()
    if mevcut:
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayitli")
    yeni = Kullanici(ad=veri.ad.strip(), e_posta=e_posta, sifre_hash=sifreyi_hashle(veri.sifre))
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return yeni


@app.post("/giris", response_model=Token, tags=["Auth"])
def kullanici_giris(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    e_posta = form.username.strip().lower()
    ip = request.client.host if request.client else "bilinmiyor"

    kalan = giris_siniri.kilit_suresi(db, e_posta, ip)
    if kalan:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Cok fazla basarisiz deneme. Lutfen daha sonra tekrar deneyin.",
            headers={"Retry-After": str(kalan)},
        )

    kullanici = db.query(Kullanici).filter(func.lower(Kullanici.e_posta) == e_posta).first()
    sifre_dogru = giris_sifresini_dogrula(form.password, kullanici.sifre_hash if kullanici else None)
    if not sifre_dogru or not kullanici.aktif:
        giris_siniri.basarisiz_giris(db, e_posta, ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya sifre yanlis")

    giris_siniri.basarili_giris(db, e_posta, ip)
    token = token_olustur({"sub": kullanici.e_posta})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/ben", response_model=KullaniciCevap, tags=["Auth"])
def benim_bilgilerim(kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    return kullanici


# ----------------------------------------------------------------- Adresler
# Siparis adresin metnini kopyalar, bu yuzden adres silinse de eski siparisler etkilenmez.

ADRES_SINIRI = 20


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
    adres = _kendi_adresi(db, adres_id, kullanici)
    db.query(Adres).filter(Adres.kullanici_id == kullanici.id, Adres.id != adres.id).update({Adres.varsayilan: False})
    adres.varsayilan = True
    db.commit()
    db.refresh(adres)
    return adres


@app.delete("/adresler/{adres_id}", tags=["Adresler"])
def adres_sil(adres_id: int, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
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
