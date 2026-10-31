# DnD Asistanı masaüstü uygulaması

**İndir:** [Releases](https://github.com/orthax00/dnd-asistan-masaustu/releases/latest) sayfasındaki `DnD-Asistani-Kurulum-x.y.z.exe`.
Windows "Bilgisayarınız korundu" derse "Ek bilgi" → "Yine de çalıştır". Kurduktan sonra uygulama kendini günceller.

Siteyi (https://dnd-asistan.vercel.app) adres çubuğu olmayan kendi penceresinde açan Windows uygulaması (Electron).

- Kampanyalar, karakterler, zarlar ve sohbet çok oyunculu olduğu için Supabase'de kalır.
- Gemini/NovelAI anahtarları sunucuda kalır; kurulum dosyası arkadaşlara anahtarsız verilebilir.
- Görseller (portre, harita, eşya, ansiklopedi) diskteki önbellekte tutulur (4 GB'a kadar), bir kez inen görsel tekrar inmez.
- Arayüz Vercel'den geldiği için yeni özellikler yeniden kurmadan gelir. Bu klasör değişirse yeni kurulum dosyası gerekir.

- E-postayla giriş: linke tıklanınca tarayıcı "DnD Asistanı açılsın mı?" diye sorar, giriş uygulamada tamamlanır
  (`dndasistani://giris`; Supabase'de Redirect URLs'e `dndasistani://**` eklidir).
- Çevrimdışı mod: internet varken açılan her kampanyanın karakter sayfaları, ansiklopedisi, tarih kitabı, mirası ve haritaları
  `%APPDATA%\DnD Asistanı\cevrimdisi` klasörüne yazılır (src/lib/offline.ts). İnternet yokken "Masaya ulaşılamadı"
  ekranındaki "Çevrimdışı oku" ya da Alt menüsündeki "Çevrimdışı kayıtlar" bunları salt okunur açar.

Kısayollar: F11 tam ekran, F5 yenile, Alt+Sol/Sağ geri/ileri, Ctrl+= / Ctrl+- yakınlaştır, Alt menüyü gösterir.

## Geliştirme

```
npm install
npm start                                        # siteyi açar
set DND_URL=http://localhost:3000 && npm start   # yerel sunucuyu açar (Windows cmd)
npm run dist                                     # dist/DnD-Asistani-Kurulum-x.y.z.exe
```

## Yeni sürüm yayınlama

1. `package.json` içindeki `version`'ı artır (ör. 1.3.0 → 1.4.0) ve main'e gönder.
2. "Yayınla" iş akışı `v1.4.0` etiketini açar, Windows'ta derler ve Release'e yükler. Kurulu uygulamalar açılışta
   (ve 4 saatte bir) yeni sürümü görür, arka planda indirir ve "Yeniden başlat ve güncelle" diye sorar.

İndirme linki (arkadaşlar için): https://github.com/orthax00/dnd-asistan-masaustu/releases/latest
