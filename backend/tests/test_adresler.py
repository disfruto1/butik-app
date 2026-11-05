ADRES_1 = "Ataturk Mah. Cicek Sok. No:5 Kadikoy / Istanbul"
ADRES_2 = "Cumhuriyet Cad. No:10 Daire:2 Besiktas / Istanbul"


def adres_ekle(client, kim, baslik="Ev", adres=ADRES_1):
    r = client.post("/adresler", json={"baslik": baslik, "adres": adres}, headers=kim)
    assert r.status_code == 200, r.text
    return r.json()


def test_giris_yapmadan_adres_gorulemez(client):
    assert client.get("/adresler").status_code == 401


def test_ilk_adres_varsayilan_olur_ikincisi_olmaz(client, musteri):
    assert adres_ekle(client, musteri)["varsayilan"] is True
    assert adres_ekle(client, musteri, "Is", ADRES_2)["varsayilan"] is False


def test_varsayilan_tek_olur_ve_listede_ustte_gelir(client, musteri):
    ev = adres_ekle(client, musteri)
    is_ = adres_ekle(client, musteri, "Is", ADRES_2)
    assert client.post(f"/adresler/{is_['id']}/varsayilan", headers=musteri).status_code == 200

    liste = client.get("/adresler", headers=musteri).json()
    assert [(a["id"], a["varsayilan"]) for a in liste] == [(is_["id"], True), (ev["id"], False)]


def test_adres_guncellenir_ve_bosluklar_temizlenir(client, musteri):
    ev = adres_ekle(client, musteri)
    r = client.put(f"/adresler/{ev['id']}", json={"baslik": "  Yazlik ", "adres": f"  {ADRES_2} "}, headers=musteri)
    assert r.status_code == 200
    assert r.json()["baslik"] == "Yazlik"
    assert r.json()["adres"] == ADRES_2
    assert r.json()["varsayilan"] is True  # duzenleme varsayilanligi bozmaz


def test_varsayilan_silinince_baska_adres_varsayilan_olur(client, musteri):
    ev = adres_ekle(client, musteri)
    is_ = adres_ekle(client, musteri, "Is", ADRES_2)
    assert client.delete(f"/adresler/{ev['id']}", headers=musteri).status_code == 200

    liste = client.get("/adresler", headers=musteri).json()
    assert [(a["id"], a["varsayilan"]) for a in liste] == [(is_["id"], True)]


def test_varsayilan_olmayan_silinince_varsayilan_degismez(client, musteri):
    ev = adres_ekle(client, musteri)
    is_ = adres_ekle(client, musteri, "Is", ADRES_2)
    assert client.delete(f"/adresler/{is_['id']}", headers=musteri).status_code == 200

    liste = client.get("/adresler", headers=musteri).json()
    assert [(a["id"], a["varsayilan"]) for a in liste] == [(ev["id"], True)]


def test_baskasinin_adresine_erisilemez(client, musteri, yonetici):
    # Yonetici dahil: adres kisisel veridir, rol ayricalik saglamaz
    ev = adres_ekle(client, musteri)
    assert client.get("/adresler", headers=yonetici).json() == []
    govde = {"baslik": "Ele gecirildi", "adres": ADRES_2}
    assert client.put(f"/adresler/{ev['id']}", json=govde, headers=yonetici).status_code == 404
    assert client.post(f"/adresler/{ev['id']}/varsayilan", headers=yonetici).status_code == 404
    assert client.delete(f"/adresler/{ev['id']}", headers=yonetici).status_code == 404
    assert client.get("/adresler", headers=musteri).json()[0]["baslik"] == "Ev"


def test_baskasinin_varsayilani_etkilenmez(client, musteri, yonetici):
    adres_ekle(client, musteri)
    y = adres_ekle(client, yonetici)
    assert y["varsayilan"] is True  # her kullanicinin kendi varsayilani olur
    client.post(f"/adresler/{y['id']}/varsayilan", headers=yonetici)
    assert client.get("/adresler", headers=musteri).json()[0]["varsayilan"] is True


def test_gecersiz_adres_reddedilir(client, musteri):
    assert client.post("/adresler", json={"baslik": "Ev", "adres": "kisa"}, headers=musteri).status_code == 422
    assert client.post("/adresler", json={"baslik": "", "adres": ADRES_1}, headers=musteri).status_code == 422


def test_adres_siniri(client, musteri):
    for i in range(20):
        adres_ekle(client, musteri, f"Adres {i}")
    r = client.post("/adresler", json={"baslik": "Fazla", "adres": ADRES_1}, headers=musteri)
    assert r.status_code == 400


def test_adres_silinse_de_siparisteki_adres_kalir(client, musteri, yonetici):
    urun = client.post("/urunler", json={"ad": "Elbise", "fiyat": "100.00", "stok": 5}, headers=yonetici).json()
    ev = adres_ekle(client, musteri)
    s = client.post(
        "/siparisler",
        json={"kargo_adres": ev["adres"], "kalemler": [{"urun_id": urun["id"], "adet": 1}]},
        headers=musteri,
    ).json()
    client.delete(f"/adresler/{ev['id']}", headers=musteri)
    assert client.get(f"/siparisler/{s['id']}", headers=musteri).json()["kargo_adres"] == ADRES_1
