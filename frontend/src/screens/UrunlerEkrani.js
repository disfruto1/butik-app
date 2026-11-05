import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, TouchableOpacity, ActivityIndicator, TextInput, ScrollView,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import api, { hataMesaji } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useFavori } from '../context/FavoriContext';
import UrunKarti from '../components/UrunKarti';
import useDebounce from '../hooks/useDebounce';
import { renk } from '../theme';

const SAYFA = 20;

export default function UrunlerEkrani({ navigation }) {
  const { cikisYap, yonetici } = useAuth();
  const { toplamAdet } = useCart();
  const { favoriMi, favoriDegistir, favoriler } = useFavori();
  const insets = useSafeAreaInsets();

  const [urunler, setUrunler] = useState([]);
  const [kategoriler, setKategoriler] = useState([]);
  const [arama, setArama] = useState('');
  const [kategoriId, setKategoriId] = useState(null);
  const aranan = useDebounce(arama.trim(), 400);

  const [yukleniyor, setYukleniyor] = useState(true);
  const [yenileniyor, setYenileniyor] = useState(false);
  const [dahaVar, setDahaVar] = useState(true);
  const [dahaYukleniyor, setDahaYukleniyor] = useState(false);
  const [hata, setHata] = useState(null);
  const istekNo = useRef(0); // eski (geç gelen) yanıtlar yeni aramayı ezmesin

  useEffect(() => {
    api.get('/kategoriler').then((r) => setKategoriler(r.data)).catch(() => {});
  }, []);

  const getir = useCallback(
    async (offset) => {
      const params = { limit: SAYFA, offset };
      if (aranan) params.q = aranan;
      if (kategoriId) params.kategori_id = kategoriId;
      const res = await api.get('/urunler', { params });
      return res.data;
    },
    [aranan, kategoriId]
  );

  const ilkYukle = useCallback(
    async (yenilemeMi = false) => {
      const no = ++istekNo.current;
      if (!yenilemeMi) setYukleniyor(true);
      try {
        const veri = await getir(0);
        if (no !== istekNo.current) return;
        setUrunler(veri);
        setDahaVar(veri.length === SAYFA);
        setHata(null);
      } catch (err) {
        if (no !== istekNo.current) return;
        setHata(hataMesaji(err, 'Ürünler yüklenemedi.'));
      } finally {
        if (no === istekNo.current) setYukleniyor(false);
      }
    },
    [getir]
  );

  useEffect(() => {
    ilkYukle();
  }, [ilkYukle]);

  const yenile = async () => {
    setYenileniyor(true);
    await ilkYukle(true);
    setYenileniyor(false);
  };

  const dahaYukle = async () => {
    if (!dahaVar || dahaYukleniyor || yukleniyor || hata) return;
    const no = istekNo.current;
    setDahaYukleniyor(true);
    try {
      const veri = await getir(urunler.length);
      if (no !== istekNo.current) return;
      setUrunler((onceki) => {
        const var_ = new Set(onceki.map((u) => u.id));
        return [...onceki, ...veri.filter((u) => !var_.has(u.id))];
      });
      setDahaVar(veri.length === SAYFA);
    } catch (err) {
      // sessizce geç; kullanıcı kaydırıp tekrar deneyebilir
    } finally {
      setDahaYukleniyor(false);
    }
  };

  const filtreAktif = !!aranan || !!kategoriId;

  return (
    <View style={[styles.container, { paddingTop: insets.top + 12 }]}>
      <View style={styles.baslikSatiri}>
        <Text style={styles.baslik}>Ürünler</Text>
        <TouchableOpacity onPress={cikisYap}>
          <Text style={styles.cikis}>Çıkış</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.menu}>
        <TouchableOpacity onPress={() => navigation.navigate('Favoriler')} style={styles.menuButon}>
          <Text style={styles.menuYazi}>Favoriler{favoriler.length > 0 ? ` (${favoriler.length})` : ''}</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.navigate('Siparislerim')} style={styles.menuButon}>
          <Text style={styles.menuYazi}>Siparişlerim</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.navigate('Sepet')} style={styles.menuButon}>
          <Text style={styles.menuYazi}>Sepet{toplamAdet > 0 ? ` (${toplamAdet})` : ''}</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.navigate('Adresler')} style={styles.menuButon}>
          <Text style={styles.menuYazi}>Adreslerim</Text>
        </TouchableOpacity>
        {yonetici ? (
          <TouchableOpacity onPress={() => navigation.navigate('Yonetim')} style={styles.menuButon}>
            <Text style={[styles.menuYazi, styles.yonetimYazi]}>Yönetim</Text>
          </TouchableOpacity>
        ) : null}
      </View>

      <TextInput
        style={styles.arama}
        placeholder="Ürün ara..."
        value={arama}
        onChangeText={setArama}
        autoCorrect={false}
        returnKeyType="search"
        clearButtonMode="while-editing"
      />

      {kategoriler.length > 0 ? (
        <View style={styles.kategoriSatiri}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <Chip yazi="Tümü" secili={kategoriId === null} onPress={() => setKategoriId(null)} />
            {kategoriler.map((k) => (
              <Chip key={k.id} yazi={k.ad} secili={kategoriId === k.id} onPress={() => setKategoriId(k.id)} />
            ))}
          </ScrollView>
        </View>
      ) : null}

      {yukleniyor ? (
        <View style={styles.ortala}>
          <ActivityIndicator size="large" color={renk.birincil} />
        </View>
      ) : hata && urunler.length === 0 ? (
        <View style={styles.ortala}>
          <Text style={styles.hataYazi}>{hata}</Text>
          <TouchableOpacity style={styles.tekrar} onPress={() => ilkYukle()}>
            <Text style={styles.tekrarYazi}>Tekrar dene</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={urunler}
          keyExtractor={(item) => item.id.toString()}
          refreshing={yenileniyor}
          onRefresh={yenile}
          onEndReached={dahaYukle}
          onEndReachedThreshold={0.4}
          keyboardShouldPersistTaps="handled"
          ListEmptyComponent={
            <Text style={styles.bos}>{filtreAktif ? 'Aramanıza uygun ürün bulunamadı.' : 'Henüz ürün yok.'}</Text>
          }
          ListFooterComponent={dahaYukleniyor ? <ActivityIndicator style={{ margin: 16 }} color={renk.birincil} /> : null}
          contentContainerStyle={{ paddingBottom: insets.bottom + 16 }}
          renderItem={({ item }) => (
            <UrunKarti
              urun={item}
              onPress={() => navigation.navigate('UrunDetay', { urun: item })}
              favori={favoriMi(item.id)}
              onFavori={() => favoriDegistir(item)}
            />
          )}
        />
      )}
    </View>
  );
}

function Chip({ yazi, secili, onPress }) {
  return (
    <TouchableOpacity style={[styles.chip, secili && styles.chipSecili]} onPress={onPress}>
      <Text style={[styles.chipYazi, secili && styles.chipYaziSecili]}>{yazi}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin, paddingHorizontal: 16 },
  baslikSatiri: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  baslik: { fontSize: 24, fontWeight: 'bold', color: renk.yazi },
  cikis: { fontSize: 15, color: renk.tehlike },
  menu: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 4, marginBottom: 8 },
  menuButon: { paddingVertical: 6, marginRight: 16 },
  menuYazi: { fontSize: 15, color: renk.baglanti },
  yonetimYazi: { fontWeight: 'bold', color: '#8e44ad' },
  arama: { backgroundColor: '#fff', borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 10, fontSize: 16, marginBottom: 10 },
  kategoriSatiri: { marginBottom: 10 },
  chip: { paddingVertical: 6, paddingHorizontal: 14, borderRadius: 16, borderWidth: 1, borderColor: renk.cizgi, backgroundColor: '#fff', marginRight: 8 },
  chipSecili: { backgroundColor: renk.birincil, borderColor: renk.birincil },
  chipYazi: { color: renk.yazi, fontSize: 14 },
  chipYaziSecili: { color: '#fff' },
  ortala: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  hataYazi: { fontSize: 15, color: renk.yaziIkincil, textAlign: 'center', marginBottom: 16 },
  tekrar: { backgroundColor: renk.birincil, paddingVertical: 12, paddingHorizontal: 24, borderRadius: 8 },
  tekrarYazi: { color: '#fff', fontWeight: 'bold' },
  bos: { textAlign: 'center', color: renk.yaziSoluk, marginTop: 40 },
});
