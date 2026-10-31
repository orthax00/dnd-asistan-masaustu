// Yerel depolama: portreler, haritalar, eşya ve ansiklopedi görselleri Chromium'un disk önbelleğinde tutulur.
// Görseller Supabase'e benzersiz adla ve "1 yıl sakla" başlığıyla yüklendiği için bir kez inen görsel
// bir daha indirilmez. Önbellek kullanıcının AppData klasöründedir (%APPDATA%\DnD Asistanı\Cache).
const ONBELLEK_BOYUTU = 4 * 1024 * 1024 * 1024; // 4 GB; dolarsa en uzun süre açılmayan görsel silinir

function kurOnbellek(app) {
  // Uygulama hazır olmadan verilmeli; sonradan değiştirilemez.
  app.commandLine.appendSwitch("disk-cache-size", String(ONBELLEK_BOYUTU));
}

module.exports = { kurOnbellek, ONBELLEK_BOYUTU };
