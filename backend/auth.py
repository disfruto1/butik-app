import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "buraya-uzun-ve-gizli-bir-anahtar-yaz":
    raise RuntimeError(
        "SECRET_KEY tanimli degil. backend/.env dosyasina uzun ve rastgele bir anahtar yazin "
        "(uretmek icin: python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
    )
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))


def sifreyi_hashle(sifre):
    return pwd_context.hash(sifre)


# Kullanici bulunamasa da ayni sure harcansin: yanit suresinden kayitli e-postalar anlasilmasin
_SAHTE_HASH = pwd_context.hash("kullanici-yokken-karsilastirilan-deger")


def giris_sifresini_dogrula(duz_sifre, hashed_sifre):
    """hashed_sifre None ise (kullanici yok) yine hash hesaplar ve False doner."""
    if len(duz_sifre.encode()) > 72:  # bcrypt en fazla 72 bayt isler, kayitta da bu sinir var
        return False
    dogru = pwd_context.verify(duz_sifre, hashed_sifre or _SAHTE_HASH)
    return dogru and hashed_sifre is not None


def token_olustur(data):
    encode_data = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    encode_data.update({"exp": expire})
    return jwt.encode(encode_data, SECRET_KEY, algorithm=ALGORITHM)


def tokeni_coz(token):
    """(e_posta, token_surumu) dondurur, gecersizse (None, 0). Eski tokenlarda surum yoktur, 0 sayilir."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub"), payload.get("tv", 0)
    except JWTError:
        return None, 0
