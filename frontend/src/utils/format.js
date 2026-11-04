export function para(deger) {
  const n = Number(deger);
  if (Number.isNaN(n)) return String(deger) + ' TL';
  return n.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' TL';
}

export function tarih(deger) {
  const d = new Date(deger);
  if (Number.isNaN(d.getTime())) return '';
  return (
    d.toLocaleDateString('tr-TR', { day: '2-digit', month: 'long', year: 'numeric' }) +
    ' ' +
    d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })
  );
}

export const DURUM_ETIKET = {
  odeme_bekliyor: 'Ödeme bekleniyor',
  odendi: 'Ödendi',
  kargoya_verildi: 'Kargoya verildi',
  teslim_edildi: 'Teslim edildi',
  iptal_edildi: 'İptal edildi',
};

// Backend'deki (models.SiparisDurum.GECISLER) geçiş tablosuyla aynı olmalı.
export const DURUM_GECISLERI = {
  odeme_bekliyor: ['odendi', 'iptal_edildi'],
  odendi: ['kargoya_verildi', 'iptal_edildi'],
  kargoya_verildi: ['teslim_edildi'],
  teslim_edildi: [],
  iptal_edildi: [],
};

export const DURUM_BUTON = {
  odendi: 'Ödendi olarak işaretle',
  kargoya_verildi: 'Kargoya ver',
  teslim_edildi: 'Teslim edildi',
  iptal_edildi: 'İptal et',
};

// "12,50" ve "12.50" yazımlarını kabul eder. Geçersizse null döner.
export function sayiOku(metin) {
  if (metin == null) return null;
  const temiz = String(metin).trim().replace(',', '.');
  if (temiz === '') return null;
  const n = Number(temiz);
  return Number.isFinite(n) ? n : null;
}
