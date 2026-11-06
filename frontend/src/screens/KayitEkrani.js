import React, { useEffect, useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, KeyboardAvoidingView, Platform,
  ScrollView, Modal, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import api, { hataMesaji } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { renk } from '../theme';

const metinleriAl = () => api.get('/yasal/kayit').then((res) => res.data);

export default function KayitEkrani() {
  const { girisYap } = useAuth();
  const [ad, setAd] = useState('');
  const [email, setEmail] = useState('');
  const [sifre, setSifre] = useState('');
  const [telefon, setTelefon] = useState('');
  const [aydinlatmaOkundu, setAydinlatmaOkundu] = useState(false);
  // İzin kutuları boş gelir: yönetmelik önceden işaretli onayı kabul etmez
  const [epostaIzni, setEpostaIzni] = useState(false);
  const [smsIzni, setSmsIzni] = useState(false);
  const [metinler, setMetinler] = useState(null);
  const [metinHatasi, setMetinHatasi] = useState(false);
  const [metinAcik, setMetinAcik] = useState(false);
  const [yukleniyor, setYukleniyor] = useState(false);

  useEffect(() => {
    metinleriAl().then(setMetinler).catch(() => setMetinHatasi(true));
  }, []);

  const metinleriYenidenDene = () => {
    setMetinHatasi(false);
    return metinleriAl().then(setMetinler).catch(() => setMetinHatasi(true));
  };

  const handleKayit = async () => {
    if (!ad.trim() || !email.trim() || !sifre) {
      Alert.alert('Hata', 'Tüm alanları doldurunuz.');
      return;
    }
    if (sifre.length < 6) {
      Alert.alert('Hata', 'Şifre en az 6 karakter olmalı.');
      return;
    }
    if (smsIzni && !/^\+?[0-9][0-9 ()-]{9,19}$/.test(telefon.trim())) {
      Alert.alert('Hata', 'SMS izni için telefon numaranızı eksiksiz yazın.');
      return;
    }
    if (!aydinlatmaOkundu) {
      Alert.alert('Hata', 'Üye olmak için KVKK Aydınlatma Metni\'ni okuduğunuzu işaretleyin.');
      return;
    }
    setYukleniyor(true);
    try {
      await api.post('/kayit', {
        ad: ad.trim(),
        e_posta: email.trim(),
        sifre,
        aydinlatma_okundu: true,
        metin_surumu: metinler.surum,
        eposta_izni: epostaIzni,
        sms_izni: smsIzni,
        telefon: smsIzni ? telefon.trim() : null,
      });
    } catch (error) {
      if (error.response?.status === 409) {
        // Metin değişmiş: yeni metin okunmadan onay kaydedilmez
        await metinleriYenidenDene();
        setAydinlatmaOkundu(false);
        setEpostaIzni(false);
        setSmsIzni(false);
        Alert.alert('Metinler güncellendi', 'Lütfen güncel metinleri okuyup yeniden işaretleyin.');
      } else {
        const mesaj = error.response?.status === 422 ? 'Bilgileri kontrol edin (geçerli bir e-posta girin).' : hataMesaji(error, 'Kayıt yapılamadı.');
        Alert.alert('Hata', mesaj);
      }
      setYukleniyor(false);
      return;
    }
    try {
      // Kayıttan sonra otomatik giriş
      const params = new URLSearchParams();
      params.append('username', email.trim());
      params.append('password', sifre);
      const response = await api.post('/giris', params.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      await girisYap(response.data.access_token);
    } catch (error) {
      Alert.alert('Kayıt tamamlandı', 'Hesabınız oluşturuldu, lütfen giriş yapın.');
      setYukleniyor(false);
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.icerik} keyboardShouldPersistTaps="handled">
        <Text style={styles.altBaslik}>Yeni hesap oluşturun</Text>
        <TextInput style={styles.input} placeholder="Ad Soyad" value={ad} onChangeText={setAd} />
        <TextInput
          style={styles.input}
          placeholder="E-posta"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
        />
        <TextInput
          style={styles.input}
          placeholder="Şifre (en az 6 karakter)"
          value={sifre}
          onChangeText={setSifre}
          secureTextEntry
        />

        {metinler ? (
          <View style={styles.onaylar}>
            <OnayKutusu
              secili={aydinlatmaOkundu}
              onPress={() => setAydinlatmaOkundu(!aydinlatmaOkundu)}
              erisimEtiketi="KVKK Aydınlatma Metni'ni okudum"
            >
              <Text style={styles.onayYazi}>
                <Text style={styles.baglanti} onPress={() => setMetinAcik(true)}>KVKK Aydınlatma Metni</Text>
                {"'ni okudum."}
              </Text>
            </OnayKutusu>
            <OnayKutusu secili={epostaIzni} onPress={() => setEpostaIzni(!epostaIzni)} erisimEtiketi={metinler.eposta_izni}>
              <Text style={styles.onayYazi}>{metinler.eposta_izni}</Text>
            </OnayKutusu>
            <OnayKutusu secili={smsIzni} onPress={() => setSmsIzni(!smsIzni)} erisimEtiketi={metinler.sms_izni}>
              <Text style={styles.onayYazi}>{metinler.sms_izni}</Text>
            </OnayKutusu>
            {smsIzni ? (
              <TextInput
                style={styles.input}
                placeholder="Telefon (05xx xxx xx xx)"
                value={telefon}
                onChangeText={setTelefon}
                keyboardType="phone-pad"
                autoComplete="tel"
                maxLength={20}
              />
            ) : null}
            <Text style={styles.not}>{metinler.izin_notu}</Text>
          </View>
        ) : metinHatasi ? (
          <View style={styles.metinDurumu}>
            <Text style={styles.not}>Üyelik metinleri yüklenemedi.</Text>
            <TouchableOpacity onPress={metinleriYenidenDene}>
              <Text style={styles.baglanti}>Tekrar dene</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <ActivityIndicator style={styles.metinDurumu} color={renk.birincil} />
        )}

        <TouchableOpacity
          style={[styles.buton, (yukleniyor || !metinler) && styles.butonDevre]}
          onPress={handleKayit}
          disabled={yukleniyor || !metinler}
        >
          <Text style={styles.butonYazi}>{yukleniyor ? 'Kaydediliyor...' : 'Kayıt Ol'}</Text>
        </TouchableOpacity>
      </ScrollView>

      <Modal visible={metinAcik} animationType="slide" onRequestClose={() => setMetinAcik(false)}>
        <SafeAreaView style={styles.container}>
          <Text style={styles.metinBaslik}>KVKK Aydınlatma Metni</Text>
          <ScrollView contentContainerStyle={styles.metinIcerik}>
            <Text style={styles.metin}>{metinler?.aydinlatma}</Text>
          </ScrollView>
          <TouchableOpacity style={styles.kapat} onPress={() => setMetinAcik(false)}>
            <Text style={styles.butonYazi}>Kapat</Text>
          </TouchableOpacity>
        </SafeAreaView>
      </Modal>
    </KeyboardAvoidingView>
  );
}

function OnayKutusu({ secili, onPress, erisimEtiketi, children }) {
  return (
    <TouchableOpacity
      style={styles.onaySatiri}
      onPress={onPress}
      accessibilityRole="checkbox"
      accessibilityState={{ checked: secili }}
      accessibilityLabel={erisimEtiketi}
    >
      <View style={[styles.kutu, secili && styles.kutuSecili]}>
        {secili ? <Text style={styles.tik}>✓</Text> : null}
      </View>
      <View style={styles.onayMetni}>{children}</View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  icerik: { flexGrow: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  altBaslik: { fontSize: 18, color: renk.yaziIkincil, marginBottom: 24 },
  input: { alignSelf: 'stretch', borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 12, fontSize: 16, marginBottom: 16 },
  onaylar: { alignSelf: 'stretch', marginBottom: 16 },
  onaySatiri: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 14 },
  kutu: { width: 22, height: 22, borderRadius: 4, borderWidth: 2, borderColor: renk.yaziSoluk, alignItems: 'center', justifyContent: 'center', marginRight: 10, marginTop: 1 },
  kutuSecili: { borderColor: renk.birincil, backgroundColor: renk.birincil },
  tik: { color: '#fff', fontSize: 14, fontWeight: 'bold', lineHeight: 16 },
  onayMetni: { flex: 1 },
  onayYazi: { fontSize: 14, color: renk.yazi, lineHeight: 20 },
  baglanti: { color: renk.baglanti, textDecorationLine: 'underline' },
  not: { fontSize: 12, color: renk.yaziSoluk, lineHeight: 18 },
  metinDurumu: { alignItems: 'center', marginBottom: 16 },
  metinBaslik: { fontSize: 18, fontWeight: 'bold', color: renk.yazi, padding: 20, paddingBottom: 8 },
  metinIcerik: { padding: 20, paddingTop: 8 },
  metin: { fontSize: 15, color: renk.yazi, lineHeight: 23 },
  kapat: { backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center', margin: 20 },
  buton: { alignSelf: 'stretch', backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center' },
  butonDevre: { backgroundColor: renk.devre },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
