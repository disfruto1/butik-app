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


def sifreyi_dogrula(duz_sifre, hashed_sifre):
    return pwd_context.verify(duz_sifre, hashed_sifre)


def token_olustur(data):
    encode_data = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    encode_data.update({"exp": expire})
    return jwt.encode(encode_data, SECRET_KEY, algorithm=ALGORITHM)


def tokeni_coz(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
