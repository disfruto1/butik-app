import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Alert,
  KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { WebView } from 'react-native-webview';
import api, { hataMesaji, sinirMesaji } from '../services/api';
import { renk } from '../theme';
import { para } from '../utils/format';

const TAMAM_ADRESI = '/odeme/paytr/tamam';
const HATA_ADRESI = '/odeme/paytr/hata';
const SORGU_ARALIGI = 3000;
const BEKLEME_SINIRI = 60000;
const ODENMIS = ['odendi', 'kargoya_verildi', 'teslim_edildi'];

export default function OdemeEkrani({ route, navigation }) {
  const { siparisId, tutar, odemeBilgisi } = route.params;
  // form -> odeme (PayTR sayfası) -> onay (bildirim bekleniyor) -> gecikti
  const [asama, setAsama] = useState('form');
  const [telefon, setTelefon] = useState('');
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState(null);
  const [odeme, setOdeme] = useState(null);
  const telefonDegisti = useRef(false);

  useEffect(() => {
    api
      .get('/ben')
      .then((res) => {
        if (!telefonDegisti.current && res.data.telefon) setTelefon(res.data.telefon);
      })
      .catch(() => {
        // Kayıtlı telefon alınamazsa müşteri elle yazar
      });
  }, []);

  const siparislereGit = () => navigation.replace('Siparislerim');

  // Ödeme sonucu yönlendirmeden değil, sunucudan okunur: sonucu kesinleştiren tek şey PayTR bildirimidir.
  useEffect(() => {
    if (!odeme || (asama !== 'odeme' && asama !== 'onay')) return undefined;
    let bitti = false;
    const baslangic = Date.now();
    const sorgula = async () => {
      if (asama === 'onay' && Date.now() - baslangic > BEKLEME_SINIRI) {
        setAsama('gecikti');
        return;
      }
      try {
        const { data } = await api.get(`/odeme/paytr/${odeme.merchant_oid}`);
        if (bitti) return;
        if (data.durum === 'basarisiz') {
          setHata(data.hata_mesaji || 'Ödeme tamamlanamadı. Tekrar deneyebilirsiniz.');
          setOdeme(null);
          setAsama('form');
        } else if (ODENMIS.includes(data.siparis_durum)) {
          bitti = true;
          Alert.alert('Ödemeniz alındı', 'Siparişiniz hazırlanacak. Siparişlerim ekranından takip edebilirsiniz.');
          siparislereGit();
        } else if (data.durum === 'basarili') {
          bitti = true;
          Alert.alert('Ödemeniz kontrol ediliyor', 'Ödemeniz bize ulaştı, kontrol edip sizi bilgilendireceğiz.');
          siparislereGit();
        }
      } catch (err) {
        // Geçici bağlantı sorunu: sonraki sorguda tekrar denenir
      }
    };
    const zamanlayici = setInterval(sorgula, SORGU_ARALIGI);
    sorgula();
    return () => {
      bitti = true;
      clearInterval(zamanlayici);
    };
    // siparislereGit her çizimde yeniden oluşur, sorgu yalnızca aşama ve ödeme değişince yenilenir
  }, [asama, odeme]);

  const odemeyeBasla = async () => {
    const numara = telefon.trim();
    if (!/^\+?[0-9][0-9 ()-]{9,19}$/.test(numara)) {
      setHata('Lütfen telefon numaranızı eksiksiz yazın.');
      return;
    }
    setHata(null);
    setYukleniyor(true);
    try {
      const { data } = await api.post(`/siparisler/${siparisId}/odeme/paytr`, { telefon: numara });
      setOdeme(data);
      setAsama('odeme');
    } catch (err) {
      setHata(err.response?.status === 429 ? sinirMesaji(err) : hataMesaji(err, 'Ödeme başlatılamadı.'));
    } finally {
      setYukleniyor(false);
    }
  };

  const yonlendirmeyiYakala = (istek) => {
    if (istek.url.includes(TAMAM_ADRESI)) {
      setAsama('onay');
      return false;
    }
    if (istek.url.includes(HATA_ADRESI)) {
      setHata('Ödeme tamamlanamadı. Tekrar deneyebilirsiniz.');
      setOdeme(null);
      setAsama('form');
      return false;
    }
    return true;
  };

  if (asama === 'odeme') {
    return (
      <View style={styles.container}>
        {odeme.test_modu ? <Text style={styles.testBandi}>TEST MODU: kartınızdan para çekilmez</Text> : null}
        <WebView
          source={{ uri: odeme.odeme_url }}
          onShouldStartLoadWithRequest={yonlendirmeyiYakala}
          originWhitelist={['https://*', 'http://*']}
          setSupportMultipleWindows={false}
          startInLoadingState
          renderLoading={() => (
            <View style={styles.yuklemeKatmani}>
              <ActivityIndicator size="large" color={renk.birincil} />
            </View>
          )}
          onError={() => {
            setHata('Ödeme sayfası açılamadı. İnternet bağlantınızı kontrol edip tekrar deneyin.');
            setOdeme(null);
            setAsama('form');
          }}
        />
        <TouchableOpacity
          style={styles.vazgec}
          onPress={() => {
            setOdeme(null);
            setAsama('form');
          }}
        >
          <Text style={styles.vazgecYazi}>Vazgeç</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (asama === 'onay') {
    return (
      <View style={styles.ortala}>
        <ActivityIndicator size="large" color={renk.birincil} />
        <Text style={styles.bilgi}>Ödemeniz doğrulanıyor, lütfen bekleyin.</Text>
      </View>
    );
  }

  if (asama === 'gecikti') {
    return (
      <View style={styles.ortala}>
        <Text style={styles.bilgi}>
          Ödeme sonucu henüz bize ulaşmadı. Kartınızdan tekrar çekim olmasın diye yeniden ödeme yapmayın; sonucu birkaç dakika içinde Siparişlerim ekranında görebilirsiniz.
        </Text>
        <TouchableOpacity style={styles.buton} onPress={siparislereGit}>
          <Text style={styles.butonYazi}>Siparişlerime git</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.icerik} keyboardShouldPersistTaps="handled">
        <Text style={styles.baslik}>Sipariş #{siparisId}</Text>
        <Text style={styles.tutar}>{para(tutar)}</Text>

        <Text style={styles.etiket}>Telefon numaranız</Text>
        <TextInput
          style={styles.girdi}
          value={telefon}
          onChangeText={(deger) => {
            telefonDegisti.current = true;
            setTelefon(deger);
          }}
          placeholder="05xx xxx xx xx"
          keyboardType="phone-pad"
          autoComplete="tel"
          maxLength={20}
        />
        {hata ? <Text style={styles.hata}>{hata}</Text> : null}

        <TouchableOpacity style={[styles.buton, yukleniyor && styles.pasif]} onPress={odemeyeBasla} disabled={yukleniyor}>
          {yukleniyor ? <ActivityIndicator color="#fff" /> : <Text style={styles.butonYazi}>Kartla öde</Text>}
        </TouchableOpacity>

        {odemeBilgisi ? (
          <View style={styles.havale}>
            <Text style={styles.havaleBaslik}>Havale/EFT ile ödemek isterseniz</Text>
            <Text style={styles.havaleYazi}>{odemeBilgisi}</Text>
          </View>
        ) : null}
        <TouchableOpacity style={styles.sonra} onPress={siparislereGit}>
          <Text style={styles.sonraYazi}>Daha sonra öde</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  icerik: { padding: 20 },
  ortala: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, backgroundColor: '#fff' },
  baslik: { fontSize: 15, color: renk.yaziIkincil },
  tutar: { fontSize: 28, fontWeight: 'bold', marginTop: 4, marginBottom: 24 },
  etiket: { fontSize: 14, fontWeight: '600', marginBottom: 6 },
  girdi: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, fontSize: 16 },
  hata: { color: renk.tehlike, marginTop: 10 },
  buton: { backgroundColor: renk.birincil, paddingVertical: 14, paddingHorizontal: 24, borderRadius: 8, alignItems: 'center', marginTop: 16 },
  pasif: { opacity: 0.6 },
  butonYazi: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  havale: { marginTop: 28, padding: 14, borderRadius: 8, backgroundColor: renk.zemin },
  havaleBaslik: { fontWeight: '600', marginBottom: 6 },
  havaleYazi: { color: renk.yaziIkincil, lineHeight: 20 },
  sonra: { alignItems: 'center', paddingVertical: 16, marginTop: 8 },
  sonraYazi: { color: renk.yaziIkincil, fontWeight: '600' },
  bilgi: { fontSize: 15, color: renk.yaziIkincil, textAlign: 'center', marginTop: 16, lineHeight: 22 },
  testBandi: { backgroundColor: '#fff3cd', color: '#664d03', textAlign: 'center', padding: 8, fontWeight: '600' },
  yuklemeKatmani: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  vazgec: { alignItems: 'center', paddingVertical: 14, borderTopWidth: 1, borderTopColor: '#eee' },
  vazgecYazi: { color: renk.yaziIkincil, fontWeight: '600' },
});
