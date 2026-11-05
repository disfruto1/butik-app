import { Platform } from 'react-native';

// API adresi frontend/.env dosyasındaki EXPO_PUBLIC_API_URL ile ayarlanır.
//  - Gerçek telefon: bilgisayarın yerel IP'si, örn. http://192.168.1.20:8000
//  - Android emülatör: http://10.0.2.2:8000 (varsayılan)
//  - iOS simülatör / web: http://127.0.0.1:8000 (varsayılan)
const varsayilan = Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://127.0.0.1:8000';

export const API_URL = (process.env.EXPO_PUBLIC_API_URL || varsayilan).replace(/\/+$/, '');
