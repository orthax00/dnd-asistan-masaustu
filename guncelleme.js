// Otomatik güncelleme: açılışta ve her 4 saatte bir yeni sürüme bakar, varsa arka planda indirir ve
// "Yeniden başlat ve güncelle" diye sorar. Kurulum dosyaları herkese açık orthax00/dnd-asistan-masaustu
// deposunun Release'lerinden gelir (ana depo gizli, oradan anahtarsız indirilemez).
const { app, dialog } = require("electron");
const { autoUpdater } = require("electron-updater");

const ARALIK = 4 * 60 * 60 * 1000;

function kurGuncelleme(pencere) {
  if (!app.isPackaged) return; // `npm start` ile geliştirirken güncelleme yok
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true; // "Sonra" denirse uygulama kapanınca kurulur
  let soruldu = false;

  autoUpdater.on("update-downloaded", async (bilgi) => {
    if (soruldu) return;
    soruldu = true;
    const { response } = await dialog.showMessageBox(pencere(), {
      type: "info",
      buttons: ["Yeniden başlat ve güncelle", "Sonra"],
      defaultId: 0,
      cancelId: 1,
      title: "DnD Asistanı",
      message: `Yeni sürüm hazır (${bilgi.version}).`,
      detail: "Şimdi yeniden başlatabilirsin; \"Sonra\" dersen uygulamayı kapattığında kendiliğinden kurulur.",
    });
    if (response === 0) autoUpdater.quitAndInstall();
  });
  // İnternet yoksa ya da depo erişilemezse sessizce geçer; bir dahaki denemede tekrar bakar.
  autoUpdater.on("error", () => {});

  const bak = () => autoUpdater.checkForUpdates().catch(() => {});
  bak();
  setInterval(bak, ARALIK);
}

module.exports = { kurGuncelleme };
