"""Uyelikte aydinlatma ve izin kayitlari."""
from conftest import kayit_ol

import yasal_metinler
from database import SessionLocal
from models import Kullanici, KullaniciOnayi


def _onaylar(e_posta):
    db = SessionLocal()
    try:
        kullanici = db.query(Kullanici).filter(Kullanici.e_posta == e_posta).first()
        if kullanici is None:
            return None
        return {o.tur: o for o in db.query(KullaniciOnayi).filter(KullaniciOnayi.kullanici_id == kullanici.id)}
    finally:
        db.close()


def test_metinler_ve_surum_sunulur(client):
    veri = client.get("/yasal/kayit").json()
    assert veri["surum"] == yasal_metinler.SURUM
    assert "Aysu Küçük" in veri["aydinlatma"]
    assert "m. 11" in veri["aydinlatma"]
    assert "e-posta" in veri["eposta_izni"]
    assert "SMS" in veri["sms_izni"]


def test_aydinlatma_okunmadan_hesap_acilmaz(client):
    r = kayit_ol(client, "Ayse", "ayse@example.com", aydinlatma_okundu=False)
    assert r.status_code == 400
    assert _onaylar("ayse@example.com") is None


def test_eski_surumle_hesap_acilmaz(client):
    r = kayit_ol(client, "Ayse", "ayse@example.com", metin_surumu="eski")
    assert r.status_code == 409
    assert _onaylar("ayse@example.com") is None


def test_alanlar_gonderilmezse_hesap_acilmaz(client):
    r = client.post("/kayit", json={"ad": "Ayse", "e_posta": "ayse@example.com", "sifre": "sifre123"})
    assert r.status_code == 400
    assert _onaylar("ayse@example.com") is None


def test_izinsiz_uyelikte_yalnizca_aydinlatma_kaydedilir(client):
    assert kayit_ol(client, "Ayse", "ayse@example.com").status_code == 200
    onaylar = _onaylar("ayse@example.com")
    assert set(onaylar) == {"aydinlatma"}
    kayit = onaylar["aydinlatma"]
    assert kayit.verildi is True
    assert kayit.metin_surumu == yasal_metinler.SURUM
    assert kayit.ip
    assert kayit.tarih is not None


def test_izinler_kanal_ve_adresle_kaydedilir(client):
    r = kayit_ol(client, "Ayse", "Ayse@Example.com", eposta_izni=True, sms_izni=True, telefon="0555 111 22 33")
    assert r.status_code == 200
    assert r.json()["telefon"] == "0555 111 22 33"
    onaylar = _onaylar("ayse@example.com")
    assert set(onaylar) == {"aydinlatma", "eposta_izni", "sms_izni"}
    assert onaylar["eposta_izni"].iletisim_adresi == "ayse@example.com"
    assert onaylar["sms_izni"].iletisim_adresi == "0555 111 22 33"


def test_izinler_birbirinden_bagimsizdir(client):
    assert kayit_ol(client, "Ayse", "ayse@example.com", eposta_izni=True).status_code == 200
    assert set(_onaylar("ayse@example.com")) == {"aydinlatma", "eposta_izni"}
    assert kayit_ol(client, "Veli", "veli@example.com", sms_izni=True, telefon="05551112233").status_code == 200
    assert set(_onaylar("veli@example.com")) == {"aydinlatma", "sms_izni"}


def test_telefonsuz_sms_izni_reddedilir(client):
    r = kayit_ol(client, "Ayse", "ayse@example.com", sms_izni=True)
    assert r.status_code == 400
    assert _onaylar("ayse@example.com") is None


def test_sms_izni_yoksa_telefon_izin_sayilmaz(client):
    assert kayit_ol(client, "Ayse", "ayse@example.com", telefon="05551112233").status_code == 200
    assert "sms_izni" not in _onaylar("ayse@example.com")


def test_tekrar_kayit_denemesi_onay_eklemez(client):
    assert kayit_ol(client, "Ayse", "ayse@example.com").status_code == 200
    assert kayit_ol(client, "Ayse", "ayse@example.com", eposta_izni=True).status_code == 400
    assert set(_onaylar("ayse@example.com")) == {"aydinlatma"}
