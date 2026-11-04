import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { renk } from '../theme';

export default function AdetSecici({ adet, onAzalt, onArttir, azaltDevre, arttirDevre }) {
  return (
    <View style={styles.satir}>
      <TouchableOpacity
        style={[styles.buton, azaltDevre && styles.butonDevre]}
        onPress={onAzalt}
        disabled={azaltDevre}
        accessibilityLabel="Adedi azalt"
      >
        <Text style={styles.butonYazi}>−</Text>
      </TouchableOpacity>
      <Text style={styles.adet}>{adet}</Text>
      <TouchableOpacity
        style={[styles.buton, arttirDevre && styles.butonDevre]}
        onPress={onArttir}
        disabled={arttirDevre}
        accessibilityLabel="Adedi artır"
      >
        <Text style={styles.butonYazi}>+</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  satir: { flexDirection: 'row', alignItems: 'center' },
  buton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: renk.cizgi,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: renk.kart,
  },
  butonDevre: { opacity: 0.35 },
  butonYazi: { fontSize: 20, color: renk.yazi, lineHeight: 22 },
  adet: { minWidth: 36, textAlign: 'center', fontSize: 16, fontWeight: 'bold', color: renk.yazi },
});
