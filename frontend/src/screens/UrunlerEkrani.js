import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, StyleSheet, TouchableOpacity } from 'react-native';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import UrunDetayEkrani from './UrunDetayEkrani';

export default function UrunlerEkrani() {
  const { token, cikisYap } = useAuth();
  const [urunler, setUrunler] = useState([]);
  const [seciliUrun, setSeciliUrun] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(true);

  useEffect(() => {
    axios.get('http://127.0.0.1:8000/urunler', {
      headers: { Authorization: 'Bearer ' + token },
    })
    .then(res => setUrunler(res.data))
    .catch(err => console.log('Hata:', err.message))
    .finally(() => setYukleniyor(false));
  }, []);

  if (seciliUrun) {
    return <UrunDetayEkrani urun={seciliUrun} geriDon={() => setSeciliUrun(null)} />;
  }

  if (yukleniyor) {
    return <View style={styles.container}><Text>Yukleniyor...</Text></View>;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.baslik}>Urunler</Text>
        <TouchableOpacity onPress={cikisYap}>
          <Text style={styles.cikis}>Cikis</Text>
        </TouchableOpacity>
      </View>
      <FlatList
        data={urunler}
        keyExtractor={item => item.id.toString()}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.kart} onPress={() => setSeciliUrun(item)}>
            <View>
              <Text style={styles.urunAd}>{item.ad}</Text>
              <Text style={styles.urunKategori}>Detay icin tikla</Text>
            </View>
            <Text style={styles.urunFiyat}>{item.fiyat} TL</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5', padding: 16, paddingTop: 60 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  baslik: { fontSize: 24, fontWeight: 'bold', color: '#333' },
  cikis: { fontSize: 16, color: '#e74c3c' },
  kart: { backgroundColor: '#fff', padding: 16, borderRadius: 8, marginBottom: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  urunAd: { fontSize: 16, color: '#333', fontWeight: 'bold' },
  urunKategori: { fontSize: 12, color: '#999', marginTop: 4 },
  urunFiyat: { fontSize: 16, fontWeight: 'bold', color: '#27ae60' },
});
