import React, { useCallback, useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator, RefreshControl } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import api, { hataMesaji } from '../services/api';
import { renk } from '../theme';
import { para, DURUM_ETIKET } from '../utils/format';

export default function YonetimEkrani({ navigation }) {
  const [ozet, setOzet] = useState(null);
  const [hata, setHata] = useState(null);
  const [yenileniyor, setYenileniyor] = useState(false);

  const yukle = useCallback(async () => {
    try {
      const res = await api.get('/yonetim/ozet');
      setOzet(res.data);
      setHata(null);
    } catch (err) {
      setHata(hataMesaji(err, 'Özet yüklenemedi.'));
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      yukle();
    }, [yukle])
  );

  const yenile = async () => {
    setYenileniyor(true);
    await yukle();
    setYenileniyor(false);
  };

  const bekleyen = ozet?.durum_sayilari?.odeme_bekliyor || 0;
  const odenen = ozet?.durum_sayilari?.odendi || 0;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.icerik}
      refreshControl={<RefreshControl refreshing={yenileniyor} onRefresh={yenile} />}
    >
      <View style={styles.menu}>
        <MenuButon yazi="Siparişler" onPress={() => navigation.navigate('YonetimSiparisler')} />
        <MenuButon yazi="Ürünler" onPress={() => navigation.navigate('YonetimUrunler')} />
        <MenuButon yazi="Kategoriler" onPress={() => navigation.navigate('YonetimKategoriler')} />
      </View>

      {hata ? <Text style={styles.hata}>{hata}</Text> : null}
      {!ozet && !hata ? <ActivityIndicator style={{ marginTop: 32 }} color={renk.birincil} /> : null}

      {ozet ? (
        <>
          <View style={styles.kutular}>
            <Kutu etiket="Bugün sipariş" deger={String(ozet.bugun_siparis_adedi)} />
            <Kutu etiket="Bugünkü tutar" deger={para(ozet.bugun_tutar)} />
          </View>
          <View style={styles.kutular}>
            <Kutu etiket="Ödenmiş toplam ciro" deger={para(ozet.odenmis_toplam_ciro)} />
            <Kutu
              etiket="İşlem bekleyen"
              deger={`${bekleyen + odenen}`}
              alt={`${bekleyen} ödeme, ${odenen} kargo bekliyor`}
              onPress={() => navigation.navigate('YonetimSiparisler')}
            />
          </View>

          <Text style={styles.altBaslik}>Siparişler (duruma göre)</Text>
          <View style={styles.kart}>
            {Object.keys(DURUM_ETIKET).map((d) => (
              <View key={d} style={styles.satir}>
                <Text style={styles.satirYazi}>{DURUM_ETIKET[d]}</Text>
                <Text style={styles.satirDeger}>{ozet.durum_sayilari[d] || 0}</Text>
              </View>
            ))}
          </View>

          <Text style={styles.altBaslik}>Stoğu azalan ürünler (5 ve altı)</Text>
          <View style={styles.kart}>
            {ozet.dusuk_stok.length === 0 ? (
              <Text style={styles.bos}>Stoğu azalan ürün yok.</Text>
            ) : (
              ozet.dusuk_stok.map((u) => (
                <View key={u.id} style={styles.satir}>
                  <Text style={styles.satirYazi}>{u.ad}</Text>
                  <Text style={[styles.satirDeger, u.stok === 0 && { color: renk.tehlike }]}>
                    {u.stok === 0 ? 'Tükendi' : u.stok}
                  </Text>
                </View>
              ))
            )}
          </View>
        </>
      ) : null}
    </ScrollView>
  );
}

function MenuButon({ yazi, onPress }) {
  return (
    <TouchableOpacity style={styles.menuButon} onPress={onPress}>
      <Text style={styles.menuYazi}>{yazi}</Text>
    </TouchableOpacity>
  );
}

function Kutu({ etiket, deger, alt, onPress }) {
  const Kap = onPress ? TouchableOpacity : View;
  return (
    <Kap style={styles.kutu} onPress={onPress}>
      <Text style={styles.kutuEtiket}>{etiket}</Text>
      <Text style={styles.kutuDeger}>{deger}</Text>
      {alt ? <Text style={styles.kutuAlt}>{alt}</Text> : null}
    </Kap>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin },
  icerik: { padding: 16 },
  menu: { flexDirection: 'row', marginBottom: 16 },
  menuButon: { flex: 1, backgroundColor: renk.birincil, paddingVertical: 12, borderRadius: 8, alignItems: 'center', marginRight: 8 },
  menuYazi: { color: '#fff', fontWeight: 'bold' },
  hata: { color: renk.tehlike, textAlign: 'center', marginVertical: 16 },
  kutular: { flexDirection: 'row', marginBottom: 8 },
  kutu: { flex: 1, backgroundColor: renk.kart, borderRadius: 8, padding: 14, marginRight: 8 },
  kutuEtiket: { fontSize: 12, color: renk.yaziSoluk },
  kutuDeger: { fontSize: 20, fontWeight: 'bold', color: renk.yazi, marginTop: 4 },
  kutuAlt: { fontSize: 11, color: renk.yaziSoluk, marginTop: 2 },
  altBaslik: { fontSize: 16, fontWeight: 'bold', color: renk.yazi, marginTop: 16, marginBottom: 8 },
  kart: { backgroundColor: renk.kart, borderRadius: 8, padding: 14 },
  satir: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  satirYazi: { color: renk.yaziIkincil, fontSize: 15, flex: 1, paddingRight: 8 },
  satirDeger: { color: renk.yazi, fontWeight: 'bold', fontSize: 15 },
  bos: { color: renk.yaziSoluk },
});
