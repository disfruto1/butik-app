import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import api, { hataMesaji } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { renk } from '../theme';

function girisHataMesaji(error) {
  const durum = error.response?.status;
  if (durum === 401) return 'E-posta veya şifre yanlış.';
  if (durum === 429) {
    const saniye = Number(error.response.headers?.['retry-after']);
    const sure = saniye > 0 ? `${Math.ceil(saniye / 60)} dakika sonra` : 'daha sonra';
    return `Çok fazla başarısız deneme yapıldı. Lütfen ${sure} tekrar deneyin.`;
  }
  if (error.response) return 'Giriş yapılamadı. Lütfen biraz sonra tekrar deneyin.';
  return hataMesaji(error); // sunucuya ulaşılamadı
}

export default function GirisEkrani({ navigation }) {
  const { girisYap } = useAuth();
  const [email, setEmail] = useState('');
  const [sifre, setSifre] = useState('');
  const [yukleniyor, setYukleniyor] = useState(false);

  const handleGiris = async () => {
    if (!email.trim() || !sifre) {
      Alert.alert('Hata', 'E-posta ve şifre giriniz.');
      return;
    }
    setYukleniyor(true);
    try {
      const params = new URLSearchParams();
      params.append('username', email.trim());
      params.append('password', sifre);
      const response = await api.post('/giris', params.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      await girisYap(response.data.access_token);
    } catch (error) {
      Alert.alert('Hata', girisHataMesaji(error));
      setYukleniyor(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Text style={styles.baslik}>Butik App</Text>
      <Text style={styles.altBaslik}>Giriş yapın</Text>
      <TextInput
        style={styles.input}
        placeholder="E-posta"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="email-address"
      />
      <TextInput
        style={styles.input}
        placeholder="Şifre"
        value={sifre}
        onChangeText={setSifre}
        secureTextEntry
        onSubmitEditing={handleGiris}
      />
      <TouchableOpacity
        style={[styles.buton, yukleniyor && styles.butonDevre]}
        onPress={handleGiris}
        disabled={yukleniyor}
      >
        <Text style={styles.butonYazi}>{yukleniyor ? 'Giriş yapılıyor...' : 'Giriş Yap'}</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.baglanti} onPress={() => navigation.navigate('Kayit')}>
        <Text style={styles.baglantiYazi}>Hesabınız yok mu? Kayıt olun</Text>
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', padding: 24 },
  baslik: { fontSize: 32, fontWeight: 'bold', color: renk.yazi, marginBottom: 8 },
  altBaslik: { fontSize: 16, color: renk.yaziSoluk, marginBottom: 32 },
  input: { alignSelf: 'stretch', borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 12, fontSize: 16, marginBottom: 16 },
  buton: { alignSelf: 'stretch', backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center' },
  butonDevre: { backgroundColor: renk.devre },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  baglanti: { marginTop: 20, padding: 8 },
  baglantiYazi: { color: renk.baglanti, fontSize: 15 },
});
