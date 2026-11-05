"""PayTR iFrame API istemcisi: ayarlar, token isteme ve bildirim imzasi.

Veritabanina dokunmaz. Siparis ve odeme kayitlari main.py'de islenir.
Belgeler: https://dev.paytr.com/iframe-api
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
from dataclasses import dataclass
from decimal import Decimal

import requests

log = logging.getLogger("butik.odeme")

TOKEN_ADRESI = "https://www.paytr.com/odeme/api/get-token"
ODEME_SAYFASI = "https://www.paytr.com/odeme/guvenli/"
# Ayni PayTR magazasi web sitesiyle paylasilirsa bildirimler bu onekle ayirt edilir
SIPARIS_ONEKI = "BUTIK"
ODEME_SURESI_DAKIKA = 30
PARA_BIRIMI = "TL"


class PaytrHatasi(Exception):
    """PayTR token vermedi veya ulasilamadi. Mesaj sadece sunucu kaydi icindir, musteriye gosterilmez."""


@dataclass(frozen=True)
class Ayarlar:
    merchant_id: str
    merchant_key: str
    merchant_salt: str
    donus_adresi: str
    test_modu: bool
    max_taksit: int
    yerel_ip: str


def ayarlar() -> Ayarlar | None:
    """Eksik veya hatali ayarda None doner, kart odemesi kapali sayilir.

    PAYTR_TEST_MODU icin varsayilan yok: yanlislikla gercek tahsilat da, gercek
    siparisin test odemesiyle "odendi" olmasi da ayni derecede kotu.
    """
    merchant_id = os.getenv("PAYTR_MERCHANT_ID", "").strip()
    merchant_key = os.getenv("PAYTR_MERCHANT_KEY", "").strip()
    merchant_salt = os.getenv("PAYTR_MERCHANT_SALT", "").strip()
    donus_adresi = os.getenv("PAYTR_DONUS_ADRESI", "").strip().rstrip("/")
    test_modu = os.getenv("PAYTR_TEST_MODU", "").strip()
    if not (merchant_id and merchant_key and merchant_salt and donus_adresi):
        return None
    if test_modu not in ("0", "1") or not donus_adresi.startswith(("http://", "https://")):
        log.error("PayTR ayarlari gecersiz: PAYTR_TEST_MODU 0 veya 1 olmali, PAYTR_DONUS_ADRESI http(s) ile baslamali")
        return None
    try:
        max_taksit = int(os.getenv("PAYTR_MAX_TAKSIT", "1").strip() or "1")
    except ValueError:
        max_taksit = -1
    if not 0 <= max_taksit <= 12:
        log.error("PayTR ayarlari gecersiz: PAYTR_MAX_TAKSIT 0 ile 12 arasinda olmali")
        return None
    return Ayarlar(
        merchant_id=merchant_id,
        merchant_key=merchant_key,
        merchant_salt=merchant_salt,
        donus_adresi=donus_adresi,
        test_modu=test_modu == "1",
        max_taksit=max_taksit,
        yerel_ip=os.getenv("PAYTR_YEREL_IP", "").strip(),
    )


def siparis_no_uret(siparis_id: int) -> str:
    """PayTR her deneme icin benzersiz ve sadece harf/rakamdan olusan numara ister."""
    return f"{SIPARIS_ONEKI}{siparis_id}T{secrets.token_hex(6)}"


def kurusa_cevir(tutar: Decimal) -> int:
    return int((tutar * 100).to_integral_value())


def sepet_kodla(kalemler: list[tuple[str, Decimal, int]]) -> str:
    satirlar = [[ad, f"{fiyat:.2f}", adet] for ad, fiyat, adet in kalemler]
    return base64.b64encode(json.dumps(satirlar).encode()).decode()


def _imzala(anahtar: str, metin: str) -> str:
    ozet = hmac.new(anahtar.encode(), metin.encode(), hashlib.sha256).digest()
    return base64.b64encode(ozet).decode()


def token_iste(
    a: Ayarlar,
    *,
    merchant_oid: str,
    ip: str,
    e_posta: str,
    tutar_kurus: int,
    sepet: str,
    ad: str,
    adres: str,
    telefon: str,
) -> str:
    """PayTR'dan odeme sayfasi icin token alir, olmazsa PaytrHatasi firlatir."""
    test = "1" if a.test_modu else "0"
    # 1: tek cekim. 0: PayTR'in izin verdigi en yuksek taksit. 2-12: en fazla o kadar taksit.
    taksitsiz = "1" if a.max_taksit == 1 else "0"
    max_taksit = "0" if a.max_taksit == 1 else str(a.max_taksit)
    imza = _imzala(
        a.merchant_key,
        a.merchant_id + ip + merchant_oid + e_posta + str(tutar_kurus) + sepet
        + taksitsiz + max_taksit + PARA_BIRIMI + test + a.merchant_salt,
    )
    try:
        cevap = requests.post(
            TOKEN_ADRESI,
            data={
                "merchant_id": a.merchant_id,
                "user_ip": ip,
                "merchant_oid": merchant_oid,
                "email": e_posta,
                "payment_amount": str(tutar_kurus),
                "paytr_token": imza,
                "user_basket": sepet,
                "debug_on": "1",  # hata nedeni sadece bu sunucuya doner, kayda yazilir
                "no_installment": taksitsiz,
                "max_installment": max_taksit,
                "user_name": ad[:60],
                "user_address": adres[:400],
                "user_phone": telefon,
                "merchant_ok_url": f"{a.donus_adresi}/odeme/paytr/tamam",
                "merchant_fail_url": f"{a.donus_adresi}/odeme/paytr/hata",
                "timeout_limit": str(ODEME_SURESI_DAKIKA),
                "currency": PARA_BIRIMI,
                "test_mode": test,
                "lang": "tr",
            },
            timeout=20,
        )
        icerik = cevap.json()
    except (requests.RequestException, ValueError) as hata:
        raise PaytrHatasi(f"PayTR'a ulasilamadi: {type(hata).__name__}") from hata
    if icerik.get("status") != "success" or not icerik.get("token"):
        raise PaytrHatasi(f"PayTR token vermedi: {icerik.get('reason', 'neden belirtilmedi')}")
    return icerik["token"]


def bildirim_gecerli(a: Ayarlar, merchant_oid: str, durum: str, toplam: str, gelen_imza: str) -> bool:
    beklenen = _imzala(a.merchant_key, merchant_oid + a.merchant_salt + durum + toplam)
    return hmac.compare_digest(beklenen.encode(), gelen_imza.encode())
