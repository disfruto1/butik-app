import React, { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const CartContext = createContext(null);

const EN_COK = 99;

function adetSiniri(urun) {
  return urun.stok == null ? EN_COK : Math.min(urun.stok, EN_COK);
}

// Sepet telefonda saklanır (uygulama kapanınca kaybolmaz), çıkış yapılınca silinir.
// Sipariş verilirken fiyat ve stok her zaman sunucudan doğrulanır.
export function CartProvider({ children }) {
  const [kalemler, setKalemler] = useState([]); // [{ urun, adet }]
  const [yuklendi, setYuklendi] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem('sepet')
      .then((ham) => {
        if (!ham) return;
        const veri = JSON.parse(ham);
        if (Array.isArray(veri)) setKalemler(veri.filter((k) => k && k.urun && k.adet > 0));
      })
      .catch(() => {})
      .finally(() => setYuklendi(true));
  }, []);

  useEffect(() => {
    if (!yuklendi) return; // yükleme bitmeden boş sepetle üzerine yazma
    AsyncStorage.setItem('sepet', JSON.stringify(kalemler)).catch(() => {});
  }, [kalemler, yuklendi]);

  const sepeteEkle = useCallback((urun, adet = 1) => {
    setKalemler((onceki) => {
      const sinir = adetSiniri(urun);
      const mevcut = onceki.find((k) => k.urun.id === urun.id);
      if (mevcut) {
        return onceki.map((k) =>
          k.urun.id === urun.id ? { urun, adet: Math.min(k.adet + adet, sinir) } : k
        );
      }
      return [...onceki, { urun, adet: Math.min(adet, sinir) }];
    });
  }, []);

  const adetDegistir = useCallback((urunId, yeniAdet) => {
    setKalemler((onceki) =>
      onceki
        .map((k) => (k.urun.id === urunId ? { ...k, adet: Math.min(yeniAdet, adetSiniri(k.urun)) } : k))
        .filter((k) => k.adet > 0)
    );
  }, []);

  const sepettenSil = useCallback((urunId) => {
    setKalemler((onceki) => onceki.filter((k) => k.urun.id !== urunId));
  }, []);

  const sepetiBosalt = useCallback(() => setKalemler([]), []);

  const toplamTutar = useMemo(
    () => kalemler.reduce((t, k) => t + Number(k.urun.fiyat) * k.adet, 0),
    [kalemler]
  );
  const toplamAdet = useMemo(() => kalemler.reduce((t, k) => t + k.adet, 0), [kalemler]);

  const deger = useMemo(
    () => ({ kalemler, toplamTutar, toplamAdet, sepeteEkle, adetDegistir, sepettenSil, sepetiBosalt }),
    [kalemler, toplamTutar, toplamAdet, sepeteEkle, adetDegistir, sepettenSil, sepetiBosalt]
  );

  return <CartContext.Provider value={deger}>{children}</CartContext.Provider>;
}

export function useCart() {
  return useContext(CartContext);
}

export { adetSiniri };
