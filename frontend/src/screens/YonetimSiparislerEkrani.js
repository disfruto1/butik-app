import React, { useCallback, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, TouchableOpacity, ActivityIndicator, Alert, ScrollView, TextInput,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import api, { hataMesaji } from '../services/api';
import SiparisKarti from '../components/SiparisKarti';
import { renk } from '../theme';
import { DURUM_ETIKET, DURUM_GECISLERI, DURUM_BUTON } from '../utils/format';

export default function YonetimSiparislerEkrani() {
  const [durum, setDurum] = useState(null); // null = tümü
  const [siparisler, setSiparisler] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [yenileniyor, setYenileniyor] = useState(false);
  const [hata, setHata] = useState(null);

  const yukle = useCallback(async () => {
    try {
      const res = await api.get('/siparisler', { params: durum ? { durum, limit: 100 } : { limit: 100 } });
      setSiparisler(res.data);
      setHata(null);
    } catch (err) {
      setHata(hataMesaji(err, 'Siparişler yüklenemedi.'));
    }
  }, [durum]);

  useFocusEffect(
    useCallback(() => {
      setYukleniyor(true);
      yukle().finally(() => setYukleniyor(false));
    }, [yukle])
  );

  const yenile = async () => {
    setYenileniyor(true);
    await yukle();
    setYenileniyor(false);
  };

  const durumuGuncelle = async (siparis, yeniDurum, takipNo) => {
    try {
      await api.patch(`/siparisler/${siparis.id}/durum`, { durum: yeniDurum, takip_no: takipNo || null });
      await yukle();
    } catch (err) {
      Alert.alert('Hata', hataMesaji(err, 'Durum güncellenemedi.'));
    }
  };

  const onayla = (siparis, yeniDurum, takipNo) => {
    if (yeniDurum === 'iptal_edildi') {
      Alert.alert('Siparişi iptal et', `#${siparis.id} iptal edilecek ve stok geri eklenecek.`, [
        { text: 'Vazgeç', style: 'cancel' },
        { text: 'İptal et', style: 'destructive', onPress: () => durumuGuncelle(siparis, yeniDurum) },
      ]);
    } else {
      durumuGuncelle(siparis, yeniDurum, takipNo);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.filtre}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 12 }}>
          <Chip yazi="Tümü" secili={durum === null} onPress={() => setDurum(null)} />
          {Object.keys(DURUM_ETIKET).map((d) => (
            <Chip key={d} yazi={DURUM_ETIKET[d]} secili={durum === d} onPress={() => setDurum(d)} />
          ))}
        </ScrollView>
      </View>

      {yukleniyor ? (
        <View style={styles.ortala}>
          <ActivityIndicator size="large" color={renk.birincil} />
        </View>
      ) : hata && siparisler.length === 0 ? (
        <View style={styles.ortala}>
          <Text style={styles.hata}>{hata}</Text>
        </View>
      ) : (
        <FlatList
          data={siparisler}
          keyExtractor={(s) => s.id.toString()}
          refreshing={yenileniyor}
          onRefresh={yenile}
          contentContainerStyle={styles.liste}
          keyboardShouldPersistTaps="handled"
          ListEmptyComponent={<Text style={styles.bos}>Bu filtrede sipariş yok.</Text>}
          renderItem={({ item }) => <SiparisIslemKarti siparis={item} onGecis={onayla} />}
        />
      )}
    </View>
  );
}

function SiparisIslemKarti({ siparis, onGecis }) {
  const [takipNo, setTakipNo] = useState(siparis.takip_no || '');
  const secenekler = DURUM_GECISLERI[siparis.durum] || [];

  return (
    <SiparisKarti siparis={siparis}>
      {secenekler.includes('kargoya_verildi') ? (
        <TextInput
          style={styles.takipInput}
          placeholder="Kargo takip no (isteğe bağlı)"
          value={takipNo}
          onChangeText={setTakipNo}
          autoCapitalize="characters"
        />
      ) : null}
      {secenekler.map((hedef) => (
        <TouchableOpacity
          key={hedef}
          style={[styles.buton, hedef === 'iptal_edildi' && styles.butonIptal]}
          onPress={() => onGecis(siparis, hedef, hedef === 'kargoya_verildi' ? takipNo.trim() : undefined)}
        >
          <Text style={[styles.butonYazi, hedef === 'iptal_edildi' && { color: renk.tehlike }]}>{DURUM_BUTON[hedef]}</Text>
        </TouchableOpacity>
      ))}
    </SiparisKarti>
  );
}

function Chip({ yazi, secili, onPress }) {
  return (
    <TouchableOpacity style={[styles.chip, secili && styles.chipSecili]} onPress={onPress}>
      <Text style={[styles.chipYazi, secili && { color: '#fff' }]}>{yazi}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin },
  filtre: { paddingVertical: 10 },
  liste: { padding: 16, paddingTop: 4 },
  ortala: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  hata: { color: renk.tehlike, textAlign: 'center' },
  bos: { textAlign: 'center', color: renk.yaziSoluk, marginTop: 40 },
  chip: { paddingVertical: 6, paddingHorizontal: 14, borderRadius: 16, borderWidth: 1, borderColor: renk.cizgi, backgroundColor: '#fff', marginRight: 8 },
  chipSecili: { backgroundColor: renk.birincil, borderColor: renk.birincil },
  chipYazi: { color: renk.yazi, fontSize: 14 },
  takipInput: { borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 10, marginTop: 12, fontSize: 15 },
  buton: { marginTop: 10, paddingVertical: 11, borderRadius: 8, backgroundColor: renk.birincil, alignItems: 'center' },
  butonIptal: { backgroundColor: '#fff', borderWidth: 1, borderColor: renk.tehlike },
  butonYazi: { color: '#fff', fontWeight: 'bold' },
});
