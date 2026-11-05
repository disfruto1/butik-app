import re

import pytest

import eposta
import giris_siniri
import sifre_sifirlama
from database import SessionLocal
from models import Kullanici, SifreSifirlamaKodu

E_POSTA = "musteri@example.com"
YENI = "yeni-sifre-456"


@pytest.fixture()
def gelenler(monkeypatch):
    kutu = []

    def sahte_gonder(alici, konu, metin):
        kutu.append({"alici": alici, "kod": re.search(r"\b\d{8}\b", metin).group()})
        return True

    monkeypatch.setattr(eposta, "gonder", sahte_gonder)
    return kutu


def iste(client, e_posta=E_POSTA):
    return client.post("/sifre-sifirlama/iste", json={"e_posta": e_posta})


def tamamla(client, kod, sifre=YENI, e_posta=E_POSTA):
    return client.post("/sifre-sifirlama/tamamla", json={"e_posta": e_posta, "kod": kod, "yeni_sifre": sifre})


def giris(client, sifre):
    return client.post("/giris", data={"username": E_POSTA, "password": sifre})


def yanlis_kod(dogru):
    return "00000000" if dogru != "00000000" else "11111111"


def test_kodla_sifre_degisir(client, musteri, gelenler):
    assert iste(client).status_code == 200
    assert gelenler[0]["alici"] == E_POSTA
    assert tamamla(client, gelenler[0]["kod"]).status_code == 200
    assert giris(client, YENI).status_code == 200
    assert giris(client, "sifre123").status_code == 401


def test_sifre_degisince_eski_oturum_kapanir(client, musteri, gelenler):
    assert client.get("/ben", headers=musteri).status_code == 200
    iste(client)
    tamamla(client, gelenler[0]["kod"])
    assert client.get("/ben", headers=musteri).status_code == 401
    yeni = giris(client, YENI).json()["access_token"]
    assert client.get("/ben", headers={"Authorization": "Bearer " + yeni}).status_code == 200


def test_surumsuz_eski_token_calismaya_devam_eder(client, musteri):
    # Bu ozellikten once verilmis oturumlar yukseltmede dusmemeli
    from auth import token_olustur
    eski = token_olustur({"sub": E_POSTA})
    assert client.get("/ben", headers={"Authorization": "Bearer " + eski}).status_code == 200


def test_kayitli_olmayan_eposta_ayni_yaniti_alir(client, musteri, gelenler):
    var = iste(client)
    yok = iste(client, "yok@example.com")
    assert (var.status_code, var.json()) == (yok.status_code, yok.json())
    assert len(gelenler) == 1


def test_kod_tek_kullanimliktir(client, musteri, gelenler):
    iste(client)
    assert tamamla(client, gelenler[0]["kod"]).status_code == 200
    assert tamamla(client, gelenler[0]["kod"], "baska-sifre-789").status_code == 400
    assert giris(client, YENI).status_code == 200


def test_yeni_kod_eskisini_iptal_eder(client, musteri, gelenler):
    iste(client)
    iste(client)
    assert gelenler[0]["kod"] != gelenler[1]["kod"]
    assert tamamla(client, gelenler[0]["kod"]).status_code == 400
    assert tamamla(client, gelenler[1]["kod"]).status_code == 200


def test_sure_dolunca_kod_gecmez(client, musteri, gelenler, monkeypatch):
    iste(client)
    simdi = sifre_sifirlama._simdi()
    monkeypatch.setattr(sifre_sifirlama, "_simdi", lambda: simdi + sifre_sifirlama.KOD_SURESI_SANIYE + 1)
    assert tamamla(client, gelenler[0]["kod"]).status_code == 400
    assert giris(client, "sifre123").status_code == 200


def test_bes_yanlis_denemede_kod_iptal_olur(client, musteri, gelenler):
    iste(client)
    dogru = gelenler[0]["kod"]
    for _ in range(sifre_sifirlama.KOD_DENEME_SINIRI):
        assert tamamla(client, yanlis_kod(dogru)).status_code == 400
    assert tamamla(client, dogru).status_code == 400
    assert giris(client, "sifre123").status_code == 200


def test_baskasinin_kodu_gecmez(client, musteri, yonetici, gelenler):
    iste(client)
    r = tamamla(client, gelenler[0]["kod"], e_posta="yonetici@example.com")
    assert r.status_code == 400
    assert client.post("/giris", data={"username": "yonetici@example.com", "password": "sifre123"}).status_code == 200


def test_ayni_epostaya_kod_siniri(client, musteri, gelenler):
    for _ in range(giris_siniri.SIFIRLAMA_EPOSTA_SINIRI):
        assert iste(client).status_code == 200
    r = iste(client)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    assert len(gelenler) == giris_siniri.SIFIRLAMA_EPOSTA_SINIRI


def test_ayni_ipden_istek_siniri(client, musteri, gelenler, monkeypatch):
    monkeypatch.setattr(giris_siniri, "SIFIRLAMA_IP_SINIRI", 2)
    assert iste(client, "a@example.com").status_code == 200
    assert iste(client, "b@example.com").status_code == 200
    assert iste(client, "c@example.com").status_code == 429


def test_ayni_ipden_kod_deneme_siniri(client, musteri, gelenler, monkeypatch):
    monkeypatch.setattr(giris_siniri, "SIFIRLAMA_DENEME_IP_SINIRI", 2)
    assert tamamla(client, "12345678").status_code == 400
    assert tamamla(client, "12345678").status_code == 400
    assert tamamla(client, "12345678").status_code == 429


def test_sifirlama_giris_kilidini_kaldirir(client, musteri, gelenler):
    for _ in range(giris_siniri.HESAP_SINIRI):
        assert giris(client, "yanlis").status_code == 401
    assert giris(client, "sifre123").status_code == 429
    iste(client)
    tamamla(client, gelenler[0]["kod"])
    assert giris(client, YENI).status_code == 200


def test_kod_veritabaninda_duz_saklanmaz(client, musteri, gelenler):
    iste(client)
    db = SessionLocal()
    try:
        kayit = db.query(SifreSifirlamaKodu).one()
        assert gelenler[0]["kod"] not in kayit.kod_ozeti
        assert len(kayit.kod_ozeti) == 64
    finally:
        db.close()


@pytest.mark.parametrize("govde", [
    {"kod": "1234", "yeni_sifre": YENI},
    {"kod": "abcdefgh", "yeni_sifre": YENI},
    {"kod": "12345678", "yeni_sifre": "kisa"},
    {"kod": "12345678", "yeni_sifre": "x" * 73},
])
def test_gecersiz_girdi_reddedilir(client, musteri, govde):
    assert client.post("/sifre-sifirlama/tamamla", json={"e_posta": E_POSTA, **govde}).status_code == 422


def test_eposta_gonderilemese_de_yanit_ayni(client, musteri, monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("EPOSTA_KONSOLA_YAZ", raising=False)
    assert iste(client).status_code == 200


def test_smtp_ayari_yoksa_gonder_false_doner(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("EPOSTA_KONSOLA_YAZ", raising=False)
    assert eposta.gonder("a@example.com", "konu", "metin") is False


def test_smtp_hatasi_firlatilmaz(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", "1")  # kapali port
    assert eposta.gonder("a@example.com", "konu", "metin") is False


def test_token_surumu_yeni_kullanicida_sifirdir(client, musteri):
    db = SessionLocal()
    try:
        assert db.query(Kullanici).filter(Kullanici.e_posta == E_POSTA).one().token_surumu == 0
    finally:
        db.close()
