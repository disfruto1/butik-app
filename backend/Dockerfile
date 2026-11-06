FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# Once bagimliliklar: kod degisince paketler yeniden kurulmasin
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --system --no-create-home butik
USER butik

EXPOSE 8000

# Tek worker bilerek: tablolar acilista olusturulur, birden fazla worker ayni anda denerse carpisabilir.
# Vekil basliklarina guvenilecek adres FORWARDED_ALLOW_IPS ile verilir (bkz. deploy/docker-compose.yml).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
