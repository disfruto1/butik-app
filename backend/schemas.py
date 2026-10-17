from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class KullaniciOlustur(BaseModel):
    ad: str
    e_posta: EmailStr
    sifre: str

class Token(BaseModel):
    access_token: str
    token_type: str

class KullaniciCevap(BaseModel):
    id: int
    ad: str
    e_posta: str
    rol: str
    aktif: bool
    olusturulma_tarihi: datetime
    class Config:
        from_attributes = True

class KategoriOlustur(BaseModel):
    ad: str
    aciklama: Optional[str] = None

class KategoriCevap(BaseModel):
    id: int
    ad: str
    aciklama: Optional[str]
    aktif: bool
    olusturulma_tarihi: datetime
    class Config:
        from_attributes = True

class UrunOlustur(BaseModel):
    ad: str
    aciklama: Optional[str] = None
    fiyat: Decimal
    stok: Optional[int] = None
    kategori_id: Optional[int] = None

class UrunCevap(BaseModel):
    id: int
    ad: str
    aciklama: Optional[str]
    fiyat: Decimal
    stok: Optional[int]
    aktif: bool
    kategori_id: Optional[int]
    olusturulma_tarihi: datetime
    class Config:
        from_attributes = True

class SiparisKalemiOlustur(BaseModel):
    urun_id: int
    adet: int

class SiparisOlustur(BaseModel):
    kargo_adres: Optional[str] = None
    kalemler: list[SiparisKalemiOlustur]

class SiparisKalemiCevap(BaseModel):
    id: int
    urun_adi: str
    birim_fiyat: Decimal
    adet: int
    class Config:
        from_attributes = True

class SiparisCevap(BaseModel):
    id: int
    durum: str
    toplam_tutar: Decimal
    kargo_adres: Optional[str]
    olusturulma_tarihi: datetime
    kalemler: list[SiparisKalemiCevap]
    class Config:
        from_attributes = True
