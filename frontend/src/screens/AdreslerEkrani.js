import React, { useCallback, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import api, { hataMesaji } from '../services/api';
import { renk } from '../theme';

export default function AdreslerEkrani({ navigation }) {
  const insets = useSafeAreaInsets();
  const [adresler, setAdresler] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);

  const yukle = useCallback(async () => {
    try {
      const res = await api.get('/adresler');
      setAdresler(res.data);
      setHata(null);
    } catch (err) {
      setHata(hataMesaji(err, 'Adresler yüklenemedi.'));
    } finally {
      setYukleniyor(false);
    }
  }, []);

  // Formdan dönüldüğünde liste güncel olsun
  useFocusEffect(
    useCallback(() => {
      yukle();
    }, [yukle])
  );

  const varsayilanYap = async (adres) => {
    try {
      await api.post(`/adresler/${adres.id}/varsayilan`);
      await yukle();
    } catch (err) {
      Alert.alert('İşlem yapılamadı', hataMesaji(err, 'Varsayılan adres değiştirilemedi.'));
    }
  };

  const sil = (adres) => {
    Alert.alert('Adres silinsin mi?', `"${adres.baslik}" silinecek. Geçmiş siparişleriniz etkilenmez.`, [
      { text: 'Vazgeç', style: 'cancel' },
      {
        text: 'Sil',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.delete(`/adresler/${adres.id}`);
            await yukle();
          } catch (err) {
            Alert.alert('Silinemedi', hataMesaji(err, 'Adres silinemedi.'));
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

  if (hata && adresler.length === 0) {
    return (
      <View style={styles.ortala}>
        <Text style={styles.bos}>{hata}</Text>
        <TouchableOpacity
          style={styles.buton}
          onPress={() => {
            setYukleniyor(true);
            yukle();
          }}
        >
          <Text style={styles.butonYazi}>Tekrar dene</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <FlatList
      style={styles.container}
      contentContainerStyle={[styles.liste, { paddingBottom: insets.bottom + 16 }]}
      data={adresler}
      keyExtractor={(a) => a.id.toString()}
      ListEmptyComponent={<Text style={styles.bos}>Henüz kayıtlı adresiniz yok.</Text>}
      renderItem={({ item }) => (
        <View style={styles.kart}>
          <View style={styles.kartUst}>
            <Text style={styles.baslik}>{item.baslik}</Text>
            {item.varsayilan ? <Text style={styles.rozet}>Varsayılan</Text> : null}
          </View>
          <Text style={styles.adres}>{item.adres}</Text>
          <View style={styles.eylemler}>
            <TouchableOpacity style={styles.eylem} onPress={() => navigation.navigate('AdresForm', { adres: item })}>
              <Text style={styles.baglanti}>Düzenle</Text>
            </TouchableOpacity>
            {!item.varsayilan ? (
              <TouchableOpacity style={styles.eylem} onPress={() => varsayilanYap(item)}>
                <Text style={styles.baglanti}>Varsayılan yap</Text>
              </TouchableOpacity>
            ) : null}
            <TouchableOpacity style={styles.eylem} onPress={() => sil(item)}>
              <Text style={styles.sil}>Sil</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
      ListFooterComponent={
        <TouchableOpacity style={styles.buton} onPress={() => navigation.navigate('AdresForm')}>
          <Text style={styles.butonYazi}>Yeni Adres Ekle</Text>
        </TouchableOpacity>
      }
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin },
  liste: { padding: 16 },
  ortala: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, backgroundColor: renk.zemin },
  bos: { textAlign: 'center', color: renk.yaziSoluk, marginVertical: 24 },
  kart: { backgroundColor: renk.kart, borderRadius: 8, padding: 16, marginBottom: 12 },
  kartUst: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  baslik: { flex: 1, fontSize: 16, fontWeight: 'bold', color: renk.yazi, paddingRight: 8 },
  rozet: { fontSize: 12, fontWeight: 'bold', color: renk.fiyat },
  adres: { fontSize: 14, color: renk.yaziIkincil, lineHeight: 20 },
  eylemler: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 4 },
  eylem: { paddingVertical: 10, marginRight: 20 },
  baglanti: { fontSize: 14, color: renk.baglanti },
  sil: { fontSize: 14, color: renk.tehlike },
  buton: { backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center', marginTop: 4 },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
