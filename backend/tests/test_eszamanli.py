"""Ayni anda gelen istekler. Satir kilidi gerektirdigi icin sadece PostgreSQL'de calisir:
    TEST_DATABASE_URL=postgresql+psycopg2:///butik_test python -m pytest -q
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest

import giris_siniri
from database import engine

pytestmark = pytest.mark.skipif(engine.dialect.name != "postgresql", reason="SQLite satir kilidi desteklemez")

ADRES = "Ataturk Mah. Cicek Sok. No:5 Kadikoy / Istanbul"


def ayni_anda(adet, is_):
    with ThreadPoolExecutor(adet) as havuz:
        return list(havuz.map(is_, range(adet)))


def durumlar(yanitlar):
    return Counter(r.status_code for r in yanitlar)


def test_stok_fazla_satilmaz(client, yonetici, musteri):
    urun = client.post("/urunler", json={"ad": "Elbise", "fiyat": "100.00", "stok": 5}, headers=yonetici).json()
    govde = {"kargo_adres": ADRES, "kalemler": [{"urun_id": urun["id"], "adet": 1}]}
    yanitlar = ayni_anda(20, lambda _: client.post("/siparisler", json=govde, headers=musteri))
    assert durumlar(yanitlar) == {200: 5, 400: 15}
    assert client.get(f"/urunler/{urun['id']}").json()["stok"] == 0


def test_iptal_stogu_bir_kez_iade_eder(client, yonetici, musteri):
    urun = client.post("/urunler", json={"ad": "Elbise", "fiyat": "100.00", "stok": 5}, headers=yonetici).json()
    govde = {"kargo_adres": ADRES, "kalemler": [{"urun_id": urun["id"], "adet": 2}]}
    sid = client.post("/siparisler", json=govde, headers=musteri).json()["id"]
    yanitlar = ayni_anda(10, lambda _: client.post(f"/siparisler/{sid}/iptal", headers=musteri))
    assert durumlar(yanitlar) == {200: 1, 400: 9}
    assert client.get(f"/urunler/{urun['id']}").json()["stok"] == 5


def test_ayni_anda_giris_denemeleri_siniri_asamaz(client):
    veri = {"username": "yok@example.com", "password": "yanlis"}
    yanitlar = ayni_anda(20, lambda _: client.post("/giris", data=veri))
    assert durumlar(yanitlar) == {401: giris_siniri.HESAP_SINIRI, 429: 20 - giris_siniri.HESAP_SINIRI}


def test_ayni_anda_adres_eklenince_tek_varsayilan_olur(client, musteri):
    yanitlar = ayni_anda(10, lambda i: client.post("/adresler", json={"baslik": f"A{i}", "adres": ADRES}, headers=musteri))
    assert durumlar(yanitlar) == {200: 10}
    liste = client.get("/adresler", headers=musteri).json()
    assert sum(a["varsayilan"] for a in liste) == 1


def test_ayni_anda_varsayilan_degisince_tek_varsayilan_kalir(client, musteri):
    idler = [client.post("/adresler", json={"baslik": f"A{i}", "adres": ADRES}, headers=musteri).json()["id"] for i in range(8)]
    yanitlar = ayni_anda(8, lambda i: client.post(f"/adresler/{idler[i]}/varsayilan", headers=musteri))
    assert durumlar(yanitlar) == {200: 8}
    liste = client.get("/adresler", headers=musteri).json()
    assert sum(a["varsayilan"] for a in liste) == 1


def test_adres_siniri_ayni_anda_asilamaz(client, musteri):
    yanitlar = ayni_anda(25, lambda i: client.post("/adresler", json={"baslik": f"A{i}", "adres": ADRES}, headers=musteri))
    assert durumlar(yanitlar) == {200: 20, 400: 5}
