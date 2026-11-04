import React, { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const FavoriContext = createContext(null);

// Favoriler telefonda saklanır (hesaba bağlı değildir). Ürünün kendisi saklandığı için liste çevrimdışı da görünür.
export function FavoriProvider({ children }) {
  const [favoriler, setFavoriler] = useState([]);
  const [yuklendi, setYuklendi] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem('favoriler')
      .then((ham) => {
        if (!ham) return;
        const veri = JSON.parse(ham);
        if (Array.isArray(veri)) setFavoriler(veri.filter((u) => u && u.id != null));
      })
      .catch(() => {})
      .finally(() => setYuklendi(true));
  }, []);

  useEffect(() => {
    if (!yuklendi) return;
    AsyncStorage.setItem('favoriler', JSON.stringify(favoriler)).catch(() => {});
  }, [favoriler, yuklendi]);

  const favoriMi = useCallback((id) => favoriler.some((u) => u.id === id), [favoriler]);

  const favoriDegistir = useCallback((urun) => {
    setFavoriler((onceki) =>
      onceki.some((u) => u.id === urun.id) ? onceki.filter((u) => u.id !== urun.id) : [urun, ...onceki]
    );
  }, []);

  const deger = useMemo(() => ({ favoriler, favoriMi, favoriDegistir }), [favoriler, favoriMi, favoriDegistir]);
  return <FavoriContext.Provider value={deger}>{children}</FavoriContext.Provider>;
}

export function useFavori() {
  return useContext(FavoriContext);
}
