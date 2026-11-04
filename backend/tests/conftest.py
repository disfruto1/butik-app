"""Testler gercek PostgreSQL'e dokunmaz: gecici bir SQLite dosyasi kullanir."""
import os
import sys
import tempfile
from pathlib import Path

_gecici = Path(tempfile.mkdtemp()) / "test_butik.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_gecici}"
os.environ["SECRET_KEY"] = "test-icin-uretilmis-uzun-bir-anahtar-0123456789"
os.environ.pop("ALLOWED_ORIGINS", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import models
from auth import sifreyi_hashle
from database import SessionLocal, engine
from main import app


@pytest.fixture(autouse=True)
def temiz_veritabani():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def _kullanici_ac(e_posta, rol):
    db = SessionLocal()
    try:
        db.add(models.Kullanici(ad=rol.title(), e_posta=e_posta, sifre_hash=sifreyi_hashle("sifre123"), rol=rol))
        db.commit()
    finally:
        db.close()


def _giris(client, e_posta):
    r = client.post("/giris", data={"username": e_posta, "password": "sifre123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture()
def yonetici(client):
    _kullanici_ac("yonetici@example.com", models.KullaniciRol.YONETICI)
    return _giris(client, "yonetici@example.com")


@pytest.fixture()
def musteri(client):
    _kullanici_ac("musteri@example.com", models.KullaniciRol.MUSTERI)
    return _giris(client, "musteri@example.com")
