import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, ScrollView, Image } from 'react-native';
import api from '../services/api';
import { useCart, adetSiniri } from '../context/CartContext';
import { useFavori } from '../context/FavoriContext';
import AdetSecici from '../components/AdetSecici';
import { renk } from '../theme';
import { para } from '../utils/format';

export default function UrunDetayEkrani({ route, navigation }) {
  const [urun, setUrun] = useState(route.params.urun);
  const { sepeteEkle } = useCart();
  const { favoriMi, favoriDegistir } = useFavori();
  const [adet, setAdet] = useState(1);

  // Listeden gelen bilgi eski olabilir (stok/fiyat), güncelini çek
  useEffect(() => {
    let iptal = false;
    api
      .get('/urunler/' + route.params.urun.id)
      .then((res) => {
        if (!iptal) setUrun(res.data);
      })
      .catch(() => {});
    return () => {
      iptal = true;
    };
  }, [route.params.urun.id]);

  useEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <TouchableOpacity onPress={() => favoriDegistir(urun)} style={{ paddingHorizontal: 16 }} accessibilityLabel="Favori">
          <Text style={{ fontSize: 26, color: favoriMi(urun.id) ? renk.tehlike : renk.yaziSoluk }}>
            {favoriMi(urun.id) ? '♥' : '♡'}
          </Text>
        </TouchableOpacity>
      ),
    });
  }, [navigation, urun, favoriMi, favoriDegistir]);

  const tukendi = urun.stok === 0;
  const sinir = adetSiniri(urun);
  const adetGecerli = Math.min(adet, Math.max(sinir, 1));

  const handleSepeteEkle = () => {
    sepeteEkle(urun, adetGecerli);
    Alert.alert('Sepete eklendi', `${adetGecerli} adet ${urun.ad} sepetinizde.`, [
      { text: 'Alışverişe devam', onPress: () => navigation.goBack() },
      { text: 'Sepete git', onPress: () => navigation.replace('Sepet') },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.icerik}>
      {urun.gorsel_url ? <Image source={{ uri: urun.gorsel_url }} style={styles.gorsel} resizeMode="cover" /> : null}
      <Text style={styles.ad}>{urun.ad}</Text>
      <Text style={styles.fiyat}>{para(urun.fiyat)}</Text>
      {urun.aciklama ? <Text style={styles.aciklama}>{urun.aciklama}</Text> : null}

      {tukendi ? (
        <Text style={styles.tukendi}>Bu ürün şu an tükendi.</Text>
      ) : (
        <>
          <View style={styles.adetSatiri}>
            <Text style={styles.adetEtiket}>Adet</Text>
            <AdetSecici
              adet={adetGecerli}
              onAzalt={() => setAdet((a) => Math.max(1, a - 1))}
              onArttir={() => setAdet((a) => Math.min(sinir, a + 1))}
              azaltDevre={adetGecerli <= 1}
              arttirDevre={adetGecerli >= sinir}
            />
          </View>
          {urun.stok != null && urun.stok <= 5 ? (
            <Text style={styles.stokUyari}>Stokta son {urun.stok} adet kaldı.</Text>
          ) : null}
          <TouchableOpacity style={styles.buton} onPress={handleSepeteEkle}>
            <Text style={styles.butonYazi}>Sepete Ekle · {para(Number(urun.fiyat) * adetGecerli)}</Text>
          </TouchableOpacity>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  icerik: { padding: 24 },
  gorsel: { width: '100%', height: 260, borderRadius: 12, backgroundColor: '#eee', marginBottom: 20 },
  ad: { fontSize: 28, fontWeight: 'bold', color: renk.yazi, marginBottom: 8 },
  fiyat: { fontSize: 22, color: renk.fiyat, fontWeight: 'bold', marginBottom: 16 },
  aciklama: { fontSize: 16, color: renk.yaziIkincil, marginBottom: 24, lineHeight: 22 },
  adetSatiri: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  adetEtiket: { fontSize: 16, color: renk.yazi },
  stokUyari: { color: '#e67e22', marginBottom: 12 },
  tukendi: { color: renk.tehlike, fontSize: 16, fontWeight: 'bold', marginTop: 8 },
  buton: { backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center', marginTop: 12 },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
