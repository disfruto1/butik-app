import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { renk } from '../theme';
import { para, tarih, DURUM_ETIKET } from '../utils/format';

// children: kartın altına eklenecek butonlar vb.
export default function SiparisKarti({ siparis, children }) {
  return (
    <View style={styles.kart}>
      <View style={styles.ust}>
        <Text style={styles.no}>Sipariş #{siparis.id}</Text>
        <Text style={[styles.durum, siparis.durum === 'iptal_edildi' && { color: renk.tehlike }]}>
          {DURUM_ETIKET[siparis.durum] || siparis.durum}
        </Text>
      </View>
      <Text style={styles.tarih}>
        {tarih(siparis.olusturulma_tarihi)}
        {siparis.musteri_ad ? ` · ${siparis.musteri_ad}` : ''}
      </Text>
      {siparis.kalemler.map((k) => (
        <Text key={k.id} style={styles.kalem}>
          {k.adet} × {k.urun_adi} · {para(Number(k.birim_fiyat) * k.adet)}
        </Text>
      ))}
      {siparis.kargo_adres ? <Text style={styles.adres}>Adres: {siparis.kargo_adres}</Text> : null}
      {siparis.takip_no ? <Text style={styles.takip}>Kargo takip no: {siparis.takip_no}</Text> : null}
      <Text style={styles.toplam}>Toplam: {para(siparis.toplam_tutar)}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  kart: { backgroundColor: renk.kart, borderRadius: 8, padding: 16, marginBottom: 12 },
  ust: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  no: { fontSize: 16, fontWeight: 'bold', color: renk.yazi },
  durum: { fontSize: 13, color: renk.baglanti, fontWeight: 'bold' },
  tarih: { fontSize: 12, color: renk.yaziSoluk, marginTop: 2, marginBottom: 10 },
  kalem: { fontSize: 14, color: renk.yaziIkincil, marginBottom: 2 },
  adres: { fontSize: 13, color: renk.yaziSoluk, marginTop: 8 },
  takip: { fontSize: 13, color: renk.yazi, marginTop: 4, fontWeight: 'bold' },
  toplam: { fontSize: 16, fontWeight: 'bold', color: renk.fiyat, marginTop: 10 },
});
