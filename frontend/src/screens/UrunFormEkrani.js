import React, { useEffect, useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ScrollView, Switch, ActivityIndicator,
} from 'react-native';
import api, { hataMesaji } from '../services/api';
import { renk } from '../theme';
import { sayiOku } from '../utils/format';

export default function UrunFormEkrani({ route, navigation }) {
  const mevcut = route.params?.urun || null;
  const [ad, setAd] = useState(mevcut?.ad || '');
  const [aciklama, setAciklama] = useState(mevcut?.aciklama || '');
  const [fiyat, setFiyat] = useState(mevcut ? String(mevcut.fiyat) : '');
  const [stok, setStok] = useState(mevcut?.stok != null ? String(mevcut.stok) : '');
  const [gorsel, setGorsel] = useState(mevcut?.gorsel_url || '');
  const [kategoriId, setKategoriId] = useState(mevcut?.kategori_id ?? null);
  const [aktif, setAktif] = useState(mevcut ? mevcut.aktif : true);
  const [kategoriler, setKategoriler] = useState([]);
  const [kaydediliyor, setKaydediliyor] = useState(false);

  useEffect(() => {
    navigation.setOptions({ title: mevcut ? 'Ürünü düzenle' : 'Yeni ürün' });
    api.get('/kategoriler').then((r) => setKategoriler(r.data)).catch(() => {});
  }, [navigation, mevcut]);

  const kaydet = async () => {
    const fiyatSayi = sayiOku(fiyat);
    const stokSayi = stok.trim() === '' ? null : sayiOku(stok);
    if (!ad.trim()) return Alert.alert('Eksik bilgi', 'Ürün adı gerekli.');
    if (fiyatSayi == null || fiyatSayi < 0) return Alert.alert('Hatalı fiyat', 'Geçerli bir fiyat girin (örn. 199,90).');
    if (stok.trim() !== '' && (stokSayi == null || stokSayi < 0 || !Number.isInteger(stokSayi))) {
      return Alert.alert('Hatalı stok', 'Stok 0 veya daha büyük bir tam sayı olmalı. Stok takibi istemiyorsanız boş bırakın.');
    }
    if (gorsel.trim() && !/^https?:\/\//i.test(gorsel.trim())) {
      return Alert.alert('Hatalı görsel adresi', 'Görsel adresi http:// veya https:// ile başlamalı.');
    }

    const govde = {
      ad: ad.trim(),
      aciklama: aciklama.trim() || null,
      fiyat: fiyatSayi,
      stok: stokSayi,
      gorsel_url: gorsel.trim() || null,
      kategori_id: kategoriId,
    };

    setKaydediliyor(true);
    try {
      if (mevcut) {
        await api.put(`/urunler/${mevcut.id}`, govde);
        if (aktif !== mevcut.aktif) await api.patch(`/urunler/${mevcut.id}/aktif`, { aktif });
      } else {
        await api.post('/urunler', govde);
      }
      navigation.goBack();
    } catch (err) {
      const mesaj = err.response?.status === 422 ? 'Bilgileri kontrol edin.' : hataMesaji(err, 'Ürün kaydedilemedi.');
      Alert.alert('Hata', mesaj);
      setKaydediliyor(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.icerik} keyboardShouldPersistTaps="handled">
      <Etiket yazi="Ürün adı *" />
      <TextInput style={styles.input} value={ad} onChangeText={setAd} placeholder="Örn. Keten Gömlek" />

      <Etiket yazi="Açıklama" />
      <TextInput
        style={[styles.input, styles.cokSatir]}
        value={aciklama}
        onChangeText={setAciklama}
        multiline
        textAlignVertical="top"
        placeholder="Kumaş, beden, bakım bilgisi..."
      />

      <Etiket yazi="Fiyat (TL) *" />
      <TextInput style={styles.input} value={fiyat} onChangeText={setFiyat} keyboardType="decimal-pad" placeholder="199,90" />

      <Etiket yazi="Stok (boş bırakırsanız takip edilmez)" />
      <TextInput style={styles.input} value={stok} onChangeText={setStok} keyboardType="number-pad" placeholder="Örn. 10" />

      <Etiket yazi="Görsel adresi (https://...)" />
      <TextInput
        style={styles.input}
        value={gorsel}
        onChangeText={setGorsel}
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        placeholder="https://..."
      />

      <Etiket yazi="Kategori" />
      <View style={styles.chipler}>
        <Chip yazi="Yok" secili={kategoriId === null} onPress={() => setKategoriId(null)} />
        {kategoriler.map((k) => (
          <Chip key={k.id} yazi={k.ad} secili={kategoriId === k.id} onPress={() => setKategoriId(k.id)} />
        ))}
      </View>

      {mevcut ? (
        <View style={styles.aktifSatiri}>
          <View style={{ flex: 1, paddingRight: 12 }}>
            <Text style={styles.aktifBaslik}>Müşterilere göster</Text>
            <Text style={styles.aktifAlt}>Kapatırsanız ürün listeden kalkar (silinmez, tekrar açabilirsiniz).</Text>
          </View>
          <Switch value={aktif} onValueChange={setAktif} />
        </View>
      ) : null}

      <TouchableOpacity style={[styles.buton, kaydediliyor && styles.butonDevre]} onPress={kaydet} disabled={kaydediliyor}>
        {kaydediliyor ? <ActivityIndicator color="#fff" /> : <Text style={styles.butonYazi}>{mevcut ? 'Kaydet' : 'Ürünü Ekle'}</Text>}
      </TouchableOpacity>
    </ScrollView>
  );
}

function Etiket({ yazi }) {
  return <Text style={styles.etiket}>{yazi}</Text>;
}

function Chip({ yazi, secili, onPress }) {
  return (
    <TouchableOpacity style={[styles.chip, secili && styles.chipSecili]} onPress={onPress}>
      <Text style={[styles.chipYazi, secili && { color: '#fff' }]}>{yazi}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  icerik: { padding: 20, paddingBottom: 48 },
  etiket: { fontSize: 14, color: renk.yaziIkincil, marginBottom: 6, marginTop: 14 },
  input: { borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 12, fontSize: 16 },
  cokSatir: { minHeight: 90 },
  chipler: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: { paddingVertical: 6, paddingHorizontal: 14, borderRadius: 16, borderWidth: 1, borderColor: renk.cizgi, marginRight: 8, marginBottom: 8 },
  chipSecili: { backgroundColor: renk.birincil, borderColor: renk.birincil },
  chipYazi: { color: renk.yazi, fontSize: 14 },
  aktifSatiri: { flexDirection: 'row', alignItems: 'center', marginTop: 20, padding: 14, backgroundColor: renk.zemin, borderRadius: 8 },
  aktifBaslik: { fontSize: 15, color: renk.yazi, fontWeight: 'bold' },
  aktifAlt: { fontSize: 12, color: renk.yaziSoluk, marginTop: 2 },
  buton: { backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center', marginTop: 28 },
  butonDevre: { backgroundColor: renk.devre },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
