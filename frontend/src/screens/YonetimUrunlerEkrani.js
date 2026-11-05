import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, FlatList, StyleSheet, TouchableOpacity, ActivityIndicator, TextInput } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import api, { hataMesaji } from '../services/api';
import UrunKarti from '../components/UrunKarti';
import useDebounce from '../hooks/useDebounce';
import { renk } from '../theme';

const SAYFA = 50;

export default function YonetimUrunlerEkrani({ navigation }) {
  const [urunler, setUrunler] = useState([]);
  const [arama, setArama] = useState('');
  const aranan = useDebounce(arama.trim(), 400);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [yenileniyor, setYenileniyor] = useState(false);
  const [dahaVar, setDahaVar] = useState(true);
  const [hata, setHata] = useState(null);
  const istekNo = useRef(0);

  const getir = useCallback(
    async (offset) => {
      const params = { limit: SAYFA, offset };
      if (aranan) params.q = aranan;
      const res = await api.get('/yonetim/urunler', { params });
      return res.data;
    },
    [aranan]
  );

  const ilkYukle = useCallback(async () => {
    const no = ++istekNo.current;
    try {
      const veri = await getir(0);
      if (no !== istekNo.current) return;
      setUrunler(veri);
      setDahaVar(veri.length === SAYFA);
      setHata(null);
    } catch (err) {
      if (no === istekNo.current) setHata(hataMesaji(err, 'Ürünler yüklenemedi.'));
    } finally {
      if (no === istekNo.current) setYukleniyor(false);
    }
  }, [getir]);

  // Ekrana her dönüşte (form kaydedildikten sonra) ve arama değişince yeniden yükle
  useFocusEffect(
    useCallback(() => {
      ilkYukle();
    }, [ilkYukle])
  );

  useEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <TouchableOpacity onPress={() => navigation.navigate('UrunForm')} style={{ paddingHorizontal: 16 }}>
          <Text style={{ color: renk.baglanti, fontSize: 16, fontWeight: 'bold' }}>+ Yeni</Text>
        </TouchableOpacity>
      ),
    });
  }, [navigation]);

  const yenile = async () => {
    setYenileniyor(true);
    await ilkYukle();
    setYenileniyor(false);
  };

  const dahaYukle = async () => {
    if (!dahaVar || yukleniyor || hata) return;
    const no = istekNo.current;
    try {
      const veri = await getir(urunler.length);
      if (no !== istekNo.current) return;
      setUrunler((onceki) => {
        const var_ = new Set(onceki.map((u) => u.id));
        return [...onceki, ...veri.filter((u) => !var_.has(u.id))];
      });
      setDahaVar(veri.length === SAYFA);
    } catch (err) {
      // sessizce geç
    }
  };

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.arama}
        placeholder="Ürün ara..."
        value={arama}
        onChangeText={setArama}
        autoCorrect={false}
        clearButtonMode="while-editing"
      />
      {yukleniyor ? (
        <View style={styles.ortala}>
          <ActivityIndicator size="large" color={renk.birincil} />
        </View>
      ) : hata && urunler.length === 0 ? (
        <View style={styles.ortala}>
          <Text style={styles.hata}>{hata}</Text>
        </View>
      ) : (
        <FlatList
          data={urunler}
          keyExtractor={(u) => u.id.toString()}
          refreshing={yenileniyor}
          onRefresh={yenile}
          onEndReached={dahaYukle}
          onEndReachedThreshold={0.4}
          contentContainerStyle={styles.liste}
          keyboardShouldPersistTaps="handled"
          ListEmptyComponent={<Text style={styles.bos}>Ürün yok. Sağ üstten "+ Yeni" ile ekleyin.</Text>}
          renderItem={({ item }) => (
            <UrunKarti
              urun={item}
              etiket={item.aktif ? null : 'Pasif (müşteriler görmez)'}
              onPress={() => navigation.navigate('UrunForm', { urun: item })}
            />
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin },
  arama: { backgroundColor: '#fff', borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 10, fontSize: 16, margin: 16, marginBottom: 4 },
  liste: { padding: 16 },
  ortala: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  hata: { color: renk.tehlike, textAlign: 'center' },
  bos: { textAlign: 'center', color: renk.yaziSoluk, marginTop: 40 },
});
