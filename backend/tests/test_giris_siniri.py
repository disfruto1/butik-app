import pytest
from fastapi.testclient import TestClient

import giris_siniri
from database import SessionLocal
from main import app
from models import GirisDenemesi

E_POSTA = "musteri@example.com"


def giris(client, sifre="yanlis-sifre", e_posta=E_POSTA):
    return client.post("/giris", data={"username": e_posta, "password": sifre})


def yanlis_dene(client, adet, e_posta=E_POSTA):
    for _ in range(adet):
        assert giris(client, e_posta=e_posta).status_code == 401


def test_sinir_dolunca_dogru_sifre_de_reddedilir(client, musteri):
    yanlis_dene(client, giris_siniri.HESAP_SINIRI)
    r = giris(client, "sifre123")
    assert r.status_code == 429
    assert 0 < int(r.headers["Retry-After"]) <= giris_siniri.PENCERE_SANIYE


def test_sinirin_altinda_giris_calisir(client, musteri):
    yanlis_dene(client, giris_siniri.HESAP_SINIRI - 1)
    assert giris(client, "sifre123").status_code == 200


def test_basarili_giris_hesap_sayacini_sifirlar(client, musteri):
    yanlis_dene(client, giris_siniri.HESAP_SINIRI - 1)
    assert giris(client, "sifre123").status_code == 200
    yanlis_dene(client, giris_siniri.HESAP_SINIRI - 1)
    assert giris(client, "sifre123").status_code == 200


def test_sure_dolunca_kilit_acilir(client, musteri, monkeypatch):
    yanlis_dene(client, giris_siniri.HESAP_SINIRI)
    assert giris(client, "sifre123").status_code == 429
    simdi = giris_siniri._simdi()
    monkeypatch.setattr(giris_siniri, "_simdi", lambda: simdi + giris_siniri.PENCERE_SANIYE + 1)
    assert giris(client, "sifre123").status_code == 200


def test_saldirgan_baskasinin_hesabini_kilitleyemez(client, musteri):
    # Saldirgan kendi IP'sinden kilitlenir, gercek kullanici baska IP'den girebilir
    yanlis_dene(client, giris_siniri.HESAP_SINIRI)
    assert giris(client, "sifre123").status_code == 429
    baska_ip = TestClient(app, client=("203.0.113.7", 50000))
    assert giris(baska_ip, "sifre123").status_code == 200


def test_ayni_ipden_baska_hesap_etkilenmez(client, musteri, yonetici):
    yanlis_dene(client, giris_siniri.HESAP_SINIRI)
    assert giris(client, "sifre123", "yonetici@example.com").status_code == 200


def test_ip_siniri_farkli_hesap_denemelerini_durdurur(client, musteri, monkeypatch):
    monkeypatch.setattr(giris_siniri, "IP_SINIRI", 3)
    for i in range(3):
        assert giris(client, e_posta=f"kisi{i}@example.com").status_code == 401
    assert giris(client, "sifre123").status_code == 429
    baska_ip = TestClient(app, client=("203.0.113.7", 50000))
    assert giris(baska_ip, "sifre123").status_code == 200


def test_basarili_giris_ip_sayacini_sifirlamaz(client, musteri, monkeypatch):
    monkeypatch.setattr(giris_siniri, "IP_SINIRI", 3)
    assert giris(client, e_posta="a@example.com").status_code == 401
    assert giris(client, e_posta="b@example.com").status_code == 401
    assert giris(client, "sifre123").status_code == 200
    assert giris(client, e_posta="c@example.com").status_code == 401
    assert giris(client, "sifre123").status_code == 429


def test_basarili_girisler_ip_sayacini_doldurmaz(client, musteri, monkeypatch):
    # Ayni IP'yi paylasan musteriler (mobil operator agi) birbirini kilitlememeli
    monkeypatch.setattr(giris_siniri, "IP_SINIRI", 3)
    for _ in range(6):
        assert giris(client, "sifre123").status_code == 200


def test_kayitli_olmayan_eposta_ayni_davranir(client):
    # Yanit farki olursa hangi e-postalarin kayitli oldugu anlasilir
    r = giris(client, e_posta="yok@example.com")
    assert r.status_code == 401
    assert r.json()["detail"] == "E-posta veya sifre yanlis"
    yanlis_dene(client, giris_siniri.HESAP_SINIRI - 1, "yok@example.com")
    assert giris(client, e_posta="yok@example.com").status_code == 429


def test_buyuk_harfli_eposta_ayni_sayaca_yazilir(client, musteri):
    yanlis_dene(client, giris_siniri.HESAP_SINIRI, E_POSTA.upper())
    assert giris(client, "sifre123").status_code == 429


def test_cok_uzun_sifre_hata_vermez(client, musteri):
    assert giris(client, "x" * 5000).status_code == 401


def test_eposta_duz_metin_saklanmaz(client, musteri):
    yanlis_dene(client, 1, "sifremi-yanlis-alana-yazdim")
    db = SessionLocal()
    try:
        kayitlar = db.query(GirisDenemesi).all()
        assert kayitlar
        assert all("sifremi" not in k.anahtar and len(k.anahtar) == 64 for k in kayitlar)
    finally:
        db.close()


def test_suresi_dolan_kayitlar_temizlenir(client, musteri, monkeypatch):
    yanlis_dene(client, 1, "eski@example.com")
    simdi = giris_siniri._simdi()
    monkeypatch.setattr(giris_siniri, "_simdi", lambda: simdi + giris_siniri.PENCERE_SANIYE + 1)
    yanlis_dene(client, 1, "yeni@example.com")
    db = SessionLocal()
    try:
        # eski hesap sayaci silindi; yeni hesap sayaci ve yenilenen IP sayaci kaldi
        assert db.query(GirisDenemesi).count() == 2
    finally:
        db.close()
