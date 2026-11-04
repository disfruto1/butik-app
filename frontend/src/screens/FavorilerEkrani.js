import React from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import { useFavori } from '../context/FavoriContext';
import UrunKarti from '../components/UrunKarti';
import { renk } from '../theme';

export default function FavorilerEkrani({ navigation }) {
  const { favoriler, favoriDegistir } = useFavori();

  return (
    <View style={styles.container}>
      <FlatList
        data={favoriler}
        keyExtractor={(u) => u.id.toString()}
        contentContainerStyle={styles.liste}
        ListEmptyComponent={<Text style={styles.bos}>Henüz favori ürününüz yok. Ürün listesinde ♡ simgesine dokunarak ekleyebilirsiniz.</Text>}
        renderItem={({ item }) => (
          <UrunKarti
            urun={item}
            onPress={() => navigation.navigate('UrunDetay', { urun: item })}
            favori
            onFavori={() => favoriDegistir(item)}
          />
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: renk.zemin },
  liste: { padding: 16 },
  bos: { textAlign: 'center', color: renk.yaziSoluk, marginTop: 40, lineHeight: 22 },
});
