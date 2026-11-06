from conftest import kayit_ol

ADRES = "Ataturk Mah. Cicek Sok. No:5 Daire:3 Kadikoy / Istanbul"


def urun_ekle(client, yonetici, **kw):
    veri = {"ad": "Elbise", "fiyat": "100.00", "stok": 5}
    veri.update(kw)
    r = client.post("/urunler", json=veri, headers=yonetici)
    assert r.status_code == 200, r.text
    return r.json()


def siparis_ver(client, musteri, urun_id, adet):
    return client.post("/siparisler", json={"kargo_adres": ADRES, "kalemler": [{"urun_id": urun_id, "adet": adet}]}, headers=musteri)


# ---------------------------------------------------------------- Auth

def test_kayit_ve_giris(client):
    r = kayit_ol(client, "Ayse", "Ayse@Example.com")
    assert r.status_code == 200
    assert r.json()["rol"] == "musteri"
    # buyuk/kucuk harf farki olmadan giris
    r = client.post("/giris", data={"username": "ayse@example.com", "password": "sifre123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert client.get("/ben", headers={"Authorization": "Bearer " + token}).json()["ad"] == "Ayse"


def test_ayni_eposta_iki_kez_kayit_olamaz(client):
    assert kayit_ol(client, "Ayse", "ayse@example.com").status_code == 200
    assert kayit_ol(client, "Ayse", "AYSE@example.com").status_code == 400


def test_yanlis_sifre_401(client, musteri):
    r = client.post("/giris", data={"username": "musteri@example.com", "password": "yanlis"})
    assert r.status_code == 401


def test_tokensiz_ben_401(client):
    assert client.get("/ben").status_code == 401


# ---------------------------------------------------------------- Urunler

def test_musteri_urun_ekleyemez(client, musteri):
    r = client.post("/urunler", json={"ad": "X", "fiyat": "1"}, headers=musteri)
    assert r.status_code == 403


def test_urun_arama_kategori_ve_sayfalama(client, yonetici):
    kat = client.post("/kategoriler", json={"ad": "Elbise"}, headers=yonetici).json()
    urun_ekle(client, yonetici, ad="Kirmizi Elbise", kategori_id=kat["id"])
    urun_ekle(client, yonetici, ad="Mavi Gomlek")
    urun_ekle(client, yonetici, ad="Yesil Gomlek")

    assert len(client.get("/urunler").json()) == 3
    assert [u["ad"] for u in client.get("/urunler", params={"q": "elbise"}).json()] == ["Kirmizi Elbise"]
    assert len(client.get("/urunler", params={"q": "gomlek"}).json()) == 2
    assert len(client.get("/urunler", params={"kategori_id": kat["id"]}).json()) == 1
    assert len(client.get("/urunler", params={"limit": 2}).json()) == 2
    assert len(client.get("/urunler", params={"limit": 2, "offset": 2}).json()) == 1


def test_pasif_urun_listede_yok_yonetimde_var(client, yonetici):
    u = urun_ekle(client, yonetici)
    assert client.delete(f"/urunler/{u['id']}", headers=yonetici).status_code == 200
    assert client.get("/urunler").json() == []
    assert client.get(f"/urunler/{u['id']}").status_code == 404
    assert len(client.get("/yonetim/urunler", headers=yonetici).json()) == 1
    r = client.patch(f"/urunler/{u['id']}/aktif", json={"aktif": True}, headers=yonetici)
    assert r.json()["aktif"] is True
    assert len(client.get("/urunler").json()) == 1


def test_olmayan_kategoriyle_urun_eklenemez(client, yonetici):
    r = client.post("/urunler", json={"ad": "X", "fiyat": "1", "kategori_id": 999}, headers=yonetici)
    assert r.status_code == 400


# ---------------------------------------------------------------- Siparisler

def test_siparis_stogu_dusurur_ve_tutari_hesaplar(client, yonetici, musteri):
    u = urun_ekle(client, yonetici, fiyat="49.50", stok=5)
    r = siparis_ver(client, musteri, u["id"], 2)
    assert r.status_code == 200, r.text
    assert float(r.json()["toplam_tutar"]) == 99.0
    assert r.json()["durum"] == "odeme_bekliyor"
    assert client.get(f"/urunler/{u['id']}").json()["stok"] == 3


def test_yetersiz_stok_siparis_olmaz(client, yonetici, musteri):
    u = urun_ekle(client, yonetici, stok=1)
    assert siparis_ver(client, musteri, u["id"], 2).status_code == 400
    assert client.get(f"/urunler/{u['id']}").json()["stok"] == 1


def test_gecersiz_siparis_istekleri(client, yonetici, musteri):
    u = urun_ekle(client, yonetici)
    assert siparis_ver(client, musteri, u["id"], 0).status_code == 422
    assert client.post("/siparisler", json={"kargo_adres": "kisa", "kalemler": [{"urun_id": u["id"], "adet": 1}]}, headers=musteri).status_code == 422
    assert client.post("/siparisler", json={"kargo_adres": ADRES, "kalemler": []}, headers=musteri).status_code == 422


def test_musteri_iptal_eder_stok_geri_gelir(client, yonetici, musteri):
    u = urun_ekle(client, yonetici, stok=5)
    s = siparis_ver(client, musteri, u["id"], 3).json()
    assert client.get(f"/urunler/{u['id']}").json()["stok"] == 2
    r = client.post(f"/siparisler/{s['id']}/iptal", headers=musteri)
    assert r.status_code == 200 and r.json()["durum"] == "iptal_edildi"
    assert client.get(f"/urunler/{u['id']}").json()["stok"] == 5
    # ikinci kez iptal edilemez
    assert client.post(f"/siparisler/{s['id']}/iptal", headers=musteri).status_code == 400


def test_odenmis_siparis_musteri_tarafindan_iptal_edilemez(client, yonetici, musteri):
    u = urun_ekle(client, yonetici)
    s = siparis_ver(client, musteri, u["id"], 1).json()
    client.patch(f"/siparisler/{s['id']}/durum", json={"durum": "odendi"}, headers=yonetici)
    assert client.post(f"/siparisler/{s['id']}/iptal", headers=musteri).status_code == 400


def test_musteri_baskasinin_siparisini_goremez(client, yonetici, musteri):
    u = urun_ekle(client, yonetici)
    s = siparis_ver(client, musteri, u["id"], 1).json()
    kayit_ol(client, "Diger", "diger@example.com")
    r = client.post("/giris", data={"username": "diger@example.com", "password": "sifre123"})
    diger = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert client.get(f"/siparisler/{s['id']}", headers=diger).status_code == 404
    assert client.get("/siparisler", headers=diger).json() == []
    assert client.post(f"/siparisler/{s['id']}/iptal", headers=diger).status_code == 404


def test_yonetici_durum_akisi_ve_takip_no(client, yonetici, musteri):
    u = urun_ekle(client, yonetici)
    s = siparis_ver(client, musteri, u["id"], 1).json()
    sid = s["id"]
    # odeme beklerken direkt kargoya verilemez
    assert client.patch(f"/siparisler/{sid}/durum", json={"durum": "kargoya_verildi"}, headers=yonetici).status_code == 400
    assert client.patch(f"/siparisler/{sid}/durum", json={"durum": "odendi"}, headers=yonetici).status_code == 200
    r = client.patch(f"/siparisler/{sid}/durum", json={"durum": "kargoya_verildi", "takip_no": "TK123"}, headers=yonetici)
    assert r.status_code == 200 and r.json()["takip_no"] == "TK123"
    assert client.patch(f"/siparisler/{sid}/durum", json={"durum": "teslim_edildi"}, headers=yonetici).json()["durum"] == "teslim_edildi"
    # teslimden sonra degisemez
    assert client.patch(f"/siparisler/{sid}/durum", json={"durum": "iptal_edildi"}, headers=yonetici).status_code == 400


def test_musteri_durum_guncelleyemez(client, yonetici, musteri):
    u = urun_ekle(client, yonetici)
    s = siparis_ver(client, musteri, u["id"], 1).json()
    assert client.patch(f"/siparisler/{s['id']}/durum", json={"durum": "odendi"}, headers=musteri).status_code == 403


def test_yonetici_tum_siparisleri_filtreleyerek_gorur(client, yonetici, musteri):
    u = urun_ekle(client, yonetici, stok=10)
    a = siparis_ver(client, musteri, u["id"], 1).json()
    siparis_ver(client, musteri, u["id"], 1)
    client.patch(f"/siparisler/{a['id']}/durum", json={"durum": "odendi"}, headers=yonetici)
    assert len(client.get("/siparisler", headers=yonetici).json()) == 2
    odenen = client.get("/siparisler", params={"durum": "odendi"}, headers=yonetici).json()
    assert len(odenen) == 1 and odenen[0]["musteri_ad"] == "Musteri"


# ---------------------------------------------------------------- Yonetim ozeti

def test_yonetim_ozeti(client, yonetici, musteri):
    u = urun_ekle(client, yonetici, fiyat="10.00", stok=3)
    s = siparis_ver(client, musteri, u["id"], 2).json()
    client.patch(f"/siparisler/{s['id']}/durum", json={"durum": "odendi"}, headers=yonetici)
    r = client.get("/yonetim/ozet", headers=yonetici)
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["bugun_siparis_adedi"] == 1
    assert o["bugun_tutar"] == 20.0
    assert o["odenmis_toplam_ciro"] == 20.0
    assert o["durum_sayilari"] == {"odendi": 1}
    assert o["dusuk_stok"][0]["stok"] == 1
    assert client.get("/yonetim/ozet", headers=musteri).status_code == 403
