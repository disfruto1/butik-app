"""E-posta gonderimi (SMTP). Servise bagli degildir: Resend, Brevo vb. SMTP veren her servisle calisir.

Ayarlar .env'den okunur (bkz. .env.example). SMTP_HOST bos ise e-posta gonderilmez.
Gelistirmede kodu gormek icin EPOSTA_KONSOLA_YAZ=1 yapilabilir; yayinda ACILMAMALI.
"""
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger("butik.eposta")


def gonder(alici: str, konu: str, metin: str) -> bool:
    """Basariliysa True doner. Hata firlatmaz: cagiran hesabin var olup olmadigi sizmasin diye sonuca gore davranmaz."""
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        if os.getenv("EPOSTA_KONSOLA_YAZ") == "1":
            print(f"[eposta] kime={alici} konu={konu}\n{metin}", flush=True)
            return True
        log.warning("E-posta gonderilmedi: SMTP_HOST tanimli degil.")
        return False

    mesaj = EmailMessage()
    mesaj["From"] = os.getenv("SMTP_GONDEREN", "").strip() or os.getenv("SMTP_KULLANICI", "").strip()
    mesaj["To"] = alici
    mesaj["Subject"] = konu
    mesaj.set_content(metin)

    port = int(os.getenv("SMTP_PORT", "587"))
    kullanici = os.getenv("SMTP_KULLANICI", "").strip()
    sifre = os.getenv("SMTP_SIFRE", "")
    baglam = ssl.create_default_context()
    try:
        if port == 465:
            sunucu = smtplib.SMTP_SSL(host, port, timeout=15, context=baglam)
        else:
            sunucu = smtplib.SMTP(host, port, timeout=15)
        with sunucu:
            if port != 465:
                sunucu.starttls(context=baglam)
            if kullanici:
                sunucu.login(kullanici, sifre)
            sunucu.send_message(mesaj)
        return True
    except (smtplib.SMTPException, OSError) as hata:
        # Icerik (kod) ve alici loga yazilmaz
        log.error("E-posta gonderilemedi: %s", type(hata).__name__)
        return False
