from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import engine, get_db
import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Butik App API",
    version="0.1.0"
)

@app.get("/")
def anasayfa():
    return {"mesaj": "Merhaba Butik!"}

@app.get("/health")
def saglik_kontrolu():
    return {"durum": "saglikli", "versiyon": "0.1.0"}

@app.get("/urunler")
def urunleri_listele(db: Session = Depends(get_db)):
    urunler = db.query(models.Urun).all()
    return urunler

@app.post("/urunler")
def urun_ekle(ad: str, fiyat: float, stok: int = 0, db: Session = Depends(get_db)):
    yeni_urun = models.Urun(ad=ad, fiyat=fiyat, stok=stok)
    db.add(yeni_urun)
    db.commit()
    db.refresh(yeni_urun)
    return yeni_urun
