import { useEffect, useState } from 'react';

// Değer değişince `gecikme` ms bekler, o sürede yeni değişiklik olmazsa günceller (arama kutusu için).
export default function useDebounce(deger, gecikme = 400) {
  const [sonuc, setSonuc] = useState(deger);
  useEffect(() => {
    const t = setTimeout(() => setSonuc(deger), gecikme);
    return () => clearTimeout(t);
  }, [deger, gecikme]);
  return sonuc;
}
