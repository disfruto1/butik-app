import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api, { authDurumu } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [kullanici, setKullanici] = useState(null); // /ben yanıtı (rol dahil)
  const [hazir, setHazir] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem('token')
      .then((kayitliToken) => {
        if (kayitliToken) {
          authDurumu.token = kayitliToken; // state'ten önce, ilk istek token'lı gitsin
          setToken(kayitliToken);
        }
      })
      .finally(() => setHazir(true));
  }, []);

  // Token değişince kullanıcı bilgisini (özellikle rolü) çek
  useEffect(() => {
    if (!token) {
      setKullanici(null);
      return;
    }
    let iptal = false;
    api
      .get('/ben')
      .then((res) => {
        if (!iptal) setKullanici(res.data);
      })
      .catch(() => {});
    return () => {
      iptal = true;
    };
  }, [token]);

  const girisYap = useCallback(async (yeniToken) => {
    authDurumu.token = yeniToken;
    await AsyncStorage.setItem('token', yeniToken);
    setToken(yeniToken);
  }, []);

  const cikisYap = useCallback(async () => {
    authDurumu.token = null;
    // Ortak telefonda bir sonraki kullanıcı önceki kişinin sepetini/favorilerini görmesin
    await AsyncStorage.multiRemove(['token', 'sepet', 'favoriler']);
    setToken(null);
  }, []);

  // Süresi dolmuş / geçersiz token: otomatik çıkış
  authDurumu.oturumDustu = cikisYap;

  if (!hazir) return null;

  const yonetici = kullanici?.rol === 'yonetici';

  return (
    <AuthContext.Provider value={{ token, kullanici, yonetici, girisYap, cikisYap }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
