import React, { useState } from 'react';
import {
  View, Text, FlatList, TextInput, TouchableOpacity, StyleSheet, Alert,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import api, { hataMesaji } from '../services/api';
import { useCart, adetSiniri } from '../context/CartContext';
import AdetSecici from '../components/AdetSecici';
import { renk } from '../theme';
import { para } from '../utils/format';

export default function SepetEkrani({ navigation }) {
  const { kalemler, toplamTutar, adetDegistir, sepettenSil, sepetiBosalt } = useCart();
  const [adres, setAdres] = useState('');
  const [yukleniyor, setYukleniyor] = useState(false);

  const siparisiTamamla = async () => {
    if (adres.trim().length < 10) {
      Alert.alert('Eksik bilgi', 'Lütfen teslimat adresinizi eksiksiz yazın.');
      return;
    }
    setYukleniyor(true);
    try {
      await api.post('/siparisler', {
        kargo_adres: adres.trim(),
        kalemler: kalemler.map((k) => ({ urun_id: k.urun.id, adet: k.adet })),
      });
      sepetiBosalt();
      setAdres('');
      let odemeBilgisi = '';
      try {
        const ayar = await api.get('/ayarlar');
        odemeBilgisi = ayar.data.odeme_bilgisi || '';
      } catch (e) {
        // ödeme bilgisi alınamazsa sipariş yine de alınmıştır
      }
      Alert.alert(
        'Siparişiniz alındı',
        (odemeBilgisi ? odemeBilgisi + '\n\n' : '') + 'Siparişlerim ekranından durumu takip edebilirsiniz.'
      );
      navigation.replace('Siparislerim');
    } catch (error) {
      Alert.alert('Sipariş verilemedi', hataMesaji(error, 'Sipariş verilemedi. Bilgileri kontrol edin.'));
    } finally {
      setYukleniyor(false);
    }
  };

  if (kalemler.length === 0) {
    return (
      <View style={styles.bosKutu}>
        <Text style={styles.bosBaslik}>Sepetiniz boş</Text>
        <TouchableOpacity style={styles.buton} onPress={() => navigation.navigate('Urunler')}>
          <Text style={styles.butonYazi}>Alışverişe başla</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <FlatList
        data={kalemler}
        keyExtractor={(k) => k.urun.id.toString()}
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={styles.liste}
        renderItem={({ item }) => (
          <View style={styles.kart}>
            <View style={styles.kartUst}>
              <View style={styles.kartSol}>
                <Text style={styles.urunAd}>{item.urun.ad}</Text>
                <Text style={styles.birimFiyat}>{para(item.urun.fiyat)}</Text>
              </View>
              <Text style={styles.satirToplam}>{para(Number(item.urun.fiyat) * item.adet)}</Text>
            </View>
            <View style={styles.kartAlt}>
              <AdetSecici
                adet={item.adet}
                onAzalt={() => adetDegistir(item.urun.id, item.adet - 1)}
                onArttir={() => adetDegistir(item.urun.id, item.adet + 1)}
                arttirDevre={item.adet >= adetSiniri(item.urun)}
              />
              <TouchableOpacity onPress={() => sepettenSil(item.urun.id)}>
                <Text style={styles.sil}>Kaldır</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
        ListFooterComponent={
          <View style={styles.alt}>
            <Text style={styles.etiket}>Teslimat adresi</Text>
            <TextInput
              style={styles.adresInput}
              placeholder="Mahalle, sokak, bina/daire no, ilçe, il"
              value={adres}
              onChangeText={setAdres}
              multiline
              textAlignVertical="top"
            />
            <View style={styles.toplamSatiri}>
              <Text style={styles.toplamEtiket}>Toplam</Text>
              <Text style={styles.toplam}>{para(toplamTutar)}</Text>
            </View>
            <TouchableOpacity
              style={[styles.buton, yukleniyor && styles.butonDevre]}
              onPress={siparisiTamamla}
              disabled={yukleniyor}
            >
              <Text style={styles.butonYazi}>{yukleniyor ? 'Sipariş veriliyor...' : 'Siparişi Tamamla'}</Text>
            </TouchableOpacity>
            <Text style={styles.not}>Sipariş "ödeme bekleniyor" olarak kaydedilir; ödeme bilgisi sipariş sonrası gösterilir.</Text>
          </View>
        }
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin },
  liste: { padding: 16 },
  bosKutu: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff', padding: 24 },
  bosBaslik: { fontSize: 18, color: renk.yaziIkincil, marginBottom: 20 },
  kart: { backgroundColor: renk.kart, borderRadius: 8, padding: 16, marginBottom: 12 },
  kartUst: { flexDirection: 'row', justifyContent: 'space-between' },
  kartSol: { flex: 1, paddingRight: 12 },
  urunAd: { fontSize: 16, fontWeight: 'bold', color: renk.yazi },
  birimFiyat: { fontSize: 13, color: renk.yaziSoluk, marginTop: 4 },
  satirToplam: { fontSize: 16, fontWeight: 'bold', color: renk.fiyat },
  kartAlt: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 },
  sil: { color: renk.tehlike, fontSize: 14 },
  alt: { marginTop: 8 },
  etiket: { fontSize: 14, color: renk.yaziIkincil, marginBottom: 6 },
  adresInput: { backgroundColor: '#fff', borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 12, fontSize: 15, minHeight: 80, marginBottom: 16 },
  toplamSatiri: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  toplamEtiket: { fontSize: 18, color: renk.yazi },
  toplam: { fontSize: 22, fontWeight: 'bold', color: renk.fiyat },
  buton: { backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center' },
  butonDevre: { backgroundColor: renk.devre },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  not: { fontSize: 12, color: renk.yaziSoluk, textAlign: 'center', marginTop: 12 },
});
