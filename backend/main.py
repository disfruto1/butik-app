from decimal import Decimal
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from models import Kullanici, KullaniciRol, Urun, Kategori, Siparis, SiparisKalemi
from schemas import (
    KullaniciOlustur, KullaniciCevap, Token,
    KategoriOlustur, KategoriCevap,
    UrunOlustur, UrunCevap,
    SiparisOlustur, SiparisCevap,
)
from auth import sifreyi_hashle, sifreyi_dogrula, token_olustur, tokeni_coz

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Butik App API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi")
    return kullanici

def yonetici_gerektir(kullanici: Kullanici = Depends(aktif_kullanici_getir)) -> Kullanici:
    if kullanici.rol != KullaniciRol.YONETICI:
        raise HTTPException(status_code=403, detail="Yonetici yetkisi gerekli")
    return kullanici

@app.get("/", tags=["Genel"])
def ana_sayfa():
    return {"mesaj": "Butik App API calisiyor", "versiyon": "2.0.0"}

@app.post("/kayit", response_model=KullaniciCevap, tags=["Auth"])
def kullanici_kayit(veri: KullaniciOlustur, db: Session = Depends(get_db)):
    mevcut = db.query(Kullanici).filter(Kullanici.e_posta == veri.e_posta).first()
    if mevcut:
        raise HTTPException(status_code=400, detail="Bu e-posta zaten kayitli")
    yeni = Kullanici(ad=veri.ad, e_posta=veri.e_posta, sifre_hash=sifreyi_hashle(veri.sifre))
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return yeni

@app.post("/giris", response_model=Token, tags=["Auth"])
def kullanici_giris(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    kullanici = db.query(Kullanici).filter(Kullanici.e_posta == form.username).first()
    if not kullanici or not sifreyi_dogrula(form.password, kullanici.sifre_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-posta veya sifre yanlis")
    token = token_olustur({"sub": kullanici.e_posta})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/ben", response_model=KullaniciCevap, tags=["Auth"])
def benim_bilgilerim(kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    return kullanici

@app.get("/kategoriler", response_model=list[KategoriCevap], tags=["Kategoriler"])
def kategorileri_listele(db: Session = Depends(get_db)):
    return db.query(Kategori).filter(Kategori.aktif == True).all()

@app.post("/kategoriler", response_model=KategoriCevap, tags=["Kategoriler"])
def kategori_ekle(veri: KategoriOlustur, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    mevcut = db.query(Kategori).filter(Kategori.ad == veri.ad).first()
    if mevcut:
        raise HTTPException(status_code=400, detail="Bu kategori zaten mevcut")
    yeni = Kategori(ad=veri.ad, aciklama=veri.aciklama)
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return yeni

@app.get("/urunler", response_model=list[UrunCevap], tags=["Urunler"])
def urunleri_listele(db: Session = Depends(get_db)):
    return db.query(Urun).filter(Urun.aktif == True).all()

@app.get("/urunler/{urun_id}", response_model=UrunCevap, tags=["Urunler"])
def urun_getir(urun_id: int, db: Session = Depends(get_db)):
    urun = db.query(Urun).filter(Urun.id == urun_id).first()
    if not urun:
        raise HTTPException(status_code=404, detail="Urun bulunamadi")
    return urun

@app.post("/urunler", response_model=UrunCevap, tags=["Urunler"])
def urun_ekle(veri: UrunOlustur, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    yeni = Urun(ad=veri.ad, aciklama=veri.aciklama, fiyat=veri.fiyat, stok=veri.stok, kategori_id=veri.kategori_id)
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    return yeni

@app.put("/urunler/{urun_id}", response_model=UrunCevap, tags=["Urunler"])
def urun_guncelle(urun_id: int, veri: UrunOlustur, db: Session = Depends(get_db), _: Kullanici = Depends(yonetici_gerektir)):
    urun = db.query(Urun).filter(Urun.id == urun_id).first()
    if not urun:
        raise HTTPException(status_code=404, detail="Urun bulunamadi")
    urun.ad = veri.ad
    urun.aciklama = veri.aciklama
    urun.fiyat = veri.fiyat
    urun.stok = veri.stok
    urun.kategori_id = veri.kategori_id
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

@app.post("/siparisler", response_model=SiparisCevap, tags=["Siparisler"])
def siparis_olustur(veri: SiparisOlustur, db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    toplam = Decimal("0")
    kalemler = []
    for k in veri.kalemler:
        urun = db.query(Urun).filter(Urun.id == k.urun_id, Urun.aktif == True).first()
        if not urun:
            raise HTTPException(status_code=404, detail=f"Urun bulunamadi: {k.urun_id}")
        if urun.stok is not None and urun.stok < k.adet:
            raise HTTPException(status_code=400, detail=f"Yetersiz stok: {urun.ad}")
        toplam += urun.fiyat * k.adet
        kalemler.append(SiparisKalemi(urun_id=urun.id, urun_adi=urun.ad, birim_fiyat=urun.fiyat, adet=k.adet))
        if urun.stok is not None:
            urun.stok -= k.adet
    siparis = Siparis(kullanici_id=kullanici.id, toplam_tutar=toplam, kargo_adres=veri.kargo_adres, kalemler=kalemler)
    db.add(siparis)
    db.commit()
    db.refresh(siparis)
    return siparis

@app.get("/siparisler", response_model=list[SiparisCevap], tags=["Siparisler"])
def siparisleri_listele(db: Session = Depends(get_db), kullanici: Kullanici = Depends(aktif_kullanici_getir)):
    if kullanici.rol == KullaniciRol.YONETICI:
        return db.query(Siparis).all()
    return db.query(Siparis).filter(Siparis.kullanici_id == kullanici.id).all()
