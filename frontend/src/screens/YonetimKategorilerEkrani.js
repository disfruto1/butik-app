import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, TextInput, FlatList, StyleSheet, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import api, { hataMesaji } from '../services/api';
import { renk } from '../theme';

export default function YonetimKategorilerEkrani() {
  const [kategoriler, setKategoriler] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [ad, setAd] = useState('');
  const [duzenlenen, setDuzenlenen] = useState(null); // düzenlenen kategorinin id'si
  const [kaydediliyor, setKaydediliyor] = useState(false);

  const yukle = useCallback(async () => {
    try {
      const res = await api.get('/kategoriler');
      setKategoriler(res.data);
    } catch (err) {
      Alert.alert('Hata', hataMesaji(err, 'Kategoriler yüklenemedi.'));
    } finally {
      setYukleniyor(false);
    }
  }, []);

  useEffect(() => {
    yukle();
  }, [yukle]);

  const kaydet = async () => {
    if (!ad.trim()) return;
    setKaydediliyor(true);
    try {
      if (duzenlenen) {
        await api.put(`/kategoriler/${duzenlenen}`, { ad: ad.trim() });
      } else {
        await api.post('/kategoriler', { ad: ad.trim() });
      }
      setAd('');
      setDuzenlenen(null);
      await yukle();
    } catch (err) {
      Alert.alert('Hata', hataMesaji(err, 'Kategori kaydedilemedi.'));
    } finally {
      setKaydediliyor(false);
    }
  };

  const sil = (k) => {
    Alert.alert('Kategoriyi kaldır', `"${k.ad}" kategorisi listeden kalkacak. İçindeki ürünler silinmez.`, [
      { text: 'Vazgeç', style: 'cancel' },
      {
        text: 'Kaldır',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.delete(`/kategoriler/${k.id}`);
            if (duzenlenen === k.id) {
              setDuzenlenen(null);
              setAd('');
            }
            await yukle();
          } catch (err) {
            Alert.alert('Hata', hataMesaji(err, 'Kategori kaldırılamadı.'));
          }
        },
      },
    ]);
  };

  const duzenlemeyeBasla = (k) => {
    setDuzenlenen(k.id);
    setAd(k.ad);
  };

  const vazgec = () => {
    setDuzenlenen(null);
    setAd('');
  };

  if (yukleniyor) {
    return (
      <View style={styles.ortala}>
        <ActivityIndicator size="large" color={renk.birincil} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.form}>
        <TextInput
          style={styles.input}
          value={ad}
          onChangeText={setAd}
          placeholder={duzenlenen ? 'Yeni ad' : 'Yeni kategori adı'}
          onSubmitEditing={kaydet}
        />
        <TouchableOpacity style={[styles.buton, kaydediliyor && { opacity: 0.5 }]} onPress={kaydet} disabled={kaydediliyor}>
          <Text style={styles.butonYazi}>{duzenlenen ? 'Güncelle' : 'Ekle'}</Text>
        </TouchableOpacity>
      </View>
      {duzenlenen ? (
        <TouchableOpacity onPress={vazgec} style={styles.vazgec}>
          <Text style={styles.vazgecYazi}>Düzenlemeden vazgeç</Text>
        </TouchableOpacity>
      ) : null}

      <FlatList
        data={kategoriler}
        keyExtractor={(k) => k.id.toString()}
        contentContainerStyle={styles.liste}
        ListEmptyComponent={<Text style={styles.bos}>Henüz kategori yok.</Text>}
        renderItem={({ item }) => (
          <View style={styles.satir}>
            <Text style={styles.ad}>{item.ad}</Text>
            <TouchableOpacity onPress={() => duzenlemeyeBasla(item)} style={styles.islem}>
              <Text style={styles.duzenle}>Düzenle</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => sil(item)} style={styles.islem}>
              <Text style={styles.sil}>Kaldır</Text>
            </TouchableOpacity>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin },
  ortala: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  form: { flexDirection: 'row', padding: 16, paddingBottom: 8 },
  input: { flex: 1, backgroundColor: '#fff', borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 10, fontSize: 16, marginRight: 8 },
  buton: { backgroundColor: renk.birincil, paddingHorizontal: 18, borderRadius: 8, justifyContent: 'center' },
  butonYazi: { color: '#fff', fontWeight: 'bold' },
  vazgec: { paddingHorizontal: 16, paddingBottom: 8 },
  vazgecYazi: { color: renk.baglanti },
  liste: { padding: 16, paddingTop: 8 },
  bos: { textAlign: 'center', color: renk.yaziSoluk, marginTop: 40 },
  satir: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 8, padding: 14, marginBottom: 10 },
  ad: { flex: 1, fontSize: 16, color: renk.yazi },
  islem: { paddingHorizontal: 8 },
  duzenle: { color: renk.baglanti },
  sil: { color: renk.tehlike },
});
