import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

export default function UrunDetayEkrani({ urun, geriDon }) {
  const { token } = useAuth();
  const [yukleniyor, setYukleniyor] = useState(false);

  const siparisVer = async () => {
    setYukleniyor(true);
    try {
      await axios.post('http://127.0.0.1:8000/siparisler',
        { kalemler: [{ urun_id: urun.id, adet: 1 }] },
        { headers: { Authorization: 'Bearer ' + token } }
      );
      Alert.alert('Basarili', urun.ad + ' siparis verildi!');
      geriDon();
    } catch (error) {
      Alert.alert('Hata', 'Siparis verilemedi.');
    } finally {
      setYukleniyor(false);
    }
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity onPress={geriDon} style={styles.geri}>
        <Text style={styles.geriYazi}>Geri</Text>
      </TouchableOpacity>
      <Text style={styles.ad}>{urun.ad}</Text>
      <Text style={styles.fiyat}>{urun.fiyat} TL</Text>
      <Text style={styles.aciklama}>{urun.aciklama}</Text>
      <TouchableOpacity
        style={[styles.buton, yukleniyor && styles.butonDevre]}
        onPress={siparisVer}
        disabled={yukleniyor}
      >
        <Text style={styles.butonYazi}>{yukleniyor ? 'Siparis veriliyor...' : 'Siparis Ver'}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', padding: 24, paddingTop: 60 },
  geri: { marginBottom: 24 },
  geriYazi: { fontSize: 16, color: '#3498db' },
  ad: { fontSize: 28, fontWeight: 'bold', color: '#333', marginBottom: 8 },
  fiyat: { fontSize: 22, color: '#27ae60', fontWeight: 'bold', marginBottom: 16 },
  aciklama: { fontSize: 16, color: '#666', marginBottom: 32 },
  buton: { backgroundColor: '#333', padding: 16, borderRadius: 8, alignItems: 'center' },
  butonDevre: { backgroundColor: '#999' },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
