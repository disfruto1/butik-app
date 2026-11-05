import React, { useEffect, useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import api, { hataMesaji } from '../services/api';
import { renk } from '../theme';

export default function AdresFormEkrani({ route, navigation }) {
  const mevcut = route.params?.adres;
  const [baslik, setBaslik] = useState(mevcut?.baslik ?? '');
  const [adres, setAdres] = useState(mevcut?.adres ?? '');
  const [kaydediliyor, setKaydediliyor] = useState(false);

  useEffect(() => {
    navigation.setOptions({ title: mevcut ? 'Adresi Düzenle' : 'Yeni Adres' });
  }, [navigation, mevcut]);

  const kaydet = async () => {
    const veri = { baslik: baslik.trim(), adres: adres.trim() };
    if (!veri.baslik) {
      Alert.alert('Eksik bilgi', 'Adrese bir başlık verin (örneğin Ev veya İş).');
      return;
    }
    if (veri.adres.length < 10) {
      Alert.alert('Eksik bilgi', 'Lütfen adresi eksiksiz yazın.');
      return;
    }
    setKaydediliyor(true);
    try {
      if (mevcut) {
        await api.put(`/adresler/${mevcut.id}`, veri);
      } else {
        await api.post('/adresler', veri);
      }
      navigation.goBack();
    } catch (err) {
      Alert.alert('Kaydedilemedi', hataMesaji(err, 'Adres kaydedilemedi.'));
      setKaydediliyor(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <ScrollView contentContainerStyle={styles.icerik} keyboardShouldPersistTaps="handled">
        <Text style={styles.etiket}>Başlık</Text>
        <TextInput
          style={styles.input}
          placeholder="Ev, İş..."
          value={baslik}
          onChangeText={setBaslik}
          maxLength={60}
        />
        <Text style={styles.etiket}>Adres</Text>
        <TextInput
          style={[styles.input, styles.adresInput]}
          placeholder="Mahalle, sokak, bina/daire no, ilçe, il"
          value={adres}
          onChangeText={setAdres}
          maxLength={500}
          multiline
          textAlignVertical="top"
        />
        <TouchableOpacity
          style={[styles.buton, kaydediliyor && styles.butonDevre]}
          onPress={kaydet}
          disabled={kaydediliyor}
        >
          <Text style={styles.butonYazi}>{kaydediliyor ? 'Kaydediliyor...' : 'Kaydet'}</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin },
  icerik: { padding: 16 },
  etiket: { fontSize: 14, color: renk.yaziIkincil, marginBottom: 6 },
  input: { backgroundColor: '#fff', borderWidth: 1, borderColor: renk.cizgi, borderRadius: 8, padding: 12, fontSize: 15, marginBottom: 16 },
  adresInput: { minHeight: 100 },
  buton: { backgroundColor: renk.birincil, padding: 16, borderRadius: 8, alignItems: 'center' },
  butonDevre: { backgroundColor: renk.devre },
  butonYazi: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
