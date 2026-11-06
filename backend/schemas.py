from decimal import Decimal
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field


class KullaniciOlustur(BaseModel):
    ad: str = Field(min_length=1, max_length=120)
    e_posta: EmailStr
    sifre: str = Field(min_length=6, max_length=72)  # bcrypt en fazla 72 bayt isler
    aydinlatma_okundu: bool = False
    metin_surumu: str = Field(default="", max_length=16)  # /yasal/kayit'tan alinan, musterinin gordugu metnin surumu
    eposta_izni: bool = False
    sms_izni: bool = False
    telefon: Optional[str] = Field(default=None, pattern=r"^\+?[0-9][0-9 ()-]{9,19}$")  # SMS izni icin zorunlu


class SifirlamaIstek(BaseModel):
    e_posta: EmailStr


class SifirlamaTamamla(BaseModel):
    e_posta: EmailStr
    kod: str = Field(min_length=8, max_length=8, pattern=r"^[0-9]{8}$")
    yeni_sifre: str = Field(min_length=6, max_length=72)


class Token(BaseModel):
    access_token: str
    token_type: str


class KullaniciCevap(BaseModel):
    id: int
    ad: str
    e_posta: str
    rol: str
    aktif: bool
    telefon: Optional[str] = None
    olusturulma_tarihi: datetime

    class Config:
        from_attributes = True


class KategoriOlustur(BaseModel):
    ad: str = Field(min_length=1, max_length=120)
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
    ad: str = Field(min_length=1, max_length=120)
    aciklama: Optional[str] = None
    fiyat: Decimal = Field(ge=0)
    stok: Optional[int] = Field(default=None, ge=0)
    gorsel_url: Optional[str] = Field(default=None, max_length=500)
    kategori_id: Optional[int] = None


class AktifGuncelle(BaseModel):
    aktif: bool


class UrunCevap(BaseModel):
    id: int
    ad: str
    aciklama: Optional[str]
    fiyat: Decimal
    stok: Optional[int]
    aktif: bool
    gorsel_url: Optional[str] = None
    kategori_id: Optional[int]
    olusturulma_tarihi: datetime

    class Config:
        from_attributes = True


class AdresOlustur(BaseModel):
    baslik: str = Field(min_length=1, max_length=60)
    adres: str = Field(min_length=10, max_length=500)  # siparisteki kargo_adres ile ayni sinirlar


class AdresCevap(BaseModel):
    id: int
    baslik: str
    adres: str
    varsayilan: bool

    class Config:
        from_attributes = True


class SiparisKalemiOlustur(BaseModel):
    urun_id: int
    adet: int = Field(gt=0, le=1000)


class SiparisOlustur(BaseModel):
    kargo_adres: str = Field(min_length=10, max_length=500)
    kalemler: list[SiparisKalemiOlustur] = Field(min_length=1)


class SiparisKalemiCevap(BaseModel):
    id: int
    urun_id: Optional[int] = None
    urun_adi: str
    birim_fiyat: Decimal
    adet: int

    class Config:
        from_attributes = True


class SiparisCevap(BaseModel):
    id: int
    kullanici_id: int
    musteri_ad: Optional[str] = None
    durum: str
    toplam_tutar: Decimal
    kargo_adres: Optional[str]
    takip_no: Optional[str] = None
    olusturulma_tarihi: datetime
    kalemler: list[SiparisKalemiCevap]

    class Config:
        from_attributes = True


class SiparisDurumGuncelle(BaseModel):
    durum: Literal["odendi", "kargoya_verildi", "teslim_edildi", "iptal_edildi"]
    takip_no: Optional[str] = Field(default=None, max_length=100)


class OdemeBaslat(BaseModel):
    # Bos ise kullanicinin kayitli telefonu kullanilir
    telefon: Optional[str] = Field(default=None, pattern=r"^\+?[0-9][0-9 ()-]{9,19}$")


class OdemeBaslatCevap(BaseModel):
    merchant_oid: str
    odeme_url: str
    test_modu: bool


class OdemeDurumCevap(BaseModel):
    merchant_oid: str
    durum: str
    siparis_id: int
    siparis_durum: str
    hata_mesaji: Optional[str] = None


class OdemeSorunuCevap(BaseModel):
    merchant_oid: str
    siparis_id: int
    inceleme_nedeni: str
    tutar_kurus: int
    odenen_kurus: Optional[int] = None
    test_modu: bool

    class Config:
        from_attributes = True
