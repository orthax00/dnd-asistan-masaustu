// Site, masaüstü uygulamasında açıldığını buradan anlar; çevrimdışı mod da kopyayı bu köprüyle yazar ve okur.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("dndMasaustu", {
  masaustu: true,
  platform: process.platform,
  // 1.1.0+: e-postadaki giriş linki bu adrese döner ve uygulamayı açar.
  girisBaglantisi: "dndasistani://giris",
  // 1.1.0+: çevrimdışı mod. Kaydetmeyi sadece site, okumayı sadece uygulamanın kendi sayfaları yapabilir (main.js denetler).
  cevrimdisiKaydet: (kopya) => ipcRenderer.invoke("cevrimdisi:kaydet", kopya),
  cevrimdisiListe: () => ipcRenderer.invoke("cevrimdisi:liste"),
  cevrimdisiOku: (id) => ipcRenderer.invoke("cevrimdisi:oku", id),
  siteyiAc: () => ipcRenderer.invoke("site:ac"),
});
