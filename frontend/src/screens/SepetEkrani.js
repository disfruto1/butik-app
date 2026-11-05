import React, { useCallback, useState } from 'react';
import {
  View, Text, FlatList, TextInput, TouchableOpacity, StyleSheet, Alert,
  KeyboardAvoidingView, Platform, Switch,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import api, { hataMesaji } from '../services/api';
import { useCart, adetSiniri } from '../context/CartContext';
import AdetSecici from '../components/AdetSecici';
import { renk } from '../theme';
import { para } from '../utils/format';

export default function SepetEkrani({ navigation }) {
  const { kalemler, toplamTutar, adetDegistir, sepettenSil, sepetiBosalt } = useCart();
  const [adres, setAdres] = useState('');
  const [yukleniyor, setYukleniyor] = useState(false);
  const [adresler, setAdresler] = useState([]);
  const [secilenId, setSecilenId] = useState(null);
  const [elleYaz, setElleYaz] = useState(false); // "Başka bir adres yaz" seçildi; liste yenilense de korunur
  const [adresiKaydet, setAdresiKaydet] = useState(true);

  // Adreslerim ekranından dönüldüğünde de güncel olsun
  useFocusEffect(
    useCallback(() => {
      let iptal = false;
      api
        .get('/adresler')
        .then((res) => {
          if (iptal) return;
          setAdresler(res.data);
          // Seçim silinmişse (ya da henüz seçim yoksa) varsayılana dön; liste varsayılanla başlar
          setSecilenId((onceki) => (res.data.some((a) => a.id === onceki) ? onceki : res.data[0]?.id ?? null));
        })
        .catch(() => {
          // Liste alınamazsa elle adres yazılarak sipariş verilebilir
        });
      return () => {
        iptal = true;
      };
    }, [])
  );

  // Seçili kayıtlı adres yoksa (kayıtlı adres hiç yoksa da) elle yazılan adres kullanılır
  const secilenAdres = elleYaz ? undefined : adresler.find((a) => a.id === secilenId);

  const siparisiTamamla = async () => {
    const kargoAdres = secilenAdres ? secilenAdres.adres : adres.trim();
    if (kargoAdres.length < 10) {
      Alert.alert('Eksik bilgi', 'Lütfen teslimat adresinizi eksiksiz yazın.');
      return;
    }
    setYukleniyor(true);
    try {
      const { data: siparis } = await api.post('/siparisler', {
        kargo_adres: kargoAdres,
        kalemler: kalemler.map((k) => ({ urun_id: k.urun.id, adet: k.adet })),
      });
      sepetiBosalt();
      setAdres('');
      if (!secilenAdres && adresiKaydet) {
        try {
          await api.post('/adresler', { baslik: `Adres ${adresler.length + 1}`, adres: kargoAdres });
        } catch (e) {
          // adres kaydedilemese de sipariş alınmıştır
        }
      }
      let odemeBilgisi = '';
      let kartOdeme = false;
      try {
        const ayar = await api.get('/ayarlar');
        odemeBilgisi = ayar.data.odeme_bilgisi || '';
        kartOdeme = !!ayar.data.kart_odeme;
      } catch (e) {
        // ödeme bilgisi alınamazsa sipariş yine de alınmıştır
      }
      if (kartOdeme) {
        navigation.replace('Odeme', { siparisId: siparis.id, tutar: siparis.toplam_tutar, odemeBilgisi });
        return;
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
        keyboardDismissMode="on-drag"
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
            <View style={styles.adresBaslikSatiri}>
              <Text style={styles.etiket}>Teslimat adresi</Text>
              {adresler.length > 0 ? (
                <TouchableOpacity onPress={() => navigation.navigate('Adresler')}>
                  <Text style={styles.adresYonet}>Adreslerim</Text>
                </TouchableOpacity>
              ) : null}
            </View>
            {adresler.map((a) => (
              <AdresSecenegi
                key={a.id}
                baslik={a.baslik}
                aciklama={a.adres}
                secili={a.id === secilenAdres?.id}
                onPress={() => {
                  setSecilenId(a.id);
                  setElleYaz(false);
                }}
              />
            ))}
            {adresler.length > 0 ? (
              <AdresSecenegi baslik="Başka bir adres yaz" secili={!secilenAdres} onPress={() => setElleYaz(true)} />
            ) : null}
            {!secilenAdres ? (
              <>
                <TextInput
                  style={styles.adresInput}
                  placeholder="Mahalle, sokak, bina/daire no, ilçe, il"
                  value={adres}
                  onChangeText={setAdres}
                  maxLength={500}
                  multiline
                  textAlignVertical="top"
                />
                <View style={styles.kaydetSatiri}>
                  <Text style={styles.kaydetYazi}>Bu adresi adreslerime kaydet</Text>
                  <Switch
                    value={adresiKaydet}
                    onValueChange={setAdresiKaydet}
                    accessibilityLabel="Bu adresi adreslerime kaydet"
                  />
                </View>
              </>
            ) : null}
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

function AdresSecenegi({ baslik, aciklama, secili, onPress }) {
  return (
    <TouchableOpacity
      style={[styles.secenek, secili && styles.secenekSecili]}
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ selected: secili }}
    >
      <View style={[styles.radyo, secili && styles.radyoSecili]}>
        {secili ? <View style={styles.radyoIc} /> : null}
      </View>
      <View style={styles.secenekYazilar}>
        <Text style={styles.secenekBaslik}>{baslik}</Text>
        {aciklama ? <Text style={styles.secenekAciklama}>{aciklama}</Text> : null}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  adresBaslikSatiri: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  adresYonet: { fontSize: 14, color: renk.baglanti, marginBottom: 6, paddingLeft: 12 },
  secenek: { flexDirection: 'row', alignItems: 'flex-start', backgroundColor: '#fff', borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 12, marginBottom: 8 },
  secenekSecili: { borderColor: renk.birincil },
  radyo: { width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: renk.yaziSoluk, alignItems: 'center', justifyContent: 'center', marginRight: 10, marginTop: 1 },
  radyoSecili: { borderColor: renk.birincil },
  radyoIc: { width: 10, height: 10, borderRadius: 5, backgroundColor: renk.birincil },
  secenekYazilar: { flex: 1 },
  secenekBaslik: { fontSize: 15, fontWeight: 'bold', color: renk.yazi },
  secenekAciklama: { fontSize: 13, color: renk.yaziIkincil, marginTop: 2, lineHeight: 18 },
  kaydetSatiri: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  kaydetYazi: { fontSize: 14, color: renk.yazi, flex: 1, paddingRight: 12 },
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
