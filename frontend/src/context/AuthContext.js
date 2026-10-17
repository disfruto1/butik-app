import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [hazir, setHazir] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem('token').then(kayitliToken => {
      if (kayitliToken) setToken(kayitliToken);
      setHazir(true);
    });
  }, []);

  const girisYap = async (yeniToken) => {
    await AsyncStorage.setItem('token', yeniToken);
    setToken(yeniToken);
  };

  const cikisYap = async () => {
    await AsyncStorage.removeItem('token');
    setToken(null);
  };

  if (!hazir) return null;

  return (
    <AuthContext.Provider value={{ token, girisYap, cikisYap }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
