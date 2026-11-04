import React, { useCallback, useState } from 'react';
import { View, Text, FlatList, StyleSheet, TouchableOpacity, ActivityIndicator, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import api, { hataMesaji } from '../services/api';
import SiparisKarti from '../components/SiparisKarti';
import { renk } from '../theme';

export default function SiparislerimEkrani() {
  const [siparisler, setSiparisler] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [yenileniyor, setYenileniyor] = useState(false);
  const [hata, setHata] = useState(null);

  const yukle = useCallback(async () => {
    try {
      const res = await api.get('/siparisler');
      setSiparisler(res.data);
      setHata(null);
    } catch (err) {
      setHata(hataMesaji(err, 'Siparişler yüklenemedi.'));
    }
  }, []);

  // Ekran her açıldığında listeyi tazele (sipariş verip döndüğünüzde yeni sipariş görünsün)
  useFocusEffect(
    useCallback(() => {
      yukle().finally(() => setYukleniyor(false));
    }, [yukle])
  );

  const yenile = async () => {
    setYenileniyor(true);
    await yukle();
    setYenileniyor(false);
  };

  const iptalEt = (siparis) => {
    Alert.alert('Siparişi iptal et', `#${siparis.id} numaralı siparişi iptal etmek istiyor musunuz?`, [
      { text: 'Vazgeç', style: 'cancel' },
      {
        text: 'İptal et',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.post(`/siparisler/${siparis.id}/iptal`);
            await yukle();
          } catch (err) {
            Alert.alert('Hata', hataMesaji(err, 'Sipariş iptal edilemedi.'));
          }
        },
      },
    ]);
  };

  if (yukleniyor) {
    return (
      <View style={styles.ortala}>
        <ActivityIndicator size="large" color={renk.birincil} />
      </View>
    );
  }

  if (hata && siparisler.length === 0) {
    return (
      <View style={styles.ortala}>
        <Text style={styles.hataYazi}>{hata}</Text>
        <TouchableOpacity style={styles.tekrar} onPress={yenile}>
          <Text style={styles.tekrarYazi}>Tekrar dene</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <FlatList
      style={styles.container}
      contentContainerStyle={styles.liste}
      data={siparisler}
      keyExtractor={(s) => s.id.toString()}
      refreshing={yenileniyor}
      onRefresh={yenile}
      ListEmptyComponent={<Text style={styles.bos}>Henüz siparişiniz yok.</Text>}
      renderItem={({ item }) => (
        <SiparisKarti siparis={item}>
          {item.durum === 'odeme_bekliyor' ? (
            <TouchableOpacity style={styles.iptal} onPress={() => iptalEt(item)}>
              <Text style={styles.iptalYazi}>Siparişi iptal et</Text>
            </TouchableOpacity>
          ) : null}
        </SiparisKarti>
      )}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin },
  liste: { padding: 16 },
  ortala: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, backgroundColor: '#fff' },
  hataYazi: { fontSize: 15, color: renk.yaziIkincil, textAlign: 'center', marginBottom: 16 },
  tekrar: { backgroundColor: renk.birincil, paddingVertical: 12, paddingHorizontal: 24, borderRadius: 8 },
  tekrarYazi: { color: '#fff', fontWeight: 'bold' },
  bos: { textAlign: 'center', color: renk.yaziSoluk, marginTop: 40 },
  iptal: { marginTop: 12, paddingVertical: 10, borderRadius: 8, borderWidth: 1, borderColor: renk.tehlike, alignItems: 'center' },
  iptalYazi: { color: renk.tehlike, fontWeight: 'bold' },
});
