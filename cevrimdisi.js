// Çevrimdışı kopyaların saklanması: %APPDATA%\DnD Asistanı\cevrimdisi\<kampanya-id>.json
const { app, ipcMain } = require("electron");
const fs = require("node:fs/promises");
const path = require("node:path");

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const EN_FAZLA = 30 * 1024 * 1024;
const klasor = () => path.join(app.getPath("userData"), "cevrimdisi");

/** siteOrigin: kopyayı yazabilen tek adres; okuma sadece uygulamanın içindeki dosya sayfalarından. */
function kurCevrimdisi(siteOrigin, siteyiAc) {
  const siteden = (e) => {
    try {
      return new URL(e.senderFrame.url).origin === siteOrigin;
    } catch {
      return false;
    }
  };
  const uygulamadan = (e) => e.senderFrame?.url.startsWith("file://");

  ipcMain.handle("cevrimdisi:kaydet", async (e, kopya) => {
    if (!siteden(e) || !UUID.test(kopya?.campaign?.id ?? "")) return;
    const json = JSON.stringify(kopya);
    if (json.length > EN_FAZLA) return;
    await fs.mkdir(klasor(), { recursive: true });
    // Önce geçici dosyaya: yazarken kapanırsa eski kopya bozulmaz.
    const hedef = path.join(klasor(), `${kopya.campaign.id}.json`);
    await fs.writeFile(`${hedef}.tmp`, json);
    await fs.rename(`${hedef}.tmp`, hedef);
  });

  ipcMain.handle("cevrimdisi:liste", async (e) => {
    if (!uygulamadan(e)) return [];
    const adlar = await fs.readdir(klasor()).catch(() => []);
    const liste = [];
    for (const ad of adlar.filter((a) => a.endsWith(".json"))) {
      try {
        const k = JSON.parse(await fs.readFile(path.join(klasor(), ad), "utf8"));
        liste.push({ ...k.campaign, savedAt: k.savedAt, sheets: k.sheets.length, entries: k.entries.length });
      } catch {
        // bozuk kopya: atla
      }
    }
    return liste.sort((a, b) => b.savedAt.localeCompare(a.savedAt));
  });

  ipcMain.handle("cevrimdisi:oku", async (e, id) => {
    if (!uygulamadan(e) || !UUID.test(id ?? "")) return null;
    return JSON.parse(await fs.readFile(path.join(klasor(), `${id}.json`), "utf8"));
  });

  ipcMain.handle("site:ac", (e) => {
    if (uygulamadan(e)) siteyiAc();
  });
}

module.exports = { kurCevrimdisi };
