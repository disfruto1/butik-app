"""Uyelikte gosterilen yasal metinler ve onay kaydi.

Metin degisince surum kendiliginden degisir (metnin ozeti). Her onay kaydi bu surumu saklar;
o tarihte hangi metnin gosterildigi git gecmisinden bulunup ozetle dogrulanabilir.
Ayrintilar ve hukuki kontrol notu: ROADMAP.md, "Bilinen riskler".
"""
import hashlib

from models import KullaniciOnayi

AYDINLATMA = """Veri sorumlusu: Aysu Küçük (Yula Moda), Zekibey Mahallesi, 13 Nisan Caddesi, No: 133/1, Ayvalık / Balıkesir. E-posta: destek@yulamoda.com

Ad, iletişim, adres, sipariş, ödeme ve IP bilgileriniz; üyelik, sipariş, ödeme ve teslimat işlemleri, hesap güvenliği ve yasal yükümlülüklerimiz için işlenir. Bu bilgiler uygulama üzerinden elektronik ortamda toplanır. Hukuki sebepler: sözleşmenin kurulması ve ifası, hukuki yükümlülük ve meşru menfaat (KVKK m. 5/2). Kampanya iletileri yalnızca ayrıca izin verirseniz gönderilir.

Bilgileriniz yalnızca bu amaçlarla ödeme kuruluşuna (PayTR), kargo firmasına (Aras Kargo), barındırma ve ileti gönderim hizmeti aldığımız firmalara, şifre sıfırlama için yurt dışındaki e-posta altyapısı sağlayıcımıza ve talep halinde yetkili kurumlara aktarılır. Kart bilgileriniz tarafımızca saklanmaz.

KVKK m. 11 uyarınca verileriniz hakkında bilgi isteme, düzeltme ve silinmesini isteme, itiraz etme ve zararın giderilmesini isteme haklarına sahipsiniz. Başvurularınızı yukarıdaki adreslere iletebilirsiniz."""

EPOSTA_IZNI = "Yula Moda'nın kampanya ve duyurularını e-posta ile almak istiyorum."
SMS_IZNI = "Yula Moda'nın kampanya ve duyurularını SMS ile almak istiyorum."
IZIN_NOTU = "İzniniz isteğe bağlıdır, istediğiniz zaman ücretsiz olarak geri alabilirsiniz."

SURUM = hashlib.sha256("\n".join((AYDINLATMA, EPOSTA_IZNI, SMS_IZNI, IZIN_NOTU)).encode()).hexdigest()[:16]

TUR_AYDINLATMA = "aydinlatma"
TUR_EPOSTA_IZNI = "eposta_izni"
TUR_SMS_IZNI = "sms_izni"


def kayit_onaylarini_olustur(kullanici_id: int, e_posta: str, telefon: str | None, eposta_izni: bool, sms_izni: bool, ip: str) -> list[KullaniciOnayi]:
    """Isaretlenmeyen izin icin kayit olusmaz: izin yoksa gonderim de yoktur."""

    def kayit(tur: str, adres: str | None) -> KullaniciOnayi:
        return KullaniciOnayi(kullanici_id=kullanici_id, tur=tur, verildi=True, metin_surumu=SURUM, iletisim_adresi=adres, ip=ip)

    kayitlar = [kayit(TUR_AYDINLATMA, None)]
    if eposta_izni:
        kayitlar.append(kayit(TUR_EPOSTA_IZNI, e_posta))
    if sms_izni:
        kayitlar.append(kayit(TUR_SMS_IZNI, telefon))
    return kayitlar
