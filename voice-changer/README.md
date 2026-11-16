# DnD Voice Changer

Mikrofonundaki sesi gerçek zamanlı değiştirip Discord'a gönderen küçük bir Windows uygulaması. DnD'de karakter sesleriyle RP yapmak için hazır karakterler, kendi karakterini kaydetme ve kısayol tuşları içerir.

```
Mikrofon ──► Voice Changer (efekt) ──► CABLE Input ══ VB-Cable ══► CABLE Output ──► Discord
```

## Kurulum

**Arkadaşların için (önerilen):** `DnDVoiceChanger_Setup_x.y.z.exe`'yi çalıştır. Kurulum, sanal mikrofonu (VB-CABLE) da kurar; bittiğinde bilgisayarı yeniden başlat. Python gerekmez.

**Geliştirme için:** Python 3.10+ kur, `baslat.bat`'a çift tıkla. VB-CABLE yoksa uygulamanın üstündeki **Sanal mikrofonu kur** butonu resmi paketi indirip kurulumu açar.

> VB-CABLE, VB-Audio Software'in bağışla desteklenen (donationware) ücretsiz bir ürünüdür: https://vb-cable.com. Kurulum dosyası resmi paketi değiştirmeden içerir.

## Kullanım

1. Uygulamada **Mikrofon**: kendi mikrofonun. **Çıkış**: `CABLE Input (VB-Audio Virtual Cable)` (otomatik seçilir).
2. Soldan bir **karakter** seç, **▶ Başlat**'a bas.
3. Discord → Kullanıcı Ayarları → **Ses ve Görüntü** → **Giriş Aygıtı**: `CABLE Output (VB-Audio Virtual Cable)`.
4. Discord'da şunları **kapat**, yoksa efekti bozarlar: *Gürültü Azaltma (Krisp)*, *Yankı Engelleme*. "Mikrofon Testi" ile sesini dinleyebilirsin.

## Oyun sırasında karakter değiştirme

**Ctrl+F1 … Ctrl+F12** listedeki ilk 12 karakteri seçer; Discord veya başka bir pencere öndeyken de çalışır.
Sıralamayı ▲ ▼ ile değiştirebilirsin: listedeki numara hangi F tuşu olduğunu gösterir. Ctrl+F1 varsayılan olarak **Normal** (kendi sesin).

## Kendi karakterini yap

1. Bir karaktere yakın olanı seç (örn. Cüce), sağdaki kaydırıcılarla ayarla. Değişiklikleri anında duyarsın ("Kendimi duy" ile).
2. **Yeni karakter olarak kaydet…** → ad ver (örn. "Bardın sesi"). Ya da **Kaydet** ile seçili karakterin üstüne yaz.
3. **Geri al** kaydetmediğin değişiklikleri siler. Başlıkta `*` görürsen kaydedilmemiş değişiklik var demektir.

Karakterler `%APPDATA%\DnD Voice Changer\presets.json` dosyasında durur; bu dosyayı arkadaşlarınla paylaşabilirsin. Silersen hazır karakterler geri gelir.

| Ayar | Ne işe yarar |
|---|---|
| Perde | Sesi kalınlaştırır (−) / inceltir (+) |
| Gırtlak / formant | Ses yolunun "boyutu". Perdeden düşük tutunca doğal kadın/erkek sesi, perdeye eşit olunca çizgi film/sincap sesi olur |
| Orijinal ses karışımı | Kaydırılmış sesin altına kendi sesini ekler: çift katmanlı, iblis/ejderha gibi |
| Hırıltı | Pürüz ve sertlik (ork, canavar) |
| Robot | Metalik ses (golem, yapay varlık) |
| Bas kes / Tiz kes | İnce-cılız ses için bası, boğuk ses için tizi keser |
| Titreme | Yaşlı, titrek ses |
| Reverb / Yankı | Mağara, salon, hayalet havası |

## Hazır karakterler

Kadın/erkek sesleri için perde ile birlikte formant da (ama daha az) kaydırılır; böylece "hızlandırılmış kaset" gibi değil, gerçek bir kadın/erkek gibi duyulur. Sesine göre Perde ve Gırtlak'ı 1-2 birim oynatman gerekebilir: kendi sesinle dene, beğendiğini kaydet.

Normal, Kadın, Erkek, Kalın erkek (bas), Kız çocuk, Erkek çocuk, Yaşlı kadın, Anlatıcı, Ejderha, Goblin, Cüce, Elf, Yaşlı büyücü, Ork, İblis, Hayalet, Peri, Golem / Robot.

## Sorun giderme

- **"Sanal mikrofon kurulu değil" uyarısı**: VB-CABLE kurulduktan sonra bilgisayarı yeniden başlat, sonra "Yenile"ye bas.
- **Başlatırken hata**: "Ses sürücüsü" listesinden başka birini dene (MME en uyumlusu, Windows WASAPI daha düşük gecikmeli).
- **Kısayollar çalışmıyor**: Başka bir program Ctrl+F tuşlarını kullanıyor olabilir; yönetici olarak açılan bir oyun öndeyken de çalışmayabilir.
- **Ses kesik kesik / cızırtılı**: MME'ye geç; ya da `app.py` içindeki `BLOCK = 512` değerini `1024` yap.
- **Kendi sesimi duymak istiyorum**: "Kendimi duy" kutusunu işaretleyip Başlat'a bas (varsayılan hoparlörden çalar, kulaklık kullan).
- **Discord'da ses gitmiyor**: Discord giriş aygıtı `CABLE Output` mu? Uygulamadaki seviye çubuğu konuşurken doluyor mu?

## Başka uygulamadan kontrol (DnD asistanı için)

Uygulama açıkken yalnızca bu bilgisayardan erişilebilen küçük bir API çalışır:

```
GET  http://127.0.0.1:47321/status            -> {"running":..., "preset":"...", "presets":[...]}
POST http://127.0.0.1:47321/preset/Ejderha     -> karaktere geç
POST http://127.0.0.1:47321/preset/index/2     -> listedeki 3. karaktere geç
```

Python'dan ses motorunu doğrudan da kullanabilirsin:

```python
from voicechanger import Engine
eng = Engine()
eng.start()                  # varsayılan mikrofon -> CABLE Input
eng.select_preset("Ejderha")
```

## Kurulum dosyasını derleme

- **GitHub:** `voice-changer/` değişip gönderilince "Ses değiştirici" iş akışı (`.github/workflows/ses-degistirici.yml`) kurulum dosyasını derler (Actions > ilgili çalışma > Artifacts). `ses-v1.0.0` gibi bir etiket gönderirsen Releases'e **ön sürüm** olarak koyar; DnD Asistanı'nın otomatik güncellemesi bundan etkilenmez.
- **Kendi bilgisayarında:** Python ve [Inno Setup 6](https://jrsoftware.org/isdl.php) kur, `build.bat`'ı çalıştır. Çıktı `dist\` klasörüne gelir.

## Dosyalar

- `voicechanger/engine.py`: ses motoru ve karakter deposu (arayüzden bağımsız)
- `voicechanger/effects.py`: efektler ve hazır karakterler
- `voicechanger/gui.py`: arayüz
- `voicechanger/control_server.py`: yerel API
- `voicechanger/vbcable.py`: VB-CABLE kontrolü ve kurulumu
- `packaging/`: PyInstaller ve Inno Setup dosyaları
- Karakterlerin `%APPDATA%\DnD Voice Changer\presets.json` dosyasında saklanır.
