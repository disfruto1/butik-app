import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

export default function GirisEkrani() {
  const { girisYap } = useAuth();
  const [email, setEmail] = useState('');
  const [sifre, setSifre] = useState('');
  const [yukleniyor, setYukleniyor] = useState(false);

  const handleGiris = async () => {
    if (!email || !sifre) { Alert.alert('Hata', 'Email ve sifre giriniz.'); return; }
    setYukleniyor(true);
    try {
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', sifre);
      const response = await axios.post('http://127.0.0.1:8000/giris', params.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      girisYap(response.data.access_token, null);
    } catch (error) {
      Alert.alert('Hata', 'Email veya sifre yanlis.');
    } finally {
      setYukleniyor(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.baslik}>Butik App</Text>
      <Text style={styles.altBaslik}>Giris yapin</Text>
      <TextInput style={styles.input} placeholder='Email' value={email} onChangeText={setEmail} autoCapitalize='none' />
      <TextInput style={styles.input} placeholder='Sifre' value={sifre} onChangeText={setSifre} secureTextEntry={true} />
      <TouchableOpacity style={[styles.buton, yukleniyor && styles.butonDevre]} onPress={handleGiris} disabled={yukleniyor}>
        <Text style={styles.butonYazi}>{yukleniyor ? 'Giris yapiliyor...' : 'Giris Yap'}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center', padding: 24 },
  baslik: { fontSize: 32, fontWeight: 'bold', color: '#333', marginBottom: 8 },
  altBaslik: { fontSize: 16, color: '#999', marginBottom: 32 },
  input: { alignSelf: 'stretch', borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, fontSize: 16, marginBottom: 16 },
  buton: { alignSelf: 'stretch', backgroundColor: '#333', padding: 16, borderRadius: 8, alignItems: 'center' },
  butonDevre: { backgroundColor: '#999' },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
