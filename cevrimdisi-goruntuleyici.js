// Çevrimdışı görüntüleyici: site kampanyayı açtıkça diske yazdığı kopyayı (src/lib/offline.ts) salt okunur gösterir.
// Bütün metinler textContent ile yazılır; kopyadaki hiçbir şey HTML olarak yorumlanmaz.
const api = window.dndMasaustu;
const icerik = document.getElementById("icerik");
const esitleme = document.getElementById("esitleme");
const kampanyalarDugmesi = document.getElementById("kampanyalar");

function el(etiket, ozellik = {}, ...cocuklar) {
  const e = document.createElement(etiket);
  for (const [k, v] of Object.entries(ozellik)) {
    if (k === "text") e.textContent = v;
    else if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of cocuklar.flat()) if (c) e.append(c);
  return e;
}

const tarih = (iso) => new Date(iso).toLocaleString("tr-TR", { dateStyle: "medium", timeStyle: "short" });

// Görsel önbellekte yoksa (çok eski ya da hiç açılmamış) kırık resim yerine hiç gösterme.
function gorsel(src, sinif) {
  if (!src || !/^https:\/\//.test(src)) return null;
  const img = el("img", { src, class: sinif, alt: "" });
  img.addEventListener("error", () => img.remove());
  return img;
}

function bolumler(liste) {
  return liste.map((b) =>
    el(
      "section",
      {},
      b.title ? el("h3", { text: b.title }) : null,
      b.text ? el("div", { class: "metin", text: b.text }) : null,
      b.lines?.length ? el("ul", {}, b.lines.map((l) => el("li", { text: l }))) : null,
    ),
  );
}

function karakterSayfasi(s) {
  return el(
    "div",
    { class: "kart" },
    el("div", { class: "baslik" }, gorsel(s.portraitUrl, "portre"), el("div", {}, el("h2", { text: s.name }), el("div", { class: "soluk", text: s.subtitle }))),
    el("div", { class: "degerler" }, s.stats.map((x) => el("div", { class: "deger" }, el("b", { text: x.value }), el("span", { text: x.label })))),
    el(
      "div",
      { class: "yetenekler" },
      s.abilities.map((a) =>
        el(
          "div",
          { class: "deger" },
          el("span", { text: a.label }),
          el("b", { text: a.mod }),
          el("span", { text: `${a.score} · kurtarma ${a.save}${a.saveProf ? " ●" : ""}` }),
        ),
      ),
    ),
    el("h3", { text: "Beceriler" }),
    el("div", { class: "beceriler" }, s.skills.map((x) => el("div", { class: x.prof ? "yeterli" : "", text: `${x.prof ? "● " : "○ "}${x.label} ${x.bonus}` }))),
    bolumler(s.sections),
  );
}

function kayitSayfasi(k) {
  return el(
    "div",
    { class: "kart" },
    k.wide ? null : gorsel(k.imageUrl, "gorsel"),
    el("h2", { text: k.title }),
    k.subtitle ? el("div", { class: "soluk", text: k.subtitle }) : null,
    k.wide ? gorsel(k.imageUrl, "genis") : null,
    bolumler(k.sections),
    el("div", { style: "clear: both" }),
  );
}

/** Solda aranabilir liste, sağda seçilen kayıt. */
function listeliGorunum(ogeler, grupla, ciz) {
  let secili = ogeler[0];
  let arama = "";
  const listeKutusu = el("div", { class: "kart liste" });
  const sag = el("div");
  const giris = el("input", { placeholder: "Ara...", oninput: (e) => ((arama = e.target.value.toLocaleLowerCase("tr")), listele()) });

  function listele() {
    listeKutusu.replaceChildren(giris);
    let sonGrup = null;
    for (const o of ogeler.filter((o) => !arama || JSON.stringify(o).toLocaleLowerCase("tr").includes(arama))) {
      const g = grupla(o);
      if (g && g !== sonGrup) listeKutusu.append(el("div", { class: "grup", text: (sonGrup = g) }));
      listeKutusu.append(el("button", { class: `oge${o === secili ? " secili" : ""}`, text: o.title ?? o.name, onclick: () => ((secili = o), listele(), goster()) }));
    }
  }
  function goster() {
    sag.replaceChildren(secili ? ciz(secili) : el("p", { class: "soluk", text: "Kayıt yok." }));
  }
  listele();
  goster();
  return el("div", { class: "duzen" }, listeKutusu, sag);
}

const GRUP_SIRASI = ["Kahramanlar", "Kişiler", "Şehir", "Yer", "Tanrı", "Fraksiyon", "Tarih", "Diğer", "Eşyalar", "Seanslar"];
const grupSirasi = (g) => (GRUP_SIRASI.indexOf(g) + 1 || 99);

async function kampanyayiAc(id) {
  const k = await api.cevrimdisiOku(id);
  if (!k) return kampanyaListesi();
  esitleme.textContent = `Son eşitleme: ${tarih(k.savedAt)}`;
  const kayitlar = [...k.entries].sort((a, b) => grupSirasi(a.group) - grupSirasi(b.group) || a.title.localeCompare(b.title, "tr"));
  const sekmeler = [
    { ad: `Karakterler (${k.sheets.length})`, ciz: () => (k.sheets.length ? listeliGorunum(k.sheets, () => null, karakterSayfasi) : bos("Bu kampanyada kaydedilmiş karakter sayfası yok.")) },
    { ad: `Ansiklopedi (${kayitlar.length})`, ciz: () => (kayitlar.length ? listeliGorunum(kayitlar, (o) => o.group, kayitSayfasi) : bos("Ansiklopedi boş.")) },
    // Tarih kitabı, miras, haritalar... (kopyada ne varsa; sıralama siteden gelir)
    ...(k.tabs ?? []).map((t) => ({ ad: `${t.title} (${t.entries.length})`, ciz: () => listeliGorunum(t.entries, (o) => o.group, kayitSayfasi) })),
  ];
  let aktif = 0;
  const govde = el("div");
  const dugmeler = el("div", { class: "sekmeler" });
  const ciz = () => {
    dugmeler.replaceChildren(...sekmeler.map((s, i) => el("button", { class: i === aktif ? "secili" : "", text: s.ad, onclick: () => ((aktif = i), ciz()) })));
    govde.replaceChildren(sekmeler[aktif].ciz());
  };
  ciz();
  icerik.replaceChildren(el("h1", { text: `${k.campaign.name}${k.campaign.isDm ? " · DM" : ""}` }), dugmeler, govde);
}

const bos = (metin) => el("div", { class: "kart bos soluk", text: metin });

async function kampanyaListesi() {
  esitleme.textContent = "";
  const liste = await api.cevrimdisiListe();
  kampanyalarDugmesi.hidden = liste.length < 2;
  if (liste.length === 1) return kampanyayiAc(liste[0].id);
  icerik.replaceChildren(
    el("h1", { text: "Kayıtlı kampanyalar" }),
    liste.length
      ? el(
          "div",
          { class: "kampanyalar" },
          liste.map((k) =>
            el(
              "div",
              { class: "kart", onclick: () => kampanyayiAc(k.id) },
              el("h2", { text: k.name }),
              el("div", { class: "soluk", text: `${k.isDm ? "DM · " : ""}${k.sheets} karakter · ${k.entries} kayıt` }),
              el("div", { class: "soluk", text: `Son eşitleme: ${tarih(k.savedAt)}` }),
            ),
          ),
        )
      : bos("Henüz kayıtlı kampanya yok. İnternet varken bir kampanyayı açınca karakterler ve ansiklopedi buraya kaydedilir."),
  );
}

document.getElementById("baglan").addEventListener("click", () => api.siteyiAc());
kampanyalarDugmesi.addEventListener("click", kampanyaListesi);
addEventListener("online", () => (esitleme.textContent = "İnternet geri geldi; \"Tekrar bağlan\"a basabilirsin."));
kampanyaListesi();
