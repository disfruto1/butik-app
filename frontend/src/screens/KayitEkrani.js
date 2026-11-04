import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, KeyboardAvoidingView, Platform } from 'react-native';
import api, { hataMesaji } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { renk } from '../theme';

export default function KayitEkrani() {
  const { girisYap } = useAuth();
  const [ad, setAd] = useState('');
  const [email, setEmail] = useState('');
  const [sifre, setSifre] = useState('');
  const [yukleniyor, setYukleniyor] = useState(false);

  const handleKayit = async () => {
    if (!ad.trim() || !email.trim() || !sifre) {
      Alert.alert('Hata', 'Tüm alanları doldurunuz.');
      return;
    }
    if (sifre.length < 6) {
      Alert.alert('Hata', 'Şifre en az 6 karakter olmalı.');
      return;
    }
    setYukleniyor(true);
    try {
      await api.post('/kayit', { ad: ad.trim(), e_posta: email.trim(), sifre });
    } catch (error) {
      const mesaj = error.response?.status === 422 ? 'Bilgileri kontrol edin (geçerli bir e-posta girin).' : hataMesaji(error, 'Kayıt yapılamadı.');
      Alert.alert('Hata', mesaj);
      setYukleniyor(false);
      return;
    }
    try {
      // Kayıttan sonra otomatik giriş
      const params = new URLSearchParams();
      params.append('username', email.trim());
      params.append('password', sifre);
      const response = await api.post('/giris', params.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      await girisYap(response.data.access_token);
    } catch (error) {
      Alert.alert('Kayıt tamamlandı', 'Hesabınız oluşturuldu, lütfen giriş yapın.');
      setYukleniyor(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Text style={styles.altBaslik}>Yeni hesap oluşturun</Text>
      <TextInput style={styles.input} placeholder="Ad Soyad" value={ad} onChangeText={setAd} />
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
        placeholder="Şifre (en az 6 karakter)"
        value={sifre}
        onChangeText={setSifre}
        secureTextEntry
        onSubmitEditing={handleKayit}
      />
      <TouchableOpacity
        style={[styles.buton, yukleniyor && styles.butonDevre]}
        onPress={handleKayit}
        disabled={yukleniyor}
      >
        <Text style={styles.butonYazi}>{yukleniyor ? 'Kaydediliyor...' : 'Kayıt Ol'}</Text>
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', padding: 24 },
  altBaslik: { fontSize: 18, color: renk.yaziIkincil, marginBottom: 24 },
  input: { alignSelf: 'stretch', borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 12, fontSize: 16, marginBottom: 16 },
  buton: { alignSelf: 'stretch', backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center' },
  butonDevre: { backgroundColor: renk.devre },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
