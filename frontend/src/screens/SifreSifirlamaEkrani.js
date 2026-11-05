import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import api, { hataMesaji, sinirMesaji } from '../services/api';
import { renk } from '../theme';

const KOD_UZUNLUGU = 8;

function hataYazisi(err, varsayilan) {
  if (err.response?.status === 429) return sinirMesaji(err);
  if (err.response) return varsayilan;
  return hataMesaji(err); // sunucuya ulaşılamadı
}

export default function SifreSifirlamaEkrani({ navigation }) {
  const [adim, setAdim] = useState('eposta'); // 'eposta' -> 'kod'
  const [ePosta, setEPosta] = useState('');
  const [kod, setKod] = useState('');
  const [sifre, setSifre] = useState('');
  const [sifreTekrar, setSifreTekrar] = useState('');
  const [yukleniyor, setYukleniyor] = useState(false);

  const kodIste = async () => {
    const temiz = ePosta.trim();
    if (!temiz.includes('@')) {
      Alert.alert('Eksik bilgi', 'Lütfen e-posta adresinizi yazın.');
      return;
    }
    setYukleniyor(true);
    try {
      await api.post('/sifre-sifirlama/iste', { e_posta: temiz });
      setAdim('kod');
    } catch (err) {
      Alert.alert('Kod gönderilemedi', hataYazisi(err, 'Lütfen e-posta adresinizi kontrol edin.'));
    } finally {
      setYukleniyor(false);
    }
  };

  const tamamla = async () => {
    const temizKod = kod.replace(/\s/g, '');
    if (temizKod.length !== KOD_UZUNLUGU) {
      Alert.alert('Eksik bilgi', `E-postadaki ${KOD_UZUNLUGU} haneli kodu yazın.`);
      return;
    }
    if (sifre.length < 6) {
      Alert.alert('Eksik bilgi', 'Yeni şifre en az 6 karakter olmalı.');
      return;
    }
    if (sifre !== sifreTekrar) {
      Alert.alert('Şifreler eşleşmiyor', 'Yeni şifreyi iki alana da aynı yazın.');
      return;
    }
    setYukleniyor(true);
    try {
      await api.post('/sifre-sifirlama/tamamla', { e_posta: ePosta.trim(), kod: temizKod, yeni_sifre: sifre });
      Alert.alert('Şifreniz değiştirildi', 'Yeni şifrenizle giriş yapabilirsiniz.', [
        { text: 'Tamam', onPress: () => navigation.goBack() },
      ]);
    } catch (err) {
      Alert.alert('Şifre değiştirilemedi', hataYazisi(err, 'Kod geçersiz veya süresi dolmuş. Yeni kod isteyebilirsiniz.'));
    } finally {
      setYukleniyor(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <ScrollView contentContainerStyle={styles.icerik} keyboardShouldPersistTaps="handled" keyboardDismissMode="on-drag">
        {adim === 'eposta' ? (
          <>
            <Text style={styles.aciklama}>E-posta adresinizi yazın, şifre sıfırlama kodunu gönderelim.</Text>
            <TextInput
              style={styles.input}
              placeholder="E-posta"
              value={ePosta}
              onChangeText={setEPosta}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              textContentType="emailAddress"
              autoComplete="email"
              onSubmitEditing={kodIste}
            />
            <TouchableOpacity style={[styles.buton, yukleniyor && styles.butonDevre]} onPress={kodIste} disabled={yukleniyor}>
              <Text style={styles.butonYazi}>{yukleniyor ? 'Gönderiliyor...' : 'Kod Gönder'}</Text>
            </TouchableOpacity>
          </>
        ) : (
          <>
            <Text style={styles.aciklama}>
              {ePosta.trim()} kayıtlıysa {KOD_UZUNLUGU} haneli bir kod gönderdik. Kod 15 dakika geçerlidir. Gelmediyse spam klasörüne bakın.
            </Text>
            <TextInput
              style={styles.input}
              placeholder={`${KOD_UZUNLUGU} haneli kod`}
              value={kod}
              onChangeText={setKod}
              keyboardType="number-pad"
              textContentType="oneTimeCode"
              autoComplete="one-time-code"
              maxLength={KOD_UZUNLUGU + 2}
            />
            <TextInput
              style={styles.input}
              placeholder="Yeni şifre"
              value={sifre}
              onChangeText={setSifre}
              secureTextEntry
              textContentType="newPassword"
              autoComplete="new-password"
              maxLength={72}
            />
            <TextInput
              style={styles.input}
              placeholder="Yeni şifre (tekrar)"
              value={sifreTekrar}
              onChangeText={setSifreTekrar}
              secureTextEntry
              textContentType="newPassword"
              autoComplete="new-password"
              maxLength={72}
            />
            <TouchableOpacity style={[styles.buton, yukleniyor && styles.butonDevre]} onPress={tamamla} disabled={yukleniyor}>
              <Text style={styles.butonYazi}>{yukleniyor ? 'Kaydediliyor...' : 'Şifreyi Değiştir'}</Text>
            </TouchableOpacity>
            <View style={styles.altSatir}>
              <TouchableOpacity style={styles.baglanti} onPress={kodIste} disabled={yukleniyor}>
                <Text style={styles.baglantiYazi}>Kodu tekrar gönder</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.baglanti} onPress={() => setAdim('eposta')} disabled={yukleniyor}>
                <Text style={styles.baglantiYazi}>E-postayı değiştir</Text>
              </TouchableOpacity>
            </View>
          </>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  icerik: { padding: 24 },
  aciklama: { fontSize: 15, color: renk.yaziIkincil, lineHeight: 21, marginBottom: 20 },
  input: { borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 12, fontSize: 16, marginBottom: 16 },
  buton: { backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center' },
  butonDevre: { backgroundColor: renk.devre },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  altSatir: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', marginTop: 12 },
  baglanti: { paddingVertical: 10 },
  baglantiYazi: { color: renk.baglanti, fontSize: 15 },
});
