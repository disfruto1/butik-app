import React from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { StatusBar } from 'expo-status-bar';

import { AuthProvider, useAuth } from './src/context/AuthContext';
import { CartProvider } from './src/context/CartContext';
import { FavoriProvider } from './src/context/FavoriContext';
import GirisEkrani from './src/screens/GirisEkrani';
import KayitEkrani from './src/screens/KayitEkrani';
import SifreSifirlamaEkrani from './src/screens/SifreSifirlamaEkrani';
import UrunlerEkrani from './src/screens/UrunlerEkrani';
import UrunDetayEkrani from './src/screens/UrunDetayEkrani';
import FavorilerEkrani from './src/screens/FavorilerEkrani';
import SepetEkrani from './src/screens/SepetEkrani';
import SiparislerimEkrani from './src/screens/SiparislerimEkrani';
import AdreslerEkrani from './src/screens/AdreslerEkrani';
import AdresFormEkrani from './src/screens/AdresFormEkrani';
import YonetimEkrani from './src/screens/YonetimEkrani';
import YonetimSiparislerEkrani from './src/screens/YonetimSiparislerEkrani';
import YonetimUrunlerEkrani from './src/screens/YonetimUrunlerEkrani';
import UrunFormEkrani from './src/screens/UrunFormEkrani';
import YonetimKategorilerEkrani from './src/screens/YonetimKategorilerEkrani';

const AuthStack = createStackNavigator();
const AppStack = createStackNavigator();

const ortakSecenekler = { headerTintColor: '#333', headerBackTitle: 'Geri' };

function GirisAkisi() {
  return (
    <AuthStack.Navigator screenOptions={ortakSecenekler}>
      <AuthStack.Screen name="Giris" component={GirisEkrani} options={{ headerShown: false }} />
      <AuthStack.Screen name="Kayit" component={KayitEkrani} options={{ title: 'Kayıt Ol' }} />
      <AuthStack.Screen name="SifreSifirlama" component={SifreSifirlamaEkrani} options={{ title: 'Şifremi Unuttum' }} />
    </AuthStack.Navigator>
  );
}

function UygulamaAkisi() {
  const { yonetici } = useAuth();
  return (
    <AppStack.Navigator screenOptions={ortakSecenekler}>
      <AppStack.Screen name="Urunler" component={UrunlerEkrani} options={{ headerShown: false }} />
      <AppStack.Screen name="UrunDetay" component={UrunDetayEkrani} options={{ title: 'Ürün' }} />
      <AppStack.Screen name="Favoriler" component={FavorilerEkrani} options={{ title: 'Favorilerim' }} />
      <AppStack.Screen name="Sepet" component={SepetEkrani} options={{ title: 'Sepetim' }} />
      <AppStack.Screen name="Siparislerim" component={SiparislerimEkrani} options={{ title: 'Siparişlerim' }} />
      <AppStack.Screen name="Adresler" component={AdreslerEkrani} options={{ title: 'Adreslerim' }} />
      <AppStack.Screen name="AdresForm" component={AdresFormEkrani} options={{ title: 'Adres' }} />
      {/* Yönetim ekranları sadece yönetici rolü için kayıtlı. Asıl yetki kontrolü backend'de yapılır. */}
      {yonetici ? (
        <>
          <AppStack.Screen name="Yonetim" component={YonetimEkrani} options={{ title: 'Yönetim' }} />
          <AppStack.Screen name="YonetimSiparisler" component={YonetimSiparislerEkrani} options={{ title: 'Siparişler' }} />
          <AppStack.Screen name="YonetimUrunler" component={YonetimUrunlerEkrani} options={{ title: 'Ürünler' }} />
          <AppStack.Screen name="UrunForm" component={UrunFormEkrani} options={{ title: 'Ürün' }} />
          <AppStack.Screen name="YonetimKategoriler" component={YonetimKategorilerEkrani} options={{ title: 'Kategoriler' }} />
        </>
      ) : null}
    </AppStack.Navigator>
  );
}

function Navigator() {
  const { token } = useAuth();
  // Sepet ve favoriler yalnızca giriş yapılmışken yaşar; çıkışta sıfırlanır.
  return token ? (
    <CartProvider>
      <FavoriProvider>
        <UygulamaAkisi />
      </FavoriProvider>
    </CartProvider>
  ) : (
    <GirisAkisi />
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <AuthProvider>
          <NavigationContainer>
            <StatusBar style="dark" />
            <Navigator />
          </NavigationContainer>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
