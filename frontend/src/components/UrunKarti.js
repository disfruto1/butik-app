import React from 'react';
import { View, Text, Image, TouchableOpacity, StyleSheet } from 'react-native';
import { renk } from '../theme';
import { para } from '../utils/format';

export function stokEtiketi(urun) {
  if (urun.stok == null) return null;
  if (urun.stok === 0) return { yazi: 'Tükendi', renk: renk.tehlike };
  if (urun.stok <= 5) return { yazi: `Son ${urun.stok} adet`, renk: '#e67e22' };
  return null;
}

export function UrunGorseli({ urun, boyut = 64, stil }) {
  if (urun.gorsel_url) {
    return <Image source={{ uri: urun.gorsel_url }} style={[{ width: boyut, height: boyut, borderRadius: 8, backgroundColor: '#eee' }, stil]} />;
  }
  return (
    <View style={[styles.bosGorsel, { width: boyut, height: boyut }, stil]}>
      <Text style={[styles.harf, { fontSize: boyut / 2.4 }]}>{(urun.ad || '?').charAt(0).toUpperCase()}</Text>
    </View>
  );
}

export default function UrunKarti({ urun, onPress, favori, onFavori, etiket }) {
  const stok = stokEtiketi(urun);
  return (
    <TouchableOpacity style={styles.kart} onPress={onPress} activeOpacity={0.7}>
      <UrunGorseli urun={urun} />
      <View style={styles.orta}>
        <Text style={styles.ad} numberOfLines={2}>{urun.ad}</Text>
        {etiket ? <Text style={styles.pasif}>{etiket}</Text> : null}
        {stok ? <Text style={[styles.stok, { color: stok.renk }]}>{stok.yazi}</Text> : null}
        <Text style={styles.fiyat}>{para(urun.fiyat)}</Text>
      </View>
      {onFavori ? (
        <TouchableOpacity onPress={onFavori} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }} accessibilityLabel="Favori">
          <Text style={[styles.kalp, favori && { color: renk.tehlike }]}>{favori ? '♥' : '♡'}</Text>
        </TouchableOpacity>
      ) : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  kart: { backgroundColor: renk.kart, padding: 12, borderRadius: 8, marginBottom: 12, flexDirection: 'row', alignItems: 'center' },
  orta: { flex: 1, paddingHorizontal: 12 },
  ad: { fontSize: 16, color: renk.yazi, fontWeight: 'bold' },
  pasif: { fontSize: 12, color: renk.tehlike, marginTop: 2 },
  stok: { fontSize: 12, fontWeight: 'bold', marginTop: 2 },
  fiyat: { fontSize: 15, fontWeight: 'bold', color: renk.fiyat, marginTop: 4 },
  kalp: { fontSize: 26, color: renk.yaziSoluk },
  bosGorsel: { borderRadius: 8, backgroundColor: '#eceff1', alignItems: 'center', justifyContent: 'center' },
  harf: { color: renk.yaziSoluk, fontWeight: 'bold' },
});
