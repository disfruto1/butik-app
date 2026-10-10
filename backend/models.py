from sqlalchemy import Column, Integer, String, Float, Boolean
from database import Base

class Urun(Base):
    __tablename__ = "urunler"

    id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    aciklama = Column(String)
    fiyat = Column(Float, nullable=False)
    stok = Column(Integer, default=0)
    aktif = Column(Boolean, default=True)
