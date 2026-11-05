from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class Kategori(Base):
    __tablename__ = "kategoriler"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ad: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    aciklama: Mapped[str | None] = mapped_column(Text, nullable=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    olusturulma_tarihi: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    urunler: Mapped[list["Urun"]] = relationship(back_populates="kategori")

class Urun(Base):
    __tablename__ = "urunler"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ad: Mapped[str] = mapped_column(String(120), nullable=False)
    aciklama: Mapped[str | None] = mapped_column(Text, nullable=True)
    fiyat: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stok: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gorsel_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kategori_id: Mapped[int | None] = mapped_column(ForeignKey("kategoriler.id"), nullable=True)
    olusturulma_tarihi: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    kategori: Mapped["Kategori | None"] = relationship(back_populates="urunler")

class KullaniciRol:
    MUSTERI = "musteri"
    YONETICI = "yonetici"

class Kullanici(Base):
    __tablename__ = "kullanicilar"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ad: Mapped[str] = mapped_column(String(120), nullable=False)
    e_posta: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    sifre_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), default=KullaniciRol.MUSTERI, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    olusturulma_tarihi: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    siparisler: Mapped[list["Siparis"]] = relationship(back_populates="kullanici")

class GirisDenemesi(Base):
    """Basarisiz giris sayaci (bkz. giris_siniri.py)."""
    __tablename__ = "giris_denemeleri"
    anahtar: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256, e-posta/IP duz metin saklanmaz
    sayi: Mapped[int] = mapped_column(Integer, nullable=False)
    pencere_basi: Mapped[int] = mapped_column(BigInteger, nullable=False)  # unix zamani (saniye)

class Adres(Base):
    __tablename__ = "adresler"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kullanici_id: Mapped[int] = mapped_column(ForeignKey("kullanicilar.id"), index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(60), nullable=False)
    adres: Mapped[str] = mapped_column(Text, nullable=False)
    varsayilan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    olusturulma_tarihi: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SiparisDurum:
    ODEME_BEKLIYOR = "odeme_bekliyor"
    ODENDI = "odendi"
    KARGOYA_VERILDI = "kargoya_verildi"
    TESLIM_EDILDI = "teslim_edildi"
    IPTAL_EDILDI = "iptal_edildi"

    # Bir durumdan hangi durumlara gecilebilir (yonetici durum guncellemesi icin)
    GECISLER = {
        "odeme_bekliyor": ["odendi", "iptal_edildi"],
        "odendi": ["kargoya_verildi", "iptal_edildi"],
        "kargoya_verildi": ["teslim_edildi"],
        "teslim_edildi": [],
        "iptal_edildi": [],
    }
    # Ciroya sayilan (odemesi alinmis) durumlar
    ODENMIS = ["odendi", "kargoya_verildi", "teslim_edildi"]

class Siparis(Base):
    __tablename__ = "siparisler"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kullanici_id: Mapped[int] = mapped_column(ForeignKey("kullanicilar.id"), nullable=False)
    durum: Mapped[str] = mapped_column(String(30), default=SiparisDurum.ODEME_BEKLIYOR, nullable=False)
    toplam_tutar: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    kargo_adres: Mapped[str | None] = mapped_column(Text, nullable=True)
    takip_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    olusturulma_tarihi: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    kullanici: Mapped[Kullanici] = relationship(back_populates="siparisler")
    kalemler: Mapped[list["SiparisKalemi"]] = relationship(back_populates="siparis", cascade="all, delete-orphan")

    @property
    def musteri_ad(self) -> str | None:
        return self.kullanici.ad if self.kullanici else None

class SiparisKalemi(Base):
    __tablename__ = "siparis_kalemleri"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    siparis_id: Mapped[int] = mapped_column(ForeignKey("siparisler.id"), nullable=False)
    urun_id: Mapped[int | None] = mapped_column(ForeignKey("urunler.id"), nullable=True)
    urun_adi: Mapped[str] = mapped_column(String(120), nullable=False)
    birim_fiyat: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    adet: Mapped[int] = mapped_column(Integer, nullable=False)
    siparis: Mapped[Siparis] = relationship(back_populates="kalemler")
