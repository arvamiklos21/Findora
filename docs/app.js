// ===== Beállítások – éles Findora feedek használata =====
const FEEDS_BASE = "";
const PARTNERS_URL = FEEDS_BASE + "/feeds/partners.json";

// Mobil detektálás – kisebb terhelés mobilon
const IS_MOBILE =
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(max-width: 768px)").matches;

const PARTNERS = new Map();
const META = new Map();
const PAGES = new Map();

// Deeplink építése – minden gomb: Megnézem🔗
function dlUrl(partnerId, rawUrl) {
  if (!rawUrl) return "#";
  return (
    FEEDS_BASE +
    "/api/dl?u=" +
    encodeURIComponent(rawUrl) +
    "&p=" +
    partnerId
  );
}

// ===== Kisegítő függvények =====
function priceText(v) {
  if (typeof v === "number" && isFinite(v)) {
    return v.toLocaleString("hu-HU") + " Ft";
  }
  if (typeof v === "string" && v.trim()) return v;
  return "—";
}

function itemUrl(it) {
  return (it && (it.url || it.link || it.deeplink)) || "";
}

function itemImg(it) {
  return (it && (it.image || it.img || it.image_link || it.thumbnail)) || "";
}

function basePath(u) {
  try {
    const x = new URL(u);
    return x.origin + x.pathname;
  } catch (_) {
    return String(u || "").split("#")[0].split("?")[0];
  }
}

function imgPath(u) {
  return String(u || "").split("#")[0].split("?")[0];
}

// Méret / szín variánsok erős deduplikálása
const SIZE_TOKENS = new RegExp(
  [
    "\\b(?:XXS|XS|S|M|L|XL|XXL|3XL|4XL|5XL)\\b",
    "\\b(?:\\d{2,3}[\\/-]\\d{2,3})\\b",
    "\\bEU\\s?\\d{2,3}\\b",
    "[\\(\\[]\\s*(?:XXS|XS|S|M|L|XL|XXL|3XL|4XL|5XL|EU\\s?\\d{2,3}|\\d{2,3}[\\/-]\\d{2,3})\\s*[\\)\\]]",
    "\\b(?:méret|meret)\\b\\s*[:\\-]?\\s*[A-Za-z0-9\\/-]+",
  ].join("|"),
  "gi"
);

function normalizeTitleNoSize(t) {
  if (!t) return "";
  return String(t)
    .replace(SIZE_TOKENS, " ")
    .replace(
      /\b(?:szín|szin|color)\s*[:\-]?\s*[a-záéíóöőúüű0-9\-]+/gi,
      " "
    )
    .replace(/\s{2,}/g, " ")
    .trim()
    .toLowerCase();
}

function stripVariantParams(u) {
  if (!u) return u;
  try {
    const x = new URL(u);
    const drop = [
      "size",
      "meret",
      "merete",
      "variant_size",
      "size_id",
      "meret_id",
      "option",
      "variant",
    ];
    for (const k of Array.from(x.searchParams.keys())) {
      if (drop.indexOf(k.toLowerCase()) > -1) x.searchParams.delete(k);
    }
    return x.toString();
  } catch (_) {
    return u;
  }
}

function dedupeStrong(items) {
  const out = [];
  const seen = new Set();
  (items || []).forEach((it) => {
    const raw = itemUrl(it);
    const key =
      basePath(stripVariantParams(raw)) +
      "|" +
      imgPath(itemImg(it)) +
      "|" +
      normalizeTitleNoSize(it && it.title);
    if (!seen.has(key)) {
      seen.add(key);
      out.push(it);
    }
  });
  return out;
}

// ===== Diszkont százalék kinyerése =====
function getDiscountNumber(it) {
  if (it && typeof it.discount === "number" && isFinite(it.discount)) {
    const d = Math.round(it.discount);
    if (d >= 5 && d <= 90) return d;
  }

  const txt =
    ((it && it.title ? it.title : "") +
      " " +
      (it && it.desc ? it.desc : "")).toLowerCase();

  const m = txt.match(/-\s?(\d{1,3})\s?%/);
  if (!m) return null;

  const d = parseInt(m[1], 10);
  if (!Number.isFinite(d)) return null;
  if (d < 5 || d > 90) return null;

  return d;
}

// ===== partners.json, meta, page betöltés =====
async function loadPartners() {
  const r = await fetch(PARTNERS_URL, { cache: "no-cache" });
  if (!r.ok) throw new Error("partners.json nem elérhető: " + r.status);
  const arr = await r.json();
  if (!Array.isArray(arr) || !arr.length) {
    throw new Error("partners.json üres vagy hibás");
  }
  PARTNERS.clear();
  arr.forEach((p) => {
    if (!p.id || !p.meta || !p.pagePattern || !p.deeplinkPartner) return;
    PARTNERS.set(p.id, p);
  });
  console.log("PARTNEREK BETÖLTVE:", PARTNERS.size);
}

async function getMeta(pid) {
  if (META.has(pid)) return META.get(pid);
  const cfg = PARTNERS.get(pid);
  if (!cfg) throw new Error("ismeretlen partner: " + pid);
  const r = await fetch(FEEDS_BASE + "/" + cfg.meta, { cache: "no-cache" });
  if (!r.ok) throw new Error(pid + " meta.json nem elérhető");
  const m = await r.json();
  META.set(pid, m);
  return m;
}

function pageUrl(cfg, n) {
  return (
    FEEDS_BASE +
    "/" +
    cfg.pagePattern.replace("{NNNN}", String(n).padStart(4, "0"))
  );
}

async function getPageItems(pid, pageNum) {
  if (!PAGES.has(pid)) PAGES.set(pid, new Map());
  const store = PAGES.get(pid);
  const key = "page-" + String(pageNum).padStart(4, "0");
  if (store.has(key)) return store.get(key);

  const cfg = PARTNERS.get(pid);
  const r = await fetch(pageUrl(cfg, pageNum), { cache: "no-cache" });
  if (!r.ok) throw new Error(pid + " " + key + " nem elérhető");
  const d = await r.json();
  const arr = d && d.items ? d.items : [];
  store.set(key, arr);
  return arr;
}

// ===== Partner-alapú bázis kategória hozzárendelés =====
const BASE_CATEGORY_BY_PARTNER = {
  tchibo: "kat-otthon",
  "cj-karcher": "kat-kert",
  "cj-eoptika": "kat-latas",
  "cj-jateknet": "kat-jatekok",
  jateksziget: "kat-jatekok",
  regiojatek: "kat-jatekok",
  decathlon: "kat-sport",
  alza: "kat-elektronika",
  kozmetikaotthon: "kat-szepseg",
  // Pepita: ne kényszerítsük utazásba, mert vegyes áruházi termékek
  pepita: "kat-multi",
  ekszereshop: "kat-szepseg",
  karacsonydekor: "kat-otthon",
  otthonmarket: "kat-otthon",
  onlinemarkabolt: "kat-elektronika",
};

function baseCategoryForPartner(pid, cfg) {
  if (BASE_CATEGORY_BY_PARTNER[pid]) return BASE_CATEGORY_BY_PARTNER[pid];

  const g = (cfg && cfg.group) || "";
  switch (g) {
    case "games":
      return "kat-jatekok";
    case "vision":
      return "kat-latas";
    case "sport":
      return "kat-sport";
    case "tech":
      return "kat-elektronika";
    case "otthon":
      return "kat-otthon";
    case "travel":
      return "kat-utazas";
    default:
      return "kat-multi";
  }
}

// ===== Kategória meghatározás egy termékre =====
function getCategoriesForItem(pid, it) {
  const cfg = PARTNERS.get(pid) || {};
  let cat = baseCategoryForPartner(pid, cfg);

  const text = (
    (it && it.title ? it.title : "") +
    " " +
    (it && it.desc ? it.desc : "")
  ).toLowerCase();

  const hasAny = (words) => words.some((w) => text.includes(w));

  // Divat / cipő – bővített lista, hogy a Tchibo cipők ne az Otthonban landoljanak
  const divatWords = [
    "alsó",
    "alsónemű",
    "alsonemu",
    "bugyi",
    "melltartó",
    "melltarto",
    "fehérnemű",
    "fehernemu",
    "pizsama",
    "hálóing",
    "haloing",
    "köntös",
    "kontos",
    "zokni",
    "harisnya",
    "leggings",
    "top",
    "póló",
    "polo",
    "pulóver",
    "pulover",
    "ruha",
    "szoknya",
    "blúz",
    "bluz",
    "kabát",
    "kabat",
    "dzseki",
    "ing",
    "farmernadrág",
    "farmernadrag",
    // cipő-specifikus
    "cipő",
    "cipo",
    "sportcipő",
    "sportcipo",
    "edzőcipő",
    "edzocipo",
    "sneaker",
    "sneakers",
    "csizma",
    "bakancs",
    "félcipő",
    "felcipo",
    "szandál",
    "szandal",
    "papucs",
    "mokaszin",
    "mokasszin",
    "loafer",
    "shoe",
    "shoes",
    "boot",
    "boots",
  ];

  // Háztartási gép kulcsszavak
  const gepekWords = [
    "mosógép",
    "mosogep",
    "mosogatógép",
    "mosogatogep",
    "mosó-szárító",
    "moso-szarito",
    "hűtőszekrény",
    "hutoszekreny",
    "fagyasztó",
    "fagyaszto",
    "sütő",
    "sutő",
    "tűzhely",
    "tuzhely",
    "mikrohullámú",
    "mikro",
    "mikrohullamu",
    "porszívó",
    "porszivo",
    "robotporszívó",
    "robotporszivo",
    "gőztisztító",
    "goztisztito",
    "kávéfőző",
    "kavefozo",
    "turmix",
    "botmixer",
    "konyhagép",
    "konyhagep",
    "mosogatógép",
  ];

  // Kerti eszközök
  const kertWords = [
    "kert",
    "kerti",
    "locsoló",
    "locsolo",
    "slag",
    "fűnyíró",
    "funyiro",
    "fűkasza",
    "fukasza",
    "láncfűrész",
    "lancfuresz",
    "metszőolló",
    "metszoollo",
    "gereblye",
    "ásó",
    "aso",
    "lapát",
    "lapat",
    "kerti szerszám",
    "magasnyomású mosó",
    "magasnyomasu moso",
  ];

  // Utazás jellegű szavak – ha nincs ilyen, ne tegyük kat-utazasba
  const travelWords = [
    "szállás",
    "szallas",
    "hotel",
    "panzió",
    "panzio",
    "repülőjegy",
    "repulojegy",
    "buszjegy",
    "vonatjegy",
    "utazási csomag",
    "utazasi csomag",
    "nyaralás",
    "nyaralas",
    "üdülés",
    "udules",
    "hajóút",
    "hajout",
    "körutazás",
    "korutazas",
  ];

  // Finomítás otthon jellegű partnereknél
  if (cat === "kat-otthon" || cat === "kat-multi") {
    if (hasAny(divatWords)) {
      cat = "kat-divat";
    } else if (hasAny(gepekWords)) {
      cat = "kat-gepek";
    } else if (hasAny(kertWords)) {
      cat = "kat-kert";
    }
  }

  // Elektronika partnerek: nagy gép → kat-gepek
  if (cat === "kat-elektronika") {
    if (hasAny(gepekWords)) {
      cat = "kat-gepek";
    }
  }

  // Utazás: csak akkor maradjon, ha tényleg utazás jellegű
  if (cat === "kat-utazas" && !hasAny(travelWords)) {
    cat = "kat-multi";
  }

  if (!cat) cat = "kat-multi";
  return [cat];
}

// ===== Akciós blokk =====
let AKCIO_PAGES = [];
let AKCIO_CURRENT = 1;

function renderAkcioCards(itemsWithPartner) {
  const list = itemsWithPartner || [];
  if (!list.length) {
    return '<div class="empty">Jelenleg nem találtunk akciós ajánlatot.</div>';
  }
  return list
    .map((row) => {
      const { pid, item } = row;
      const cfg = PARTNERS.get(pid);
      const raw = itemUrl(item);
      const img = itemImg(item);
      const price = priceText(item && item.price);
      const disc = getDiscountNumber(item);
      const partnerName = (cfg && cfg.name) || pid;

      return (
        '<div class="card">' +
        '<div class="thumb">' +
        (img
          ? '<img src="' +
            img +
            '" alt="" loading="lazy" decoding="async" style="max-width:100%;max-height:100%;object-fit:contain">'
          : "🛍️") +
        "</div>" +
        '<div class="title">' +
        (item && item.title ? item.title : "") +
        "</div>" +
        '<div class="price">' +
        price +
        (disc ? " (-" + disc + "%)" : "") +
        "</div>" +
        '<div class="partner">• ' +
        partnerName +
        "</div>" +
        (raw
          ? '<a class="btn-megnez akcios" href="' +
            dlUrl(cfg ? cfg.deeplinkPartner : pid, raw) +
            '" target="_blank" rel="nofollow sponsored noopener noreferrer">Megnézem🔗</a>'
          : "") +
        "</div>"
      );
    })
    .join("");
}

function renderAkcioPage(page) {
  const grid = document.getElementById("akciok-grid");
  const nav = document.getElementById("akciok-nav");
  if (!grid || !nav) return;

  if (!AKCIO_PAGES.length) {
    grid.innerHTML =
      '<div class="empty">Jelenleg nem találtunk akciós ajánlatot.</div>';
    nav.innerHTML = "";
    return;
  }

  if (page < 1) page = 1;
  if (page > AKCIO_PAGES.length) page = AKCIO_PAGES.length;
  AKCIO_CURRENT = page;

  grid.innerHTML = renderAkcioCards(AKCIO_PAGES[page - 1]);

  nav.innerHTML =
    '<button class="btn-megnez" ' +
    (page <= 1 ? "disabled" : "") +
    ' onclick="window.akciokPager && window.akciokPager.go(' +
    (page - 1) +
    ')">Előző</button>' +
    '<span style="align-self:center;font-size:13px;margin:0 8px;">' +
    page +
    "/" +
    AKCIO_PAGES.length +
    "</span>" +
    '<button class="btn-megnez" ' +
    (page >= AKCIO_PAGES.length ? "disabled" : "") +
    ' onclick="window.akciokPager && window.akciokPager.go(' +
    (page + 1) +
    ')">Következő</button>';

  window.akciokPager = {
    go: function (p) {
      renderAkcioPage(p);
    },
  };
}

async function buildAkciosBlokk() {
  const host = document.getElementById("akciok-grid");
  if (!host) return;
  try {
    host.innerHTML =
      '<div class="card"><div class="thumb">⏳</div><div class="title">Akciók betöltése…</div></div>';
    const nav = document.getElementById("akciok-nav");
    if (nav) nav.innerHTML = "";

    const collected = [];
    const scanPagesMax = IS_MOBILE ? 1 : 2;

    for (const [pid, cfg] of PARTNERS.entries()) {
      const plc = cfg.placements || {};
      const anyEnabled = Object.keys(plc).some((k) => {
        const v = plc[k];
        return (v && v.enabled) || (v && v.full && v.full.enabled);
      });
      if (!anyEnabled) continue;

      const meta = await getMeta(pid);
      const pageSize = meta.pageSize || 300;
      const totalPages =
        meta.pages || Math.ceil((meta.total || 0) / pageSize) || 1;
      const scanPages = Math.min(scanPagesMax, totalPages);

      for (let pg = 1; pg <= scanPages; pg++) {
        const arr = await getPageItems(pid, pg);
        for (const it of arr) {
          const d = getDiscountNumber(it);
          if (d !== null && d >= 10) {
            collected.push({ pid, item: it });
          }
        }
      }
    }

    const dedItems = dedupeStrong(collected.map((r) => r.item));
    const backMap = new Map();
    collected.forEach((r) => {
      const raw = itemUrl(r.item);
      if (!raw) return;
      const key =
        basePath(stripVariantParams(raw)) +
        "|" +
        imgPath(itemImg(r.item)) +
        "|" +
        normalizeTitleNoSize(r.item.title || "");
      if (!backMap.has(key)) backMap.set(key, r.pid);
    });

    const merged = dedItems
      .map((it) => {
        const raw = itemUrl(it);
        const key =
          basePath(stripVariantParams(raw)) +
          "|" +
          imgPath(itemImg(it)) +
          "|" +
          normalizeTitleNoSize(it.title || "");
        const pid = backMap.get(key) || "unknown";
        return { pid, item: it };
      })
      .sort((a, b) => {
        const da = getDiscountNumber(a.item) || 0;
        const db = getDiscountNumber(b.item) || 0;
        return db - da;
      });

    // Mobilon kevesebb akciót tartunk meg
    const MAX_RESULTS = IS_MOBILE ? 60 : 120;
    const limited = merged.slice(0, MAX_RESULTS);

    const PAGE_SIZE = 12;
    AKCIO_PAGES = [];
    for (let i = 0; i < limited.length; i += PAGE_SIZE) {
      AKCIO_PAGES.push(limited.slice(i, i + PAGE_SIZE));
    }

    renderAkcioPage(1);
  } catch (e) {
    console.error("Akciós blokk hiba:", e);
    host.innerHTML =
      '<div class="empty">Hiba történt az akciók betöltése közben.</div>';
    const nav = document.getElementById("akciok-nav");
    if (nav) nav.innerHTML = "";
  }
}

// ===== KATEGÓRIA BLOKKOK – partnerenként lapozható =====
const CATEGORY_IDS = [
  "kat-elektronika",
  "kat-gepek",
  "kat-otthon",
  "kat-kert",
  "kat-jatekok",
  "kat-divat",
  "kat-szepseg",
  "kat-sport",
  "kat-latas",
  "kat-allatok",
  "kat-konyv",
  "kat-utazas",
  "kat-multi",
];

// catId -> { pid -> [ [ {pid,item}, ... ], ... ] }
const CATEGORY_PAGES = {};
// catId -> { pid -> currentPage }
const CATEGORY_CURRENT = {};
window.catPager = window.catPager || {};

// Partner + kategória mátrix a partner-nézethez
const PARTNER_CATEGORY_ITEMS = {};
const PARTNER_CATEGORY_LOAD_PROMISES = {};

// Partner nézet állapot
let PARTNER_VIEW_STATE = {
  pid: null,
  catId: null,
  items: [],
  filtered: [],
  page: 1,
  pageSize: 20,
  sort: "default",
  query: "",
  loading: false,
};

function getPartnerName(pid) {
  const cfg = PARTNERS.get(pid);
  return (cfg && cfg.name) || pid;
}

function getCategoryName(catId) {
  const el = document.querySelector("#" + catId + " .section-header h2");
  return el ? el.textContent.trim() : "";
}

// Kártyák renderelése (általános)
function renderCategoryCards(itemsWithPartner, catId, showPartnerRow) {
  const list = itemsWithPartner || [];
  if (!list.length) {
    return '<div class="empty">Jelenleg nincs termék ebben a kategóriában.</div>';
  }
  return list
    .map((row) => {
      const { pid, item } = row;
      const cfg = PARTNERS.get(pid);
      const raw = itemUrl(item);
      const img = itemImg(item);
      const price = priceText(item && item.price);
      const disc = getDiscountNumber(item);

      let partnerRowHtml = "";
      if (showPartnerRow) {
        const partnerName = getPartnerName(pid);
        partnerRowHtml = '<div class="partner">• ' + partnerName + "</div>";
      }

      return (
        '<div class="card">' +
        '<div class="thumb">' +
        (img
          ? '<img src="' +
            img +
            '" alt="" loading="lazy" decoding="async" style="max-width:100%;max-height:100%;object-fit:contain">'
          : "🛍️") +
        "</div>" +
        '<div class="title">' +
        (item && item.title ? item.title : "") +
        "</div>" +
        '<div class="price">' +
        price +
        (disc ? " (-" + disc + "%)" : "") +
        "</div>" +
        partnerRowHtml +
        (raw
          ? '<a class="btn-megnez" href="' +
            dlUrl(cfg ? cfg.deeplinkPartner : pid, raw) +
            '" target="_blank" rel="nofollow sponsored noopener noreferrer">Megnézem🔗</a>'
          : "") +
        "</div>"
      );
    })
    .join("");
}

// Kategória renderelése: partnerenként külön blokk, saját nav
function renderCategory(catId) {
  const grid = document.getElementById(catId + "-grid");
  const nav = document.getElementById(catId + "-nav");
  if (!grid || !nav) return;

  const byPartner = CATEGORY_PAGES[catId] || {};
  const partnerIds = Object.keys(byPartner);

  if (!partnerIds.length) {
    grid.innerHTML =
      '<div class="empty">Jelenleg nincs termék ebben a kategóriában.</div>';
    nav.innerHTML = "";
    return;
  }

  const catName = getCategoryName(catId);
  let html = "";

  partnerIds.forEach((pid) => {
    const pages = byPartner[pid] || [];
    if (!pages.length) return;

    const currentMap = CATEGORY_CURRENT[catId] || {};
    let currentPage = currentMap[pid] || 1;
    if (currentPage < 1) currentPage = 1;
    if (currentPage > pages.length) currentPage = pages.length;
    currentMap[pid] = currentPage;
    CATEGORY_CURRENT[catId] = currentMap;

    const items = pages[currentPage - 1] || [];
    const partnerName = getPartnerName(pid);
    const titleText = partnerName + (catName ? " – " + catName : "");

    html +=
      '<div class="partner-block" data-partner="' +
      pid +
      '" data-cat="' +
      catId +
      '">' +
      '<div class="partner-block-header">' +
      '<button type="button" class="partner-block-title" data-partner="' +
      pid +
      '" data-cat="' +
      catId +
      '">' +
      titleText +
      "</button>" +
      "</div>" +
      '<div class="grid partner-block-grid">' +
      renderCategoryCards(items, catId, false) +
      "</div>" +
      '<div class="partner-block-nav">' +
      '<button class="btn-megnez" ' +
      (currentPage <= 1 ? "disabled" : "") +
      ' data-cat="' +
      catId +
      '" data-partner="' +
      pid +
      '" data-partner-page="' +
      (currentPage - 1) +
      '">Előző</button>' +
      '<span style="align-self:center;font-size:13px;margin:0 8px;">' +
      currentPage +
      "/" +
      pages.length +
      "</span>" +
      '<button class="btn-megnez" ' +
      (currentPage >= pages.length ? "disabled" : "") +
      ' data-cat="' +
      catId +
      '" data-partner="' +
      pid +
      '" data-partner-page="' +
      (currentPage + 1) +
      '">Következő</button>' +
      "</div>" +
      "</div>";
  });

  grid.innerHTML = html;
  nav.innerHTML = ""; // kategória szintű lapozó nem kell
}

async function buildCategoryBlocks() {
  // buffers: catId -> pid -> [ {pid,item}, ... ]
  const buffers = {};
  const scanPagesMax = IS_MOBILE ? 1 : 2;

  for (const [pid, cfg] of PARTNERS.entries()) {
    const plc = cfg.placements || {};
    const anyEnabled = Object.keys(plc).some((k) => {
      const v = plc[k];
      return (v && v.enabled) || (v && v.full && v.full.enabled);
    });
    if (!anyEnabled) continue;

    const meta = await getMeta(pid);
    const pageSize = meta.pageSize || 300;
    const totalPages =
      meta.pages || Math.ceil((meta.total || 0) / pageSize) || 1;
    const scanPages = Math.min(scanPagesMax, totalPages);

    for (let pg = 1; pg <= scanPages; pg++) {
      const arr = await getPageItems(pid, pg);
      for (const it of arr) {
        const cats = getCategoriesForItem(pid, it) || [];
        cats.forEach((catId) => {
          if (!buffers[catId]) buffers[catId] = {};
          if (!buffers[catId][pid]) buffers[catId][pid] = [];
          buffers[catId][pid].push({ pid, item: it });

          if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};
          if (!PARTNER_CATEGORY_ITEMS[pid][catId])
            PARTNER_CATEGORY_ITEMS[pid][catId] = [];
          PARTNER_CATEGORY_ITEMS[pid][catId].push({ pid, item: it });
        });
      }
    }
  }

  const PAGE_SIZE = IS_MOBILE ? 3 : 6;

  CATEGORY_IDS.forEach((catId) => {
    const byPartner = buffers[catId] || {};
    const partnerIds = Object.keys(byPartner);

    const catPages = {};
    const catCurrent = {};

    partnerIds.forEach((pid) => {
      const list = byPartner[pid] || [];
      const pages = [];
      for (let i = 0; i < list.length; i += PAGE_SIZE) {
        pages.push(list.slice(i, i + PAGE_SIZE));
      }
      catPages[pid] = pages;
      catCurrent[pid] = pages.length ? 1 : 0;
    });

    CATEGORY_PAGES[catId] = catPages;
    CATEGORY_CURRENT[catId] = catCurrent;

    if (partnerIds.length) {
      renderCategory(catId);
    } else {
      const grid = document.getElementById(catId + "-grid");
      const nav = document.getElementById(catId + "-nav");
      if (grid) {
        grid.innerHTML =
          '<div class="empty">Jelenleg nincs termék ebben a kategóriában.</div>';
      }
      if (nav) nav.innerHTML = "";
    }
  });
}

// ===== 4/C – Partner + kategória teljes feed háttérbetöltés =====
async function hydratePartnerCategoryItems(pid, catId) {
  const key = pid + "||" + catId;
  if (PARTNER_CATEGORY_LOAD_PROMISES[key]) {
    return PARTNER_CATEGORY_LOAD_PROMISES[key];
  }

  const p = (async () => {
    try {
      const cfg = PARTNERS.get(pid);
      if (!cfg) return;

      const meta = await getMeta(pid);
      const pageSize = meta.pageSize || 300;
      const totalPages =
        meta.pages || Math.ceil((meta.total || 0) / pageSize) || 1;

      let pagesToScan = null;
      if (cfg.categoryIndex && cfg.categoryIndex[catId]) {
        const idx = cfg.categoryIndex[catId];
        if (idx && Array.isArray(idx.pages) && idx.pages.length) {
          pagesToScan = idx.pages
            .map((n) => parseInt(n, 10))
            .filter((n) => Number.isFinite(n) && n >= 1 && n <= totalPages);
        }
      }

      const allRows = [];

      if (pagesToScan && pagesToScan.length) {
        for (const pg of pagesToScan) {
          const arr = await getPageItems(pid, pg);
          for (const it of arr) {
            const cats = getCategoriesForItem(pid, it) || [];
            if (cats.includes(catId)) {
              allRows.push({ pid, item: it });
            }
          }
        }
      } else {
        for (let pg = 1; pg <= totalPages; pg++) {
          const arr = await getPageItems(pid, pg);
          for (const it of arr) {
            const cats = getCategoriesForItem(pid, it) || [];
            if (cats.includes(catId)) {
              allRows.push({ pid, item: it });
            }
          }
        }
      }

      if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};
      PARTNER_CATEGORY_ITEMS[pid][catId] = allRows;

      if (
        PARTNER_VIEW_STATE.pid === pid &&
        PARTNER_VIEW_STATE.catId === catId
      ) {
        PARTNER_VIEW_STATE.items = allRows.slice();
        PARTNER_VIEW_STATE.loading = false;
        applyPartnerFilters();

        const total = PARTNER_VIEW_STATE.filtered.length || 0;
        const pageSizeView = PARTNER_VIEW_STATE.pageSize || 20;
        const maxPage = Math.max(1, Math.ceil(total / pageSizeView));
        const current = PARTNER_VIEW_STATE.page || 1;
        const newPage = current > maxPage ? maxPage : current;
        renderPartnerViewPage(newPage);
      }
    } catch (e) {
      console.error("hydratePartnerCategoryItems hiba:", pid, catId, e);
      if (
        PARTNER_VIEW_STATE.pid === pid &&
        PARTNER_VIEW_STATE.catId === catId
      ) {
        PARTNER_VIEW_STATE.loading = false;
        applyPartnerFilters();
        renderPartnerViewPage(1);
      }
    } finally {
      delete PARTNER_CATEGORY_LOAD_PROMISES[key];
    }
  })();

  PARTNER_CATEGORY_LOAD_PROMISES[key] = p;
  return p;
}

// ===== PARTNER NÉZET – KERESÉS, RENDEZÉS, LAPOZÁS =====
function applyPartnerFilters() {
  if (!PARTNER_VIEW_STATE.items) {
    PARTNER_VIEW_STATE.filtered = [];
    return;
  }
  const q = (PARTNER_VIEW_STATE.query || "").toLowerCase();
  let arr = PARTNER_VIEW_STATE.items.slice();

  if (q) {
    arr = arr.filter(({ item }) => {
      const t = ((item && item.title) || "").toLowerCase();
      const d = ((item && item.desc) || "").toLowerCase();
      return t.includes(q) || d.includes(q);
    });
  }

  const sort = PARTNER_VIEW_STATE.sort;
  if (sort === "name-asc" || sort === "name-desc") {
    arr.sort((a, b) => {
      const ta = ((a.item && a.item.title) || "").toLowerCase();
      const tb = ((b.item && b.item.title) || "").toLowerCase();
      if (ta < tb) return sort === "name-asc" ? -1 : 1;
      if (ta > tb) return sort === "name-asc" ? 1 : -1;
      return 0;
    });
  } else if (sort === "price-asc" || sort === "price-desc") {
    arr.sort((a, b) => {
      const pa =
        a.item && typeof a.item.price === "number" ? a.item.price : Infinity;
      const pb =
        b.item && typeof b.item.price === "number" ? b.item.price : Infinity;
      if (pa === pb) return 0;
      if (sort === "price-asc") return pa - pb;
      return pb - pa;
    });
  }

  PARTNER_VIEW_STATE.filtered = arr;
}

function renderPartnerViewPage(page) {
  const grid = document.getElementById("partner-view-grid");
  const nav = document.getElementById("partner-view-nav");
  if (!grid || !nav) return;

  if (!PARTNER_VIEW_STATE.filtered || !PARTNER_VIEW_STATE.filtered.length) {
    if (PARTNER_VIEW_STATE.loading) {
      grid.innerHTML = '<div class="empty">Termékek betöltése…</div>';
    } else {
      grid.innerHTML =
        '<div class="empty">Nincs találat ennél a partnernél.</div>';
    }
    nav.innerHTML = "";
    return;
  }

  const total = PARTNER_VIEW_STATE.filtered.length;
  const pageSize = PARTNER_VIEW_STATE.pageSize || 20;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  if (page < 1) page = 1;
  if (page > maxPage) page = maxPage;
  PARTNER_VIEW_STATE.page = page;

  const start = (page - 1) * pageSize;
  const slice = PARTNER_VIEW_STATE.filtered.slice(start, start + pageSize);

  grid.innerHTML = renderCategoryCards(slice, PARTNER_VIEW_STATE.catId, false);

  nav.innerHTML =
    '<button class="btn-megnez" ' +
    (page <= 1 ? "disabled" : "") +
    ' data-partner-page="' +
    (page - 1) +
    '">Előző</button>' +
    '<span style="align-self:center;font-size:13px;margin:0 8px;">' +
    page +
    "/" +
    maxPage +
    "</span>" +
    '<button class="btn-megnez" ' +
    (page >= maxPage ? "disabled" : "") +
    ' data-partner-page="' +
    (page + 1) +
    '">Következő</button>';
}

function openPartnerView(pid, catId) {
  const sec = document.getElementById("partner-view");
  const titleEl = document.getElementById("partner-view-title");
  const subEl = document.getElementById("partner-view-subtitle");
  if (!sec || !titleEl || !subEl) return;

  const name = getPartnerName(pid);
  const catName = getCategoryName(catId);

  const itemsForCombo =
    (PARTNER_CATEGORY_ITEMS[pid] && PARTNER_CATEGORY_ITEMS[pid][catId]) || [];

  PARTNER_VIEW_STATE = {
    pid,
    catId,
    items: itemsForCombo.slice(),
    filtered: [],
    page: 1,
    pageSize: 20,
    sort: "default",
    query: "",
    loading: true,
  };

  const searchInput = document.getElementById("partner-search");
  const sortSelect = document.getElementById("partner-sort");
  if (searchInput) searchInput.value = "";
  if (sortSelect) sortSelect.value = "default";

  titleEl.textContent = name + (catName ? " – " + catName : "");
  subEl.textContent = itemsForCombo.length
    ? "Ebben a nézetben a(z) " +
      name +
      " " +
      (catName || "") +
      " ajánlatai látszanak. A teljes lista betöltése folyamatban…"
    : "A teljes lista betöltése folyamatban ennél a partner–kategória kombinációnál.";

  const hero = document.querySelector(".hero");
  const catbarWrap = document.querySelector(".catbar-wrap");
  const bf = document.getElementById("black-friday");
  const akciok = document.getElementById("akciok");

  [hero, catbarWrap, bf, akciok].forEach((el) => {
    if (el) el.classList.add("hidden");
  });

  CATEGORY_IDS.forEach((id) => {
    const s = document.getElementById(id);
    if (s) s.classList.add("hidden");
  });

  sec.classList.remove("hidden");

  applyPartnerFilters();
  renderPartnerViewPage(1);

  hydratePartnerCategoryItems(pid, catId);
}

// ===== Hero kereső → search.html (Algolia) =====
function attachSearchForm() {
  const form = document.getElementById("searchFormAll");
  const input = document.getElementById("qAll");
  if (!form || !input) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const q = (input.value || "").trim();
    if (!q) return;

    const current = window.location.href;
    try {
      const url = new URL(current);
      const base = url.origin + "/search.html";
      const target = base + "?q=" + encodeURIComponent(q);
      window.location.href = target;
    } catch (_) {
      window.location.href = "search.html?q=" + encodeURIComponent(q);
    }
  });
}

// ===== Menü & kategória pill görgetés =====
function smoothScrollTo(selector) {
  const el = document.querySelector(selector);
  if (!el) return;

  const rect = el.getBoundingClientRect();
  const offset = window.scrollY || window.pageYOffset || 0;
  const top = rect.top + offset - 70;

  window.scrollTo({
    top,
    behavior: "smooth",
  });
}

function handleScrollClick(event) {
  const trigger = event.target.closest("[data-scroll]");
  if (!trigger) return;

  const target = trigger.getAttribute("data-scroll");
  if (!target) return;

  event.preventDefault();
  smoothScrollTo(target);

  if (trigger.classList.contains("cat-pill")) {
    document.querySelectorAll(".cat-pill").forEach((el) => {
      el.classList.toggle("active", el === trigger);
    });
  }
}

function attachScrollHandlers() {
  document.addEventListener("click", handleScrollClick);
}

// ===== FELSŐ NAV =====
function showCategoryOnly(catId) {
  const hero = document.querySelector(".hero");
  const catbarWrap = document.querySelector(".catbar-wrap");
  const bf = document.getElementById("black-friday");
  const akciok = document.getElementById("akciok");
  const pv = document.getElementById("partner-view");

  [hero, catbarWrap, bf, akciok].forEach((el) => {
    if (el) el.classList.add("hidden");
  });
  if (pv) pv.classList.add("hidden");

  CATEGORY_IDS.forEach((id) => {
    const sec = document.getElementById(id);
    if (!sec) return;
    if (id === catId) {
      sec.classList.remove("hidden");
    } else {
      sec.classList.add("hidden");
    }
  });

  smoothScrollTo("#" + catId);
}

function showAllSections() {
  const hero = document.querySelector(".hero");
  const catbarWrap = document.querySelector(".catbar-wrap");
  const bf = document.getElementById("black-friday");
  const akciok = document.getElementById("akciok");
  const pv = document.getElementById("partner-view");

  [hero, catbarWrap, bf, akciok].forEach((el) => {
    if (el) el.classList.remove("hidden");
  });
  if (pv) pv.classList.add("hidden");

  CATEGORY_IDS.forEach((id) => {
    const sec = document.getElementById(id);
    if (sec) sec.classList.remove("hidden");
  });

  smoothScrollTo("#akciok");
}

function handleNavClick(event) {
  const btn = event.target.closest(".nav-btn[data-view]");
  if (!btn) return;

  const view = btn.getAttribute("data-view");
  if (view === "home") {
    event.preventDefault();
    showAllSections();
    return;
  }

  if (view === "category") {
    const catId = btn.getAttribute("data-cat");
    if (!catId) return;
    event.preventDefault();
    showCategoryOnly(catId);
  }
}

function attachNavHandlers() {
  document.addEventListener("click", handleNavClick);
}

// ===== PARTNER NÉZET – UI EVENTEK =====
function handlePartnerUiClick(event) {
  // Kategória partner-blokk címe
  const headerBtn = event.target.closest(".partner-block-title");
  if (headerBtn) {
    event.preventDefault();
    const pid = headerBtn.getAttribute("data-partner");
    const catId = headerBtn.getAttribute("data-cat") || null;
    if (pid && catId) {
      openPartnerView(pid, catId);
    }
    return;
  }

  // Vissza gomb partner-nézetben
  const backBtn = event.target.closest(".btn-back-partner");
  if (backBtn) {
    event.preventDefault();
    if (PARTNER_VIEW_STATE && PARTNER_VIEW_STATE.catId) {
      showCategoryOnly(PARTNER_VIEW_STATE.catId);
    } else {
      showAllSections();
    }
    return;
  }

  // Főoldal gomb partner-nézetben
  const homeBtn = event.target.closest(".btn-home-partner");
  if (homeBtn) {
    event.preventDefault();
    showAllSections();
    return;
  }

  // Lapozó gombok – kategória-blokk VAGY partner-nézet
  const pagerBtn = event.target.closest("[data-partner-page]");
  if (pagerBtn) {
    event.preventDefault();
    const p = parseInt(pagerBtn.getAttribute("data-partner-page"), 10);
    if (!Number.isFinite(p)) return;

    const inPartnerView = !!pagerBtn.closest("#partner-view");
    if (inPartnerView) {
      renderPartnerViewPage(p);
    } else {
      const pid = pagerBtn.getAttribute("data-partner");
      const catId = pagerBtn.getAttribute("data-cat");
      if (!pid || !catId) return;
      const byPartner = CATEGORY_PAGES[catId];
      if (!byPartner || !byPartner[pid]) return;
      const pages = byPartner[pid];
      if (p < 1 || p > pages.length) return;
      if (!CATEGORY_CURRENT[catId]) CATEGORY_CURRENT[catId] = {};
      CATEGORY_CURRENT[catId][pid] = p;
      renderCategory(catId);
    }
    return;
  }
}

function attachPartnerViewHandlers() {
  const searchInput = document.getElementById("partner-search");
  const sortSelect = document.getElementById("partner-sort");

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      PARTNER_VIEW_STATE.query = this.value || "";
      applyPartnerFilters();
      renderPartnerViewPage(1);
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener("change", function () {
      PARTNER_VIEW_STATE.sort = this.value || "default";
      applyPartnerFilters();
      renderPartnerViewPage(1);
    });
  }

  document.addEventListener("click", handlePartnerUiClick);
}

// ===== INIT =====
async function init() {
  try {
    attachScrollHandlers();
    attachNavHandlers();
    attachSearchForm();
    attachPartnerViewHandlers();
    await loadPartners();
    await buildAkciosBlokk();
    await buildCategoryBlocks();
  } catch (e) {
    console.error("Init hiba:", e);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
