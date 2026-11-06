"""PayTR kart odemesi. PayTR'a gercek istek gitmez, token cevabi taklit edilir."""
import base64
import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from conftest import kayit_ol

import giris_siniri
import main
import models
import paytr
from database import SessionLocal, engine

ADRES = "Ataturk Mah. Cicek Sok. No:5 Kadikoy / Istanbul"
TELEFON = "05551112233"
ANAHTAR = "deneme-anahtar"
TUZ = "deneme-tuz"
sadece_postgres = pytest.mark.skipif(engine.dialect.name != "postgresql", reason="SQLite satir kilidi desteklemez")


class SahteCevap:
    def __init__(self, icerik):
        self.icerik = icerik

    def json(self):
        return self.icerik


@pytest.fixture(autouse=True)
def ayarlar(monkeypatch):
    monkeypatch.setenv("PAYTR_MERCHANT_ID", "123456")
    monkeypatch.setenv("PAYTR_MERCHANT_KEY", ANAHTAR)
    monkeypatch.setenv("PAYTR_MERCHANT_SALT", TUZ)
    monkeypatch.setenv("PAYTR_DONUS_ADRESI", "https://api.ornek.com/")
    monkeypatch.setenv("PAYTR_TEST_MODU", "0")
    monkeypatch.delenv("PAYTR_MAX_TAKSIT", raising=False)
    monkeypatch.delenv("PAYTR_YEREL_IP", raising=False)


@pytest.fixture()
def paytr_istegi(monkeypatch):
    """PayTR'a giden istegi yakalar ve basarili token cevabi verir."""
    istekler = []

    def sahte_post(adres, data, timeout):
        istekler.append((adres, data))
        return SahteCevap({"status": "success", "token": "sahte-token"})

    monkeypatch.setattr(paytr.requests, "post", sahte_post)
    return istekler


def imza(oid, durum, toplam, anahtar=ANAHTAR, tuz=TUZ):
    ozet = hmac.new(anahtar.encode(), f"{oid}{tuz}{durum}{toplam}".encode(), hashlib.sha256).digest()
    return base64.b64encode(ozet).decode()


def bildirim(client, oid, durum="success", toplam="20000", **ek):
    veri = {"merchant_oid": oid, "status": durum, "total_amount": toplam, "hash": imza(oid, durum, toplam), **ek}
    return client.post("/odeme/paytr/bildirim", data=veri)


def siparis_ac(client, yonetici, musteri, fiyat="100.00", stok=5, adet=2):
    urun = client.post("/urunler", json={"ad": "Şık Elbise", "fiyat": fiyat, "stok": stok}, headers=yonetici).json()
    govde = {"kargo_adres": ADRES, "kalemler": [{"urun_id": urun["id"], "adet": adet}]}
    r = client.post("/siparisler", json=govde, headers=musteri)
    assert r.status_code == 200, r.text
    return r.json()["id"], urun["id"]


def odeme_baslat(client, musteri, sid, telefon=TELEFON):
    r = client.post(f"/siparisler/{sid}/odeme/paytr", json={"telefon": telefon}, headers=musteri)
    assert r.status_code == 200, r.text
    return r.json()["merchant_oid"]


def siparis_durumu(client, sid, musteri):
    return client.get(f"/siparisler/{sid}", headers=musteri).json()["durum"]


def denemeyi_eskit(oid):
    db = SessionLocal()
    try:
        odeme = db.get(models.PaytrOdeme, oid)
        odeme.olusturulma = int(time.time()) - main.ODEME_ZAMAN_ASIMI_SANIYE - 1
        db.commit()
    finally:
        db.close()


def temizlik():
    db = SessionLocal()
    try:
        return main.suresi_dolan_odemeleri_iptal_et(db)
    finally:
        db.close()


# ---------------------------------------------------- baslatma

def test_baslatma_tutari_siparisten_alir_ve_dogru_imzalar(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    r = client.post(f"/siparisler/{sid}/odeme/paytr", json={"telefon": TELEFON}, headers=musteri)
    assert r.status_code == 200, r.text
    govde = r.json()
    assert govde["odeme_url"] == "https://www.paytr.com/odeme/guvenli/sahte-token"
    assert govde["test_modu"] is False

    adres, d = paytr_istegi[0]
    assert adres == "https://www.paytr.com/odeme/api/get-token"
    assert d["payment_amount"] == "20000"
    assert d["merchant_oid"] == govde["merchant_oid"]
    assert d["merchant_oid"].isalnum() and d["merchant_oid"].startswith("BUTIK")
    assert d["merchant_ok_url"] == "https://api.ornek.com/odeme/paytr/tamam"
    assert d["merchant_fail_url"] == "https://api.ornek.com/odeme/paytr/hata"
    assert d["user_phone"] == TELEFON and d["user_address"] == ADRES
    assert (d["no_installment"], d["max_installment"], d["test_mode"]) == ("1", "0", "0")
    assert json.loads(base64.b64decode(d["user_basket"])) == [["Şık Elbise", "100.00", 2]]

    # Belgedeki sira: id, ip, oid, email, tutar, sepet, taksitsiz, taksit, para birimi, test, tuz
    metin = "".join(d[a] for a in ("merchant_id", "user_ip", "merchant_oid", "email", "payment_amount", "user_basket",
                                   "no_installment", "max_installment", "currency", "test_mode")) + TUZ
    beklenen = base64.b64encode(hmac.new(ANAHTAR.encode(), metin.encode(), hashlib.sha256).digest()).decode()
    assert d["paytr_token"] == beklenen


def test_ayar_yoksa_kart_kapali(client, yonetici, musteri, monkeypatch, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    assert client.get("/ayarlar").json()["kart_odeme"] is True
    monkeypatch.delenv("PAYTR_MERCHANT_KEY")
    assert client.get("/ayarlar").json()["kart_odeme"] is False
    assert client.post(f"/siparisler/{sid}/odeme/paytr", json={"telefon": TELEFON}, headers=musteri).status_code == 503
    assert paytr_istegi == []


def test_test_modu_acikca_belirtilmezse_kart_kapali(monkeypatch):
    monkeypatch.delenv("PAYTR_TEST_MODU")
    assert paytr.ayarlar() is None
    monkeypatch.setenv("PAYTR_TEST_MODU", "evet")
    assert paytr.ayarlar() is None


def test_baskasinin_siparisi_icin_baslatilamaz(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    r = client.post(f"/siparisler/{sid}/odeme/paytr", json={"telefon": TELEFON}, headers=yonetici)
    assert r.status_code == 404
    assert paytr_istegi == []


def test_iptal_siparis_icin_baslatilamaz(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    client.post(f"/siparisler/{sid}/iptal", headers=musteri)
    r = client.post(f"/siparisler/{sid}/odeme/paytr", json={"telefon": TELEFON}, headers=musteri)
    assert r.status_code == 400
    assert paytr_istegi == []


def test_telefon_gerekli_ve_saklanir(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    assert client.post(f"/siparisler/{sid}/odeme/paytr", json={}, headers=musteri).status_code == 400
    assert client.post(f"/siparisler/{sid}/odeme/paytr", json={"telefon": "abc"}, headers=musteri).status_code == 422
    odeme_baslat(client, musteri, sid)
    assert client.get("/ben", headers=musteri).json()["telefon"] == TELEFON
    assert client.post(f"/siparisler/{sid}/odeme/paytr", json={}, headers=musteri).status_code == 200
    assert paytr_istegi[-1][1]["user_phone"] == TELEFON


def test_her_denemede_yeni_numara(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    assert odeme_baslat(client, musteri, sid) != odeme_baslat(client, musteri, sid)


def test_baslatma_siniri(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    for _ in range(giris_siniri.ODEME_BASLATMA_SINIRI):
        odeme_baslat(client, musteri, sid)
    r = client.post(f"/siparisler/{sid}/odeme/paytr", json={"telefon": TELEFON}, headers=musteri)
    assert r.status_code == 429


@pytest.mark.parametrize("sahte", [
    lambda *a, **k: SahteCevap({"status": "failed", "reason": "gizli ayrinti"}),
    lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError()),
])
def test_paytr_hatasi_musteriye_sizmaz_ve_siparis_bozulmaz(client, yonetici, musteri, monkeypatch, sahte):
    sid, _ = siparis_ac(client, yonetici, musteri)
    monkeypatch.setattr(paytr.requests, "post", sahte)
    r = client.post(f"/siparisler/{sid}/odeme/paytr", json={"telefon": TELEFON}, headers=musteri)
    assert r.status_code == 502
    assert "gizli" not in r.text
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"
    db = SessionLocal()
    try:
        assert db.query(models.PaytrOdeme).one().durum == models.PaytrDurum.TOKEN_ALINAMADI
    finally:
        db.close()


def test_yerel_ip_ayari(monkeypatch):
    monkeypatch.setenv("PAYTR_YEREL_IP", "203.0.113.7")

    class Istemci:
        host = "127.0.0.1"

    class Istek:
        client = Istemci()

    assert main._odeme_ip(Istek(), paytr.ayarlar()) == "203.0.113.7"
    Istemci.host = "8.8.8.8"
    assert main._odeme_ip(Istek(), paytr.ayarlar()) == "8.8.8.8"


@pytest.mark.parametrize("deger,taksitsiz,en_fazla", [("1", "1", "0"), ("0", "0", "0"), ("6", "0", "6")])
def test_taksit_ayari(client, yonetici, musteri, paytr_istegi, monkeypatch, deger, taksitsiz, en_fazla):
    monkeypatch.setenv("PAYTR_MAX_TAKSIT", deger)
    sid, _ = siparis_ac(client, yonetici, musteri)
    odeme_baslat(client, musteri, sid)
    d = paytr_istegi[0][1]
    assert (d["no_installment"], d["max_installment"]) == (taksitsiz, en_fazla)


# ---------------------------------------------------- bildirim

def test_basarili_bildirim_siparisi_odendi_yapar(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    r = bildirim(client, oid)
    assert r.status_code == 200 and r.text == "OK"
    assert siparis_durumu(client, sid, musteri) == "odendi"
    durum = client.get(f"/odeme/paytr/{oid}", headers=musteri).json()
    assert durum["durum"] == "basarili" and durum["siparis_durum"] == "odendi"


@pytest.mark.parametrize("bozuk", [
    {"hash": "yanlis"},
    {"hash": imza("X", "success", "20000")},
    {"hash": imza("{oid}", "success", "20000", anahtar="baska-anahtar")},
    {"total_amount": "99999999"},
])
def test_gecersiz_imza_reddedilir(client, yonetici, musteri, paytr_istegi, bozuk):
    sid, _ = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    veri = {"merchant_oid": oid, "status": "success", "total_amount": "20000", "hash": imza(oid, "success", "20000")}
    veri.update(bozuk)
    r = client.post("/odeme/paytr/bildirim", data=veri)
    assert r.status_code == 400 and r.text != "OK"
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"


def test_tamam_sayfasi_siparisi_odendi_yapmaz(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    odeme_baslat(client, musteri, sid)
    assert client.get("/odeme/paytr/tamam").status_code == 200
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"


def test_bilinmeyen_siparis_icin_ok_donulmez(client):
    r = bildirim(client, "WEBSITE123")
    assert r.status_code == 404 and r.text != "OK"


def test_tekrar_gelen_bildirim_bir_kez_islenir(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    assert bildirim(client, oid).text == "OK"
    client.patch(f"/siparisler/{sid}/durum", json={"durum": "kargoya_verildi"}, headers=yonetici)
    assert bildirim(client, oid).text == "OK"
    assert siparis_durumu(client, sid, musteri) == "kargoya_verildi"
    assert client.get("/yonetim/odeme-sorunlari", headers=yonetici).json() == []


def test_basarisiz_bildirim_siparisi_bekletir_ve_yeniden_denenir(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    r = bildirim(client, oid, durum="failed", toplam="0", failed_reason_code="6", failed_reason_msg="Limit yetersiz")
    assert r.text == "OK"
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"
    assert client.get(f"/odeme/paytr/{oid}", headers=musteri).json()["hata_mesaji"] == "Limit yetersiz"
    # basarisizdan sonra gelen basarili ayni numara icin dikkate alinmaz (ilk bildirim gecerli)
    assert bildirim(client, oid).text == "OK"
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"
    assert bildirim(client, odeme_baslat(client, musteri, sid)).text == "OK"
    assert siparis_durumu(client, sid, musteri) == "odendi"


def test_vade_farkiyla_yuksek_tutar_kabul_edilir(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    assert bildirim(client, odeme_baslat(client, musteri, sid), toplam="21500").text == "OK"
    assert siparis_durumu(client, sid, musteri) == "odendi"


def test_eksik_tutar_siparisi_odendi_yapmaz(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    assert bildirim(client, oid, toplam="100").text == "OK"
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"
    sorunlar = client.get("/yonetim/odeme-sorunlari", headers=yonetici).json()
    assert [(s["merchant_oid"], s["inceleme_nedeni"]) for s in sorunlar] == [(oid, "tutar_uyusmazligi")]


def test_yabanci_para_birimi_incelemeye_duser(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    assert bildirim(client, odeme_baslat(client, musteri, sid), currency="USD").text == "OK"
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"


def test_gercek_denemeye_test_bildirimi_siparisi_odendi_yapmaz(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    assert bildirim(client, odeme_baslat(client, musteri, sid), test_mode="1").text == "OK"
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"
    assert client.get("/yonetim/odeme-sorunlari", headers=yonetici).json()[0]["inceleme_nedeni"] == "test_bildirimi"


def test_test_modundaki_deneme_test_bildirimiyle_odenir(client, yonetici, musteri, paytr_istegi, monkeypatch):
    monkeypatch.setenv("PAYTR_TEST_MODU", "1")
    sid, _ = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    assert paytr_istegi[0][1]["test_mode"] == "1"
    assert bildirim(client, oid, test_mode="1").text == "OK"
    assert siparis_durumu(client, sid, musteri) == "odendi"


def test_iptal_edilmis_siparise_gelen_odeme_incelemeye_duser(client, yonetici, musteri, paytr_istegi):
    sid, uid = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    client.post(f"/siparisler/{sid}/iptal", headers=musteri)
    assert bildirim(client, oid).text == "OK"
    assert siparis_durumu(client, sid, musteri) == "iptal_edildi"
    assert client.get(f"/urunler/{uid}").json()["stok"] == 5
    assert client.get("/yonetim/odeme-sorunlari", headers=yonetici).json()[0]["inceleme_nedeni"] == "iptal_siparise_odeme"


def test_ikinci_odeme_incelemeye_duser(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    ilk, ikinci = odeme_baslat(client, musteri, sid), odeme_baslat(client, musteri, sid)
    bildirim(client, ilk)
    assert bildirim(client, ikinci).text == "OK"
    assert client.get("/yonetim/odeme-sorunlari", headers=yonetici).json()[0]["inceleme_nedeni"] == "zaten_odenmis_siparis"


def test_odeme_durumu_ve_sorunlar_yetki_ister(client, yonetici, musteri, paytr_istegi):
    kayit_ol(client, "Baska", "baska@example.com")
    baska = {"Authorization": "Bearer " + client.post("/giris", data={"username": "baska@example.com", "password": "sifre123"}).json()["access_token"]}
    sid, _ = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    assert client.get(f"/odeme/paytr/{oid}", headers=baska).status_code == 404
    assert client.get(f"/odeme/paytr/{oid}", headers=yonetici).status_code == 200
    assert client.get("/yonetim/odeme-sorunlari", headers=musteri).status_code == 403


# ---------------------------------------------------- zaman asimi

def test_terk_edilen_odeme_iptal_olur_ve_stok_doner(client, yonetici, musteri, paytr_istegi):
    sid, uid = siparis_ac(client, yonetici, musteri)
    assert client.get(f"/urunler/{uid}").json()["stok"] == 3
    denemeyi_eskit(odeme_baslat(client, musteri, sid))
    assert temizlik() == 1
    assert siparis_durumu(client, sid, musteri) == "iptal_edildi"
    assert client.get(f"/urunler/{uid}").json()["stok"] == 5
    assert temizlik() == 0
    assert client.get(f"/urunler/{uid}").json()["stok"] == 5


def test_havale_siparisine_dokunulmaz(client, yonetici, musteri):
    sid, _ = siparis_ac(client, yonetici, musteri)
    assert temizlik() == 0
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"


def test_yeni_deneme_varken_iptal_edilmez(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    denemeyi_eskit(odeme_baslat(client, musteri, sid))
    odeme_baslat(client, musteri, sid)
    assert temizlik() == 0
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"


def test_token_alinamayan_deneme_sureyi_baslatmaz(client, yonetici, musteri, monkeypatch):
    sid, _ = siparis_ac(client, yonetici, musteri)
    monkeypatch.setattr(paytr.requests, "post", lambda *a, **k: SahteCevap({"status": "failed", "reason": "x"}))
    client.post(f"/siparisler/{sid}/odeme/paytr", json={"telefon": TELEFON}, headers=musteri)
    db = SessionLocal()
    try:
        oid = db.query(models.PaytrOdeme).one().merchant_oid
    finally:
        db.close()
    denemeyi_eskit(oid)
    assert temizlik() == 0
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"


def test_para_alinmis_ama_incelemedeki_siparis_iptal_edilmez(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    bildirim(client, oid, toplam="100")
    denemeyi_eskit(oid)
    assert temizlik() == 0
    assert siparis_durumu(client, sid, musteri) == "odeme_bekliyor"


# ---------------------------------------------------- ayni anda

@sadece_postgres
def test_ayni_anda_gelen_bildirimler_bir_kez_islenir(client, yonetici, musteri, paytr_istegi):
    sid, _ = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    with ThreadPoolExecutor(10) as havuz:
        yanitlar = list(havuz.map(lambda _: bildirim(client, oid), range(10)))
    assert all(r.text == "OK" for r in yanitlar)
    assert siparis_durumu(client, sid, musteri) == "odendi"
    assert client.get("/yonetim/odeme-sorunlari", headers=yonetici).json() == []


@sadece_postgres
def test_iptal_ve_odeme_yarisinda_para_kaybolmaz(client, yonetici, musteri, paytr_istegi):
    """Hangisi once gelirse gelsin: ya siparis odendi olur ya da odeme incelemeye duser. Stok bir kez doner."""
    for _ in range(5):
        sid, uid = siparis_ac(client, yonetici, musteri)
        oid = odeme_baslat(client, musteri, sid)
        with ThreadPoolExecutor(2) as havuz:
            odeme_is = havuz.submit(bildirim, client, oid)
            iptal_is = havuz.submit(client.post, f"/siparisler/{sid}/iptal", headers=musteri)
        assert odeme_is.result().text == "OK"
        stok = client.get(f"/urunler/{uid}").json()["stok"]
        sorunlu = {s["merchant_oid"] for s in client.get("/yonetim/odeme-sorunlari", headers=yonetici).json()}
        if iptal_is.result().status_code == 200:
            assert siparis_durumu(client, sid, musteri) == "iptal_edildi"
            assert oid in sorunlu and stok == 5
        else:
            assert siparis_durumu(client, sid, musteri) == "odendi"
            assert oid not in sorunlu and stok == 3


@sadece_postgres
def test_ayni_anda_temizlik_stogu_bir_kez_iade_eder(client, yonetici, musteri, paytr_istegi):
    sid, uid = siparis_ac(client, yonetici, musteri)
    oid = odeme_baslat(client, musteri, sid)
    denemeyi_eskit(oid)
    with ThreadPoolExecutor(6) as havuz:
        sonuclar = list(havuz.map(lambda _: temizlik(), range(6)))
    assert sum(sonuclar) == 1
    assert client.get(f"/urunler/{uid}").json()["stok"] == 5
