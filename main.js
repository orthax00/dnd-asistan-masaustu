// DnD Asistanı masaüstü uygulaması: siteyi adres çubuğu olmayan kendi penceresinde açar.
// Veriler (kampanya, karakter, zar, sohbet) çok oyunculu olduğu için Supabase'de kalır; Gemini/NovelAI
// anahtarları da sunucuda durur, böylece kurulum dosyası arkadaşlara anahtarsız verilebilir.
const { app, BrowserWindow, Menu, shell, session, dialog } = require("electron");
const fs = require("node:fs");
const path = require("node:path");
const { fileURLToPath } = require("node:url");
const { kurOnbellek } = require("./onbellek");
const { kurCevrimdisi } = require("./cevrimdisi");
const { kurGuncelleme } = require("./guncelleme");

// DND_URL ile yerel sunucu da açılabilir: `set DND_URL=http://localhost:3000 && npm start`
const APP_URL = process.env.DND_URL || "https://dnd-asistan.vercel.app";
const APP_ORIGIN = new URL(APP_URL).origin;

// Girişin geçtiği adresler pencerenin içinde açılır; geri kalan bağlantılar sistem tarayıcısına gider.
const GIRIS_ALANLARI = [/\.supabase\.co$/, /(^|\.)discord\.com$/, /(^|\.)discordapp\.com$/];
const icerdeKalir = (url) => {
  try {
    const u = new URL(url);
    // Uygulamanın kendi sayfaları (bağlantı yok ekranı, çevrimdışı mod).
    if (u.protocol === "file:") return fileURLToPath(u).startsWith(__dirname);
    return u.origin === APP_ORIGIN || GIRIS_ALANLARI.some((re) => re.test(u.hostname));
  } catch {
    return false;
  }
};
const gorselMi = (url) => /\/storage\/v1\/object\/public\//.test(url) || /\.(png|jpe?g|webp|svg)(\?|$)/i.test(url);

// E-postadaki giriş linki tarayıcıda açılır; Supabase oradan "dndasistani://giris?code=..." adresine yönlendirir,
// Windows da bu adresi uygulamaya verir. Kod, girişi başlatan pencerenin çerezleriyle oturuma çevrilir.
const PROTOKOL = "dndasistani";
if (process.defaultApp && process.argv[1]) {
  // `npm start` ile geliştirirken: electron.exe'ye uygulama klasörü de verilmeli.
  app.setAsDefaultProtocolClient(PROTOKOL, process.execPath, [path.resolve(process.argv[1])]);
} else {
  app.setAsDefaultProtocolClient(PROTOKOL);
}
const derinBaglanti = (argv) => argv.find((a) => a.startsWith(`${PROTOKOL}://`));
/** dndasistani://giris?code=...&next=/k/1 → https://site/auth/callback?code=...&next=/k/1 */
function girisAdresi(baglanti) {
  try {
    const u = new URL(baglanti);
    if (u.hostname !== "giris") return null;
    return `${APP_URL}/auth/callback${u.search}`;
  } catch {
    return null;
  }
}

// Tek kopya: ikinci kez açılınca (ya da giriş linki gelince) var olan pencere öne gelir.
if (!app.requestSingleInstanceLock()) app.quit();

const ayarDosyasi = () => path.join(app.getPath("userData"), "pencere.json");
function pencereAyari() {
  try {
    return JSON.parse(fs.readFileSync(ayarDosyasi(), "utf8"));
  } catch {
    return { width: 1440, height: 900 };
  }
}
function pencereAyariniKaydet(win) {
  const a = { ...win.getNormalBounds(), maximized: win.isMaximized(), fullscreen: win.isFullScreen() };
  try {
    fs.writeFileSync(ayarDosyasi(), JSON.stringify(a));
  } catch {
    // Kaydedilemezse bir dahaki açılış varsayılan boyutta olur, sorun değil.
  }
}

let anaPencere = null;

function anaPencereyiAc(ilkAdres = APP_URL) {
  const a = pencereAyari();
  const win = new BrowserWindow({
    x: a.x,
    y: a.y,
    width: a.width,
    height: a.height,
    minWidth: 900,
    minHeight: 600,
    title: "DnD Asistanı",
    icon: path.join(__dirname, "build", "icon.png"),
    backgroundColor: "#1c1410",
    autoHideMenuBar: true,
    show: false,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true },
  });
  anaPencere = win;
  win.setMenuBarVisibility(false);
  if (a.maximized) win.maximize();
  if (a.fullscreen) win.setFullScreen(true);
  win.once("ready-to-show", () => win.show());
  win.on("close", () => pencereAyariniKaydet(win));
  win.on("closed", () => (anaPencere = null));

  win.webContents.on("will-navigate", (e, url) => {
    if (!icerdeKalir(url)) {
      e.preventDefault();
      shell.openExternal(url);
    }
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    // "Büyük aç" görselleri uygulamanın içinde ayrı bir pencerede açılır.
    if (gorselMi(url)) {
      return {
        action: "allow",
        overrideBrowserWindowOptions: { autoHideMenuBar: true, backgroundColor: "#000000", title: "DnD Asistanı" },
      };
    }
    if (icerdeKalir(url)) {
      win.loadURL(url);
      return { action: "deny" };
    }
    shell.openExternal(url);
    return { action: "deny" };
  });

  // Site açılamazsa (internet yok, sunucu uykuda) beyaz ekran yerine açıklama ve "Tekrar dene".
  win.webContents.on("did-fail-load", (_e, kod, aciklama, url, anaCerceve) => {
    if (!anaCerceve || kod === -3) return; // -3: kullanıcı başka sayfaya geçti
    win.loadFile(path.join(__dirname, "yukleniyor.html"), { query: { hata: aciklama, adres: url || APP_URL } });
  });

  win.loadURL(ilkAdres);
  return win;
}

function menuKur() {
  const sablon = [
    {
      label: "Uygulama",
      submenu: [
        { label: "Ana sayfa", accelerator: "Alt+Home", click: () => anaPencere?.loadURL(APP_URL) },
        { label: "Çevrimdışı kayıtlar", click: () => anaPencere?.loadFile(path.join(__dirname, "cevrimdisi.html")) },
        { label: "Geri", accelerator: "Alt+Left", click: () => anaPencere?.webContents.navigationHistory.goBack() },
        { label: "İleri", accelerator: "Alt+Right", click: () => anaPencere?.webContents.navigationHistory.goForward() },
        { label: "Yenile", accelerator: "F5", role: "reload" },
        { label: "Yenile", accelerator: "CmdOrCtrl+R", role: "reload", visible: false },
        { type: "separator" },
        { label: "Tam ekran", accelerator: "F11", role: "togglefullscreen" },
        { label: "Yakınlaştır", accelerator: "CmdOrCtrl+=", role: "zoomIn" },
        { label: "Uzaklaştır", accelerator: "CmdOrCtrl+-", role: "zoomOut" },
        { label: "Gerçek boyut", accelerator: "CmdOrCtrl+0", role: "resetZoom" },
        { type: "separator" },
        {
          label: "Görsel önbelleğini temizle",
          click: async () => {
            await session.defaultSession.clearCache();
            dialog.showMessageBox({ message: "Önbellek temizlendi. Görseller bir sonraki açılışta yeniden indirilecek." });
          },
        },
        { label: "Geliştirici araçları", accelerator: "CmdOrCtrl+Shift+I", role: "toggleDevTools" },
        { type: "separator" },
        { label: "Çıkış", accelerator: "Alt+F4", role: "quit" },
      ],
    },
  ];
  // Menü çubuğu gizli kalır (Alt ile görünür); kısayollar yine de çalışır.
  Menu.setApplicationMenu(Menu.buildFromTemplate(sablon));
}

kurOnbellek(app);
kurCevrimdisi(APP_ORIGIN, () => anaPencere?.loadURL(APP_URL));

app.on("second-instance", (_e, argv) => {
  if (!anaPencere) return;
  const giris = girisAdresi(derinBaglanti(argv) ?? "");
  if (giris) anaPencere.loadURL(giris);
  if (anaPencere.isMinimized()) anaPencere.restore();
  anaPencere.focus();
});

app.whenReady().then(() => {
  menuKur();
  // Uygulama kapalıyken giriş linkine tıklandıysa adres komut satırında gelir.
  anaPencereyiAc(girisAdresi(derinBaglanti(process.argv) ?? "") ?? APP_URL);
  kurGuncelleme(() => anaPencere);
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) anaPencereyiAc();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
