import axios from 'axios';
import { API_URL } from '../config';

// AuthContext bu nesneyi günceller. İstekler anlık token'ı buradan okur.
export const authDurumu = {
  token: null,
  oturumDustu: null, // 401 gelince çağrılır (otomatik çıkış)
};

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  if (authDurumu.token) {
    config.headers.Authorization = 'Bearer ' + authDurumu.token;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    // Sadece token ile gönderilmiş bir istek 401 alırsa oturum bitmiş demektir.
    // (Yanlış şifreyle giriş denemesi de 401 döner, onu çıkış sayma.)
    const tokenluIstek = !!err.config?.headers?.Authorization;
    if (err.response?.status === 401 && tokenluIstek && authDurumu.oturumDustu) {
      authDurumu.oturumDustu();
    }
    return Promise.reject(err);
  }
);

export function hataMesaji(err, varsayilan = 'Bir hata oluştu.') {
  if (!err?.response) {
    return 'Sunucuya ulaşılamadı. İnternet bağlantınızı ve API adresini kontrol edin (' + API_URL + ').';
  }
  const detay = err.response.data?.detail;
  return typeof detay === 'string' ? detay : varsayilan;
}

// Deneme sınırı (429) yanıtındaki bekleme süresini kullanıcıya yazar
export function sinirMesaji(err) {
  const saniye = Number(err.response?.headers?.['retry-after']);
  const sure = saniye > 0 ? `${Math.ceil(saniye / 60)} dakika sonra` : 'daha sonra';
  return `Çok fazla deneme yapıldı. Lütfen ${sure} tekrar deneyin.`;
}

export default api;
