import React from 'react';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import GirisEkrani from './src/screens/GirisEkrani';
import UrunlerEkrani from './src/screens/UrunlerEkrani';

function Navigator() {
  const { token } = useAuth();
  return token ? <UrunlerEkrani /> : <GirisEkrani />;
}

export default function App() {
  return (
    <AuthProvider>
      <Navigator />
    </AuthProvider>
  );
}
