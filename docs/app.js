const FEEDS_BASE = "";
const PARTNERS_URL = "feeds/partners.json";

const PARTNERS = new Map();
const META = new Map();
const CATEGORY_META = new Map();
const PAGES = new Map();

// ===== category-map.json =====
const CATEGORY_MAP_URL = FEEDS_BASE + "/feeds/category-map.json";
const CATEGORY_MAP = {};

function normalizeCategoryText(str) {
  return (str || "")
    .toString()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

async function loadCategoryMap() {
  try {
    const r = await fetch(CATEGORY_MAP_URL, { cache: "no-cache" });
    if (!r.ok) return;

    const text = await r.text();
    if (!text.trim()) {
      // üres fájl – nem baj, csak nincs finomhangolt szabály
      return;
    }

    let data = null;
    try {
      data = JSON.parse(text);
    } catch (parseErr) {
      console.warn("category-map.json parse hiba:", parseErr);
      return;
    }

    if (!data || typeof data !== "object") return;

    Object.keys(data).forEach((pid) => {
      const rules = data[pid];
      if (!Array.isArray(rules)) return;
      CATEGORY_MAP[pid] = rules
        .map((rule) => ({
          pattern: normalizeCategoryText(rule.pattern || ""),
          catId: rule.catId || "",
        }))
        .filter((r) => r.catId);
    });

    console.log("category-map.json betöltve");
  } catch (e) {
    console.warn("category-map betöltési hiba:", e);
  }
}

function mapCategoryByPartner(pid, it) {
  const rules = CATEGORY_MAP[pid];
  if (!rules || !rules.length) return null;

  const baseCat =
    (it && (it.categoryPath || it.category_path || it.category || "")) || "";
  const text = normalizeCategoryText(
    baseCat +
      " " +
      ((it && it.title) || "") +
      " " +
      ((it && (it.desc || it.description)) || "")
  );

  if (!text) {
    const fallback = rules.find((r) => !r.pattern);
    return fallback ? fallback.catId : null;
  }

  for (const rule of rules) {
    if (rule.pattern && text.includes(rule.pattern)) return rule.catId;
  }

  return null;
}

// ===== Deeplink =====
function dlUrl(pid, rawUrl) {
  if (!rawUrl) return "#";
  return FEEDS_BASE + "/api/dl?u=" + encodeURIComponent(rawUrl) + "&p=" + pid;
}

// ===== Helper =====
function priceText(v) {
  if (typeof v === "number" && isFinite(v))
    return v.toLocaleString("hu-HU") + " Ft";
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

// ===== Variáns normalizálás / dedupe =====
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
      if (drop.includes(k.toLowerCase())) x.searchParams.delete(k);
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
    const key =
      basePath(stripVariantParams(itemUrl(it))) +
      "|" +
      imgPath(itemImg(it)) +
      "|" +
      normalizeTitleNoSize(it.title);
    if (!seen.has(key)) {
      seen.add(key);
      out.push(it);
    }
  });
  return out;
}

function dedupeRowsStrong(rows) {
  const out = [];
  const seen = new Set();
  (rows || []).forEach((row) => {
    if (!row || !row.item) return;
    const it = row.item;
    const key =
      row.pid +
      "|" +
      basePath(stripVariantParams(itemUrl(it))) +
      "|" +
      imgPath(itemImg(it)) +
      "|" +
      normalizeTitleNoSize(it.title || "");
    if (!seen.has(key)) {
      seen.add(key);
      out.push(row);
    }
  });
  return out;
}

// ===== Discount (backend-only, korrekt) =====
function getDiscountNumber(it) {
  if (it && typeof it.discount === "number" && isFinite(it.discount)) {
    const d = Math.round(it.discount);
    if (d >= 10 && d <= 70) return d;
  }
  return null;
}

// Akciós árak kiszámítása: jelenlegi + eredeti (ha van)
function getAkcioPrices(it) {
  if (!it) return { current: null, original: null };

  let current = null;

  // jelenlegi / akciós ár
  if (typeof it.price === "number" && isFinite(it.price)) {
    current = it.price;
  } else if (typeof it.sale_price === "number" && isFinite(it.sale_price)) {
    current = it.sale_price;
  }

  // eredeti ár lehetséges mezőkben
  let original = null;
  const candidates = [
    it.old_price,
    it.price_old,
    it.original_price,
    it.list_price,
    it.regular_price,
  ];

  for (const v of candidates) {
    if (typeof v === "number" && isFinite(v)) {
      original = v;
      break;
    }
  }

  // ha nincs explicit eredeti ár, számoljuk vissza a discount-ból
  const disc = getDiscountNumber(it);
  if (!original && current && disc !== null) {
    const base = current / (1 - disc / 100);
    if (isFinite(base) && base > 0) {
      original = Math.round(base);
    }
  }

  return { current, original };
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
    // categoryMetaPattern, categoryPagePattern opcionális
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

// ===== Meta helper függvények (régi + új formátum) =====
function metaPageSize(meta, fallback) {
  if (!meta || typeof meta !== "object") return fallback;
  return meta.pageSize || meta.page_size || fallback;
}

function metaTotalItems(meta) {
  if (!meta || typeof meta !== "object") return 0;
  return meta.total || meta.total_items || meta.totalItems || 0;
}

function metaPageCount(meta, pageSizeFallback) {
  if (!meta || typeof meta !== "object") return 0;
  return (
    meta.pages ||
    meta.page_count ||
    meta.pageCount ||
    (pageSizeFallback
      ? Math.ceil(metaTotalItems(meta) / pageSizeFallback)
      : 0)
  );
}

// ===== Kategória meta + kategória page (pl. ALZA /feeds/alza/{CAT}/...) =====
async function getCategoryMeta(pid, catId) {
  const cfg = PARTNERS.get(pid);
  if (!cfg || !cfg.categoryMetaPattern) return null;

  const backendSlug = CATID_TO_BACKEND[catId];
  if (!backendSlug) return null;

  const key = pid + "||" + backendSlug;
  if (CATEGORY_META.has(key)) return CATEGORY_META.get(key);

  const url =
    FEEDS_BASE +
    "/" +
    cfg.categoryMetaPattern.replace("{CAT}", backendSlug);

  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) {
    console.warn("Category meta nem elérhető:", pid, backendSlug, r.status);
    return null;
  }
  const m = await r.json();
  CATEGORY_META.set(key, m);
  return m;
}

async function getCategoryFeedItems(pid, catId, pageNum) {
  const cfg = PARTNERS.get(pid);
  if (!cfg || !cfg.categoryPagePattern) return null;

  const backendSlug = CATID_TO_BACKEND[catId];
  if (!backendSlug) return null;

  if (!PAGES.has(pid)) PAGES.set(pid, new Map());
  const store = PAGES.get(pid);
  const key =
    backendSlug + "-page-" + String(pageNum).padStart(4, "0");
  if (store.has(key)) return store.get(key);

  const url =
    FEEDS_BASE +
    "/" +
    cfg.categoryPagePattern
      .replace("{CAT}", backendSlug)
      .replace("{NNNN}", String(pageNum).padStart(4, "0"));

  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) {
    console.warn(
      "Category feed page nem elérhető:",
      pid,
      backendSlug,
      pageNum,
      r.status
    );
    store.set(key, []);
    return [];
  }

  const d = await r.json();
  const arr = d && d.items ? d.items : [];
  store.set(key, arr);
  return arr;
}

// ===== Partner default kategória (frontend) =====
const BASE_CATEGORY_BY_PARTNER = {
  tchibo: "kat-divat",
  "cj-karcher": "kat-kert",
  "cj-eoptika": "kat-latas",
  "cj-jateknet": "kat-jatekok",
  jateksziget: "kat-jatekok",
  regiojatek: "kat-jatekok",
  decathlon: "kat-sport",
  alza: "kat-elektronika",
  kozmetikaotthon: "kat-szepseg",
  pepita: "kat-otthon",
  ekszereshop: "kat-szepseg",
  karacsonydekor: "kat-otthon",
  otthonmarket: "kat-otthon",
  onlinemarkabolt: "kat-otthon",
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

// ===== Fő kategória lista =====
const CATEGORY_IDS = [
  "kat-elektronika",
  "kat-gepek",
  "kat-szamitastechnika",
  "kat-mobil",
  "kat-gaming",
  "kat-smart-home",
  "kat-otthon",
  "kat-lakberendezes",
  "kat-konyha",
  "kat-kert",
  "kat-jatekok",
  "kat-divat",
  "kat-szepseg",
  "kat-drogeria",
  "kat-baba",
  "kat-sport",
  "kat-egeszseg",
  "kat-latas",
  "kat-allatok",
  "kat-konyv",
  "kat-utazas",
  "kat-iroda-iskola",
  "kat-szerszam-barkacs",
  "kat-auto-motor",
  "kat-multi",
];

// Backend findora_main / cat → front-end kat-* ID
const FINDORA_MAIN_TO_CATID = {
  "kat-elektronika": "kat-elektronika",
  "kat-gepek": "kat-gepek",
  "kat-szamitastechnika": "kat-szamitastechnika",
  "kat-mobil": "kat-mobil",
  "kat-gaming": "kat-gaming",
  "kat-smart-home": "kat-smart-home",
  "kat-otthon": "kat-otthon",
  "kat-lakberendezes": "kat-lakberendezes",
  "kat-konyha": "kat-konyha",
  "kat-kert": "kat-kert",
  "kat-jatekok": "kat-jatekok",
  "kat-divat": "kat-divat",
  "kat-szepseg": "kat-szepseg",
  "kat-drogeria": "kat-drogeria",
  "kat-baba": "kat-baba",
  "kat-sport": "kat-sport",
  "kat-egeszseg": "kat-egeszseg",
  "kat-latas": "kat-latas",
  "kat-allatok": "kat-allatok",
  "kat-konyv": "kat-konyv",
  "kat-utazas": "kat-utazas",
  "kat-iroda-iskola": "kat-iroda-iskola",
  "kat-szerszam-barkacs": "kat-szerszam-barkacs",
  "kat-auto-motor": "kat-auto-motor",
  "kat-multi": "kat-multi",
};

// Backend szinonimák (Python-ból jövő kulcsok → kat-* ID)
const BACKEND_SYNONYM_TO_CATID = {
  elektronika: "kat-elektronika",
  haztartasi_gepek: "kat-gepek",
  szamitastechnika: "kat-szamitastechnika",
  mobil: "kat-mobil",
  gaming: "kat-gaming",
  smart_home: "kat-smart-home",
  otthon: "kat-otthon",
  lakberendezes: "kat-lakberendezes",
  konyha_fozes: "kat-konyha",
  kert: "kat-kert",
  jatekok: "kat-jatekok",
  divat: "kat-divat",
  szepseg: "kat-szepseg",
  drogeria: "kat-drogeria",
  baba: "kat-baba",
  sport: "kat-sport",
  egeszseg: "kat-egeszseg",
  latas: "kat-latas",
  allatok: "kat-allatok",
  konyv: "kat-konyv",
  utazas: "kat-utazas",
  iroda_iskola: "kat-iroda-iskola",
  szerszam_barkacs: "kat-szerszam-barkacs",
  auto_motor: "kat-auto-motor",
  multi: "kat-multi",
};

// backend cat kulcs → kat-* ID (fordított map)
const BACKEND_FROM_CATID = {};
Object.entries(FINDORA_MAIN_TO_CATID).forEach(([backendKey, catId]) => {
  BACKEND_FROM_CATID[catId] = backendKey;
});

// CATID → backend slug (Python findora_main) – ALZA /feeds/alza/{CAT}/... miatt
const CATID_TO_BACKEND = {};
Object.entries(BACKEND_SYNONYM_TO_CATID).forEach(([backendKey, catId]) => {
  CATID_TO_BACKEND[catId] = backendKey;
});

// CATID → findora_main (Algolia filterhez – kanonikus kulcs, de itt főleg meta infó)
const CATID_TO_FINDORA_MAIN = {};
Object.keys(FINDORA_MAIN_TO_CATID).forEach((key) => {
  const cid = FINDORA_MAIN_TO_CATID[key];
  CATID_TO_FINDORA_MAIN[cid] = key;
});

// ===== Kategória meghatározás egy termékre – BACKEND cat + category-map + partner default =====
function getCategoriesForItem(pid, it) {
  const cfg = PARTNERS.get(pid) || {};

  // 0) Backend cat / findora_main mező (Python-ból)
  const backendCatRaw =
    it &&
    (it.findora_main ||
      it.kat ||
      it.cat ||
      it.catid ||
      it.catId ||
      it.categoryId ||
      it.category_id ||
      null);

  if (backendCatRaw) {
    const backendCat = String(backendCatRaw).toLowerCase();

    // közvetlen "kat-..." kulcs
    let mappedFromBackend = FINDORA_MAIN_TO_CATID[backendCat];

    // ha nem kat-..., akkor próbáljuk a szinonima mapet
    if (!mappedFromBackend && BACKEND_SYNONYM_TO_CATID[backendCat]) {
      mappedFromBackend = BACKEND_SYNONYM_TO_CATID[backendCat];
    }

    if (mappedFromBackend && CATEGORY_IDS.includes(mappedFromBackend)) {
      return [mappedFromBackend];
    }
  }

  // 1) Külső category-map.json alapján
  const mapped = mapCategoryByPartner(pid, it);
  if (mapped && CATEGORY_IDS.includes(mapped)) {
    return [mapped];
  }

  // 2) Partner default kategória
  const base = baseCategoryForPartner(pid, cfg);
  if (CATEGORY_IDS.includes(base)) return [base];

  // 3) Fallback
  return ["kat-multi"];
}

// ===== Helper a címekhez =====
function getPartnerName(pid) {
  const cfg = PARTNERS.get(pid);
  return (cfg && cfg.name) || pid;
}

function getCategoryName(catId) {
  const el = document.querySelector("#" + catId + " .section-header h2");
  return el ? el.textContent.trim() : "";
}

// ===== Akciós blokk + Black Friday (JSON FEED ALAPÚ) =====
let AKCIO_PAGES = [2];
let AKCIO_CURRENT = 1;

let AKCIO_FULL_STATE = {
  items: [],
  page: 1,
  pageSize: 12,
};

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

      const disc = getDiscountNumber(item);
      const prices = getAkcioPrices(item);
      const currentText = priceText(
        prices.current != null ? prices.current : item && item.price
      );
      const originalText =
        prices.original != null ? priceText(prices.original) : null;

      const partnerName = (cfg && cfg.name) || pid;

      let priceHtml = "";

      if (originalText && currentText && prices.original !== prices.current) {
        // Eredeti + akciós ár + %-os kedvezmény
        priceHtml =
          '<div class="price">' +
          '<span class="old-price" style="text-decoration:line-through;opacity:0.7;margin-right:4px;">' +
          originalText +
          "</span>" +
          '<span class="new-price" style="font-weight:bold;margin-right:4px;">' +
          currentText +
          "</span>" +
          (disc
            ? '<span class="disc" style="color:#c00;font-weight:bold;">-' +
              disc +
              "%</span>"
            : "") +
          "</div>";
      } else {
        // Csak egy ár + opcionális %-os kedvezmény
        priceHtml =
          '<div class="price">' +
          currentText +
          (disc ? " (-" + disc + "%)" : "") +
          "</div>";
      }

      let btn = "";
      if (raw) {
        btn =
          '<a class="btn-megnez akcios" href="' +
          dlUrl(cfg ? cfg.deeplinkPartner : pid, raw) +
          '" target="_blank" rel="nofollow sponsored noopener noreferrer">Megnézem🔗</a>';
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
        priceHtml +
        '<div class="partner">• ' +
        partnerName +
        "</div>" +
        btn +
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

function renderAkcioFullPage(page) {
  const grid = document.getElementById("akciok-grid");
  const nav = document.getElementById("akciok-nav");
  if (!grid || !nav) return;

  const total = AKCIO_FULL_STATE.items.length;
  if (!total) {
    grid.innerHTML =
      '<div class="empty">Jelenleg nem találtunk akciós ajánlatot.</div>';
    nav.innerHTML = "";
    return;
  }

  const pageSize = AKCIO_FULL_STATE.pageSize || 20;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  if (page < 1) page = 1;
  if (page > maxPage) page = maxPage;
  AKCIO_FULL_STATE.page = page;

  const start = (page - 1) * pageSize;
  const slice = AKCIO_FULL_STATE.items.slice(start, start + pageSize);

  grid.innerHTML = renderAkcioCards(slice);

  nav.innerHTML =
    '<button class="btn-megnez" ' +
    (page <= 1 ? "disabled" : "") +
    ' onclick="window.akciokFullPager && window.akciokFullPager.go(' +
    (page - 1) +
    ')">Előző</button>' +
    '<span style="align-self:center;font-size:13px;margin:0 8px;">' +
    page +
    "/" +
    maxPage +
    "</span>" +
    '<button class="btn-megnez" ' +
    (page >= maxPage ? "disabled" : "") +
    ' onclick="window.akciokFullPager && window.akciokFullPager.go(' +
    (page + 1) +
    ')">Következő</button>';

  window.akciokFullPager = {
    go: function (p) {
      renderAkcioFullPage(p);
    },
  };
}

// AKCIÓS BLOKK – JSON FEED, ahol lehet kategória-feedet használ
async function buildAkciosBlokk() {
  const host = document.getElementById("akciok-grid");
  if (!host) return;

  try {
    host.innerHTML =
      '<div class="card"><div class="thumb">⏳</div><div class="title">Akciók betöltése…</div></div>';
    const nav = document.getElementById("akciok-nav");
    if (nav) nav.innerHTML = "";

    const collected = [];
    const partnerIds = Array.from(PARTNERS.keys());
    const MAX_PAGES_PER_PARTNER = 5; // maximum 5 oldal / partner / akció

    for (const pid of partnerIds) {
      try {
        const cfg = PARTNERS.get(pid);
        if (!cfg) continue;

        const canUseCategoryFeed =
          cfg.categoryPagePattern && cfg.categoryMetaPattern;

        if (canUseCategoryFeed) {
          // ÚJ: partner (pl. ALZA), amelynél vannak kategória-feedek
          for (const catId of CATEGORY_IDS) {
            const backendSlug = CATID_TO_BACKEND[catId];
            if (!backendSlug) continue;

            const catMeta = await getCategoryMeta(pid, catId);
            if (!catMeta) continue;

            const pageSize = metaPageSize(catMeta, 20);
            const totalPages = metaPageCount(catMeta, pageSize) || 1;
            const limit = Math.min(totalPages, MAX_PAGES_PER_PARTNER);

            for (let pg = 1; pg <= limit; pg++) {
              const arr = await getCategoryFeedItems(pid, catId, pg);
              (arr || []).forEach((it) => {
                const disc = getDiscountNumber(it);
                if (disc !== null) {
                  collected.push({ pid, item: it });
                }
              });
            }
          }
        } else {
          // RÉGI: sima page-000X.json alapú akciószkennelés
          const meta = await getMeta(pid);
          const pageSize = metaPageSize(meta, 300);
          const totalPages = metaPageCount(meta, pageSize) || 1;

          const limit = Math.min(totalPages, MAX_PAGES_PER_PARTNER);

          for (let pg = 1; pg <= limit; pg++) {
            const arr = await getPageItems(pid, pg);
            (arr || []).forEach((it) => {
              const disc = getDiscountNumber(it);
              if (disc !== null) {
                collected.push({ pid, item: it });
              }
            });
          }
        }
      } catch (e) {
        console.error("Akciók betöltése hiba partnernél:", pid, e);
      }
    }

    if (!collected.length) {
      host.innerHTML =
        '<div class="empty">Jelenleg nem találtunk akciós ajánlatot.</div>';
      if (nav) nav.innerHTML = "";
      const bfGrid = document.getElementById("bf-grid");
      if (bfGrid) {
        bfGrid.innerHTML =
          '<div class="empty">Jelenleg nincs kifejezetten Black Friday / Black Weekend jelölésű ajánlat.</div>';
      }
      return;
    }

    const dedRows = dedupeRowsStrong(collected);

    const merged = dedRows
      .slice()
      .sort((a, b) => {
        const da = getDiscountNumber(a.item) || 0;
        const db = getDiscountNumber(b.item) || 0;
        return db - da;
      });

    // Teljes akciós lista (20/lap, nincs mesterséges lap-határ)
    AKCIO_FULL_STATE.items = merged;
    AKCIO_FULL_STATE.page = 1;

    // Főoldali előnézet (pl. 12 / lap)
    const PREVIEW_PAGE_SIZE = 12;
    AKCIO_PAGES = [];
    for (let i = 0; i < merged.length; i += PREVIEW_PAGE_SIZE) {
      AKCIO_PAGES.push(merged.slice(i, i + PREVIEW_PAGE_SIZE));
    }

    renderAkcioPage(1);

    // Black Friday blokk – akciós listából szűrve
    const bfGrid = document.getElementById("bf-grid");
    if (bfGrid) {
      const bfItems = merged.filter(({ item }) => {
        const txt =
          ((item && item.title ? item.title : "") +
            " " +
            (item && item.desc ? item.desc : "") +
            " " +
            (item && item.description ? item.description : "")).toLowerCase();
        return (
          txt.includes("black friday") ||
          txt.includes("black weekend") ||
          txt.includes("blackweekend")
        );
      });

      if (!bfItems.length) {
        bfGrid.innerHTML =
          '<div class="empty">Jelenleg nincs kifejezetten Black Friday / Black Weekend jelölésű ajánlat.</div>';
      } else {
        bfGrid.innerHTML = renderAkcioCards(bfItems.slice(0, 12));
      }
    }
  } catch (e) {
    console.error("Akciós blokk hiba:", e);
    host.innerHTML =
      '<div class="empty">Hiba történt az akciók betöltése közben.</div>';
    const nav = document.getElementById("akciok-nav");
    if (nav) nav.innerHTML = "";
    const bfGrid = document.getElementById("bf-grid");
    if (bfGrid) {
      bfGrid.innerHTML =
        '<div class="empty">Hiba történt a Black Friday ajánlatok betöltése közben.</div>';
    }
  }
}

// ===== KATEGÓRIA BLOKKOK – FŐOLDAL + PARTNER NÉZET =====
const CATEGORY_PAGES = {};
const CATEGORY_CURRENT = {};
window.catPager = window.catPager || {};

const PARTNER_CATEGORY_ITEMS = {};
const PARTNER_CATEGORY_LOAD_PROMISES = {};

// FULL kategória (összes partner, 20/lap) állapot
const FULL_CATEGORY_STATE = {
  catId: null,
  items: [],
  page: 1,
  pageSize: 20,
};
window.fullCatPager = window.fullCatPager || {};

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

// FŐOLDALI kategória-render (mixelve, lapozóval)
function renderCategory(catId, page) {
  const grid = document.getElementById(catId + "-grid");
  const nav = document.getElementById(catId + "-nav");
  if (!grid || !nav) return;

  const pages = CATEGORY_PAGES[catId] || [];
  if (!pages.length) {
    grid.innerHTML =
      '<div class="empty">Jelenleg nincs termék ebben a kategóriában.</div>';
    nav.innerHTML = "";
    return;
  }

  if (page < 1) page = 1;
  if (page > pages.length) page = pages.length;
  CATEGORY_CURRENT[catId] = page;

  const pageItems = pages[page - 1] || [];

  const groups = new Map();
  pageItems.forEach((row) => {
    const pid = row.pid;
    if (!groups.has(pid)) groups.set(pid, []);
    groups.get(pid).push(row);
  });

  let html = "";

  groups.forEach((items, pid) => {
    const partnerName = getPartnerName(pid);
    const titleText = partnerName;

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
      "</div>";
  });

  grid.innerHTML = html;

  nav.innerHTML =
    '<button class="btn-megnez" ' +
    (page <= 1 ? "disabled" : "") +
    ' onclick="window.catPager[\'' +
    catId +
    '\'] && window.catPager[\'' +
    catId +
    '\'].go(' +
    (page - 1) +
    ')">Előző</button>' +
    '<span style="align-self:center;font-size:13px;margin:0 8px;">' +
    page +
    "/" +
    pages.length +
    "</span>" +
    '<button class="btn-megnez" ' +
    (page >= pages.length ? "disabled" : "") +
    ' onclick="window.catPager[\'' +
    catId +
    '\'] && window.catPager[\'' +
    catId +
    '\'].go(' +
    (page + 1) +
    ')">Következő</button>';

  window.catPager[catId] = {
    go: function (p) {
      renderCategory(catId, p);
    },
  };
}

// KATEGÓRIA NÉZET (felső menü) – max 6 termék / partner (egy lap, „sample”)
function renderCategoryFull(catId) {
  const grid = document.getElementById(catId + "-grid");
  const nav = document.getElementById(catId + "-nav");
  if (!grid || !nav) return;

  let html = "";
  let hasAny = false;

  for (const [pid] of PARTNERS.entries()) {
    const perCat =
      PARTNER_CATEGORY_ITEMS[pid] &&
      PARTNER_CATEGORY_ITEMS[pid][catId] &&
      PARTNER_CATEGORY_ITEMS[pid][catId].length
        ? PARTNER_CATEGORY_ITEMS[pid][catId]
        : null;
    if (!perCat) continue;

    hasAny = true;
    const partnerName = getPartnerName(pid);
    const titleText = partnerName;

    const slice = perCat.slice(0, 6);

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
      renderCategoryCards(slice, catId, false) +
      "</div>" +
      "</div>";
  }

  if (!hasAny) {
    grid.innerHTML =
      '<div class="empty">Jelenleg nincs termék ebben a kategóriában.</div>';
    nav.innerHTML = "";
    return;
  }

  grid.innerHTML = html;
  nav.innerHTML = "";
}

// FULL kategória állapot felépítése (összes partner, 20/lap)
function buildFullCategoryState(catId) {
  const allRows = [];
  Object.keys(PARTNER_CATEGORY_ITEMS).forEach((pid) => {
    const perCat =
      PARTNER_CATEGORY_ITEMS[pid] &&
      PARTNER_CATEGORY_ITEMS[pid][catId] &&
      PARTNER_CATEGORY_ITEMS[pid][catId].length
        ? PARTNER_CATEGORY_ITEMS[pid][catId]
        : null;
    if (perCat && perCat.length) {
      allRows.push(...perCat);
    }
  });

  const ded = dedupeRowsStrong(allRows);
  FULL_CATEGORY_STATE.catId = catId;
  FULL_CATEGORY_STATE.items = ded;
  FULL_CATEGORY_STATE.page = 1;
}

// FULL kategória 20/lap render (összes partner összeöntve)
function renderFullCategoryPage(catId, page) {
  const grid = document.getElementById(catId + "-grid");
  const nav = document.getElementById(catId + "-nav");
  if (!grid || !nav) return;

  if (FULL_CATEGORY_STATE.catId !== catId) {
    buildFullCategoryState(catId);
  }

  const total = FULL_CATEGORY_STATE.items.length;
  if (!total) {
    grid.innerHTML =
      '<div class="empty">Jelenleg nincs termék ebben a kategóriában.</div>';
    nav.innerHTML = "";
    return;
  }

  const pageSize = FULL_CATEGORY_STATE.pageSize || 20;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  if (page < 1) page = 1;
  if (page > maxPage) page = maxPage;
  FULL_CATEGORY_STATE.page = page;

  const start = (page - 1) * pageSize;
  const slice = FULL_CATEGORY_STATE.items.slice(start, start + pageSize);

  grid.innerHTML = renderCategoryCards(slice, catId, true);

  nav.innerHTML =
    '<button class="btn-megnez" ' +
    (page <= 1 ? "disabled" : "") +
    ' onclick="window.fullCatPager[\'' +
    catId +
    '\'] && window.fullCatPager[\'' +
    catId +
    '\'].go(' +
    (page - 1) +
    ')">Előző</button>' +
    '<span style="align-self:center;font-size:13px;margin:0 8px;">' +
    page +
    "/" +
    maxPage +
    "</span>" +
    '<button class="btn-megnez" ' +
    (page >= maxPage ? "disabled" : "") +
    ' onclick="window.fullCatPager[\'' +
    catId +
    '\'] && window.fullCatPager[\'' +
    catId +
    '\'].go(' +
    (page + 1) +
    ')">Következő</button>';

  window.fullCatPager[catId] = {
    go: function (p) {
      renderFullCategoryPage(catId, p);
    },
  };
}

// ===== PARTNER NÉZET – KERESÉS, RENDEZÉS, LAPOZÁS =====
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

function updatePartnerSubtitle() {
  const subEl = document.getElementById("partner-view-subtitle");
  if (!subEl || !PARTNER_VIEW_STATE.pid || !PARTNER_VIEW_STATE.catId) return;

  const name = getPartnerName(PARTNER_VIEW_STATE.pid);
  const catName = getCategoryName(PARTNER_VIEW_STATE.catId);
  const total =
    (PARTNER_VIEW_STATE.filtered && PARTNER_VIEW_STATE.filtered.length) || 0;

  if (PARTNER_VIEW_STATE.loading) {
    subEl.textContent =
      "Ebben a nézetben a(z) " +
      name +
      " " +
      (catName || "") +
      " ajánlatai látszanak. A teljes lista betöltése folyamatban… (" +
      total +
      " találat eddig)";
  } else {
    subEl.textContent =
      "Ebben a nézetben a(z) " +
      name +
      " " +
      (catName || "") +
      " ajánlatai látszanak. Összesen " +
      total +
      " termék.";
  }
}

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
    updatePartnerSubtitle();
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

  updatePartnerSubtitle();
}

// TELJES partner–kategória lista háttérben – JSON FEED, kategória-feed ha van
async function hydratePartnerCategoryItems(pid, catId) {
  const key = pid + "||" + catId;
  if (PARTNER_CATEGORY_LOAD_PROMISES[key]) {
    return PARTNER_CATEGORY_LOAD_PROMISES[key];
  }

  const p = (async () => {
    try {
      const cfg = PARTNERS.get(pid);
      if (!cfg) return;

      if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};
      if (!PARTNER_CATEGORY_ITEMS[pid][catId]) {
        PARTNER_CATEGORY_ITEMS[pid][catId] = [];
      }

      const pushAndUpdate = (newRows) => {
        if (!newRows || !newRows.length) return;

        const existing = PARTNER_CATEGORY_ITEMS[pid][catId] || [];
        const combined = dedupeRowsStrong(existing.concat(newRows));
        PARTNER_CATEGORY_ITEMS[pid][catId] = combined;

        if (
          PARTNER_VIEW_STATE.pid === pid &&
          PARTNER_VIEW_STATE.catId === catId
        ) {
          PARTNER_VIEW_STATE.items = combined.slice();
          applyPartnerFilters();

          const total = PARTNER_VIEW_STATE.filtered.length || 0;
          const pageSizeView = PARTNER_VIEW_STATE.pageSize || 20;
          const maxPage = Math.max(1, Math.ceil(total / pageSizeView));
          const current = PARTNER_VIEW_STATE.page || 1;
          const newPage = current > maxPage ? maxPage : current;

          renderPartnerViewPage(newPage);
        }
      };

      const canUseCategoryFeed =
        cfg.categoryPagePattern && cfg.categoryMetaPattern && CATID_TO_BACKEND[catId];

      if (canUseCategoryFeed) {
        // ÚJ: kategória-specifikus feedek (pl. ALZA /feeds/alza/{CAT}/...)
        const catMeta = await getCategoryMeta(pid, catId);
        if (catMeta) {
          const pageSize = metaPageSize(catMeta, 20);
          const totalPages = metaPageCount(catMeta, pageSize) || 1;
          const scanList = Array.from({ length: totalPages }, (_, i) => i + 1);

          for (const pg of scanList) {
            const arr = await getCategoryFeedItems(pid, catId, pg);
            const rowsForPage = (arr || []).map((it) => ({ pid, item: it }));
            pushAndUpdate(rowsForPage);
          }

          if (
            PARTNER_VIEW_STATE.pid === pid &&
            PARTNER_VIEW_STATE.catId === catId
          ) {
            PARTNER_VIEW_STATE.loading = false;
            applyPartnerFilters();
            renderPartnerViewPage(PARTNER_VIEW_STATE.page || 1);
          }
          return;
        } else {
          console.warn(
            "Category meta hiányzik, visszaesés globál scanre:",
            pid,
            catId
          );
        }
      }

      // RÉGI / FALLBACK: globál page-ek végigscannelése kategória szerint
      const meta = await getMeta(pid);
      const pageSize = metaPageSize(meta, 300);
      const totalPages = metaPageCount(meta, pageSize) || 1;

      let pagesToScan = null;
      if (cfg.categoryIndex && cfg.categoryIndex[catId]) {
        const idx = cfg.categoryIndex[catId];
        if (idx && Array.isArray(idx.pages) && idx.pages.length) {
          pagesToScan = idx.pages
            .map((n) => parseInt(n, 10))
            .filter((n) => Number.isFinite(n) && n >= 1 && n <= totalPages);
        }
      }

      const scanList =
        pagesToScan && pagesToScan.length
          ? pagesToScan
          : Array.from({ length: totalPages }, (_, i) => i + 1);

      for (const pg of scanList) {
        const arr = await getPageItems(pid, pg);
        const rowsForPage = [];

        for (const it of arr) {
          const cats = getCategoriesForItem(pid, it) || [];
          if (cats.includes(catId)) {
            rowsForPage.push({ pid, item: it });
          }
        }

        pushAndUpdate(rowsForPage);
      }

      if (
        PARTNER_VIEW_STATE.pid === pid &&
        PARTNER_VIEW_STATE.catId === catId
      ) {
        PARTNER_VIEW_STATE.loading = false;
        applyPartnerFilters();
        renderPartnerViewPage(PARTNER_VIEW_STATE.page || 1);
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

  applyPartnerFilters();
  updatePartnerSubtitle();

  const hero = document.querySelector(".hero");
  const catbarWrap = document.querySelector(".catbar-wrap");
  const bf = document.getElementById("black-friday");
  const akciok = document.getElementById("akciok");
  const homeDescs = document.getElementById("home-category-descriptions");

  [hero, catbarWrap, bf, akciok, homeDescs].forEach((el) => {
    if (el) el.classList.add("hidden");
  });

  CATEGORY_IDS.forEach((id) => {
    const s = document.getElementById(id);
    if (s) s.classList.add("hidden");
  });

  sec.classList.remove("hidden");

  renderPartnerViewPage(1);

  hydratePartnerCategoryItems(pid, catId);
}

// ===== KATEGÓRIA NÉZET – PARTNERENKÉNT 6 TERMÉK / BLOKK =====
function showCategoryOnly(catId) {
  const hero = document.querySelector(".hero");
  const catbarWrap = document.querySelector(".catbar-wrap");
  const bf = document.getElementById("black-friday");
  const akciok = document.getElementById("akciok");
  const pv = document.getElementById("partner-view");
  const homeDescs = document.getElementById("home-category-descriptions");

  [hero, catbarWrap, bf, akciok, homeDescs].forEach((el) => {
    if (el) el.classList.add("hidden");
  });
  if (pv) pv.classList.add("hidden");

  CATEGORY_IDS.forEach((id) => {
    const sec = document.getElementById(id);
    if (!sec) return;

    if (id === catId) {
      sec.classList.remove("hidden");
      if (CATEGORY_PAGES[id] && CATEGORY_PAGES[id].length) {
        const current = CATEGORY_CURRENT[id] || 1;
        renderCategory(id, current);
      }
    } else {
      sec.classList.add("hidden");
    }
  });

  smoothScrollTo("#" + catId);
}

// FULL KATEGÓRIA NÉZET – csak adott kategória, összes partner, 20/lap
function showFullCategoryList(catId) {
  const hero = document.querySelector(".hero");
  const catbarWrap = document.querySelector(".catbar-wrap");
  const bf = document.getElementById("black-friday");
  const akciok = document.getElementById("akciok");
  const pv = document.getElementById("partner-view");
  const homeDescs = document.getElementById("home-category-descriptions");

  [hero, catbarWrap, bf, akciok, homeDescs].forEach((el) => {
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

  buildFullCategoryState(catId);
  renderFullCategoryPage(catId, 1);
  smoothScrollTo("#" + catId);
}

// ===== Hero kereső → Algolia search.html (globális kereső, külön oldal JS-sel) =====
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

// ===== FELSŐ NAV – FŐOLDAL vs KATEGÓRIA =====
function showAllSections() {
  const hero = document.querySelector(".hero");
  const catbarWrap = document.querySelector(".catbar-wrap");
  const bf = document.getElementById("black-friday");
  const akciok = document.getElementById("akciok");
  const pv = document.getElementById("partner-view");
  const homeDescs = document.getElementById("home-category-descriptions");

  [hero, catbarWrap, bf, akciok, homeDescs].forEach((el) => {
    if (el) el.classList.remove("hidden");
  });
  if (pv) pv.classList.add("hidden");

  CATEGORY_IDS.forEach((id) => {
    const sec = document.getElementById(id);
    if (sec) sec.classList.remove("hidden");

    if (CATEGORY_PAGES[id] && CATEGORY_PAGES[id].length) {
      const current = CATEGORY_CURRENT[id] || 1;
      renderCategory(id, current);
    }
  });

  smoothScrollTo("#akciok");
}

function handleNavClick(event) {
  const btn = event.target.closest(".nav-btn[data-view]");
  if (!btn) return;

  const view = btn.getAttribute("data-view");

  // Főoldal
  if (view === "home") {
    event.preventDefault();
    showAllSections();
    return;
  }

  // Akciók – külön nézet (20/lap)
  if (view === "akciok") {
    event.preventDefault();
    showAkcioOnly();
    return;
  }

  // Kategória nézet
  if (view === "category") {
    const catId = btn.getAttribute("data-cat");
    if (!catId) return;
    event.preventDefault();
    showCategoryOnly(catId);
    return;
  }

  // Teljes kategória 20/lap
  if (view === "category-full") {
    const catId = btn.getAttribute("data-cat");
    if (!catId) return;
    event.preventDefault();
    showFullCategoryList(catId);
    return;
  }
}

function attachNavHandlers() {
  document.addEventListener("click", handleNavClick);
}

// ===== PARTNER NÉZET – UI EVENTEK =====
function handlePartnerUiClick(event) {
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

  const homeBtn = event.target.closest(".btn-home-partner");
  if (homeBtn) {
    event.preventDefault();
    showAllSections();
    return;
  }

  const pagerBtn = event.target.closest("[data-partner-page]");
  if (pagerBtn) {
    event.preventDefault();
    const p = parseInt(pagerBtn.getAttribute("data-partner-page"), 10);
    if (Number.isFinite(p)) {
      renderPartnerViewPage(p);
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

// ===== Akció cím kattintható: teljes 20/lap nézet =====
function attachAkcioTitleHandler() {
  const title = document.querySelector("#akciok .section-header h2");
  if (!title) return;
  title.style.cursor = "pointer";
  title.addEventListener("click", function () {
    showAkcioOnly();
  });
}

function showAkcioOnly() {
  const hero = document.querySelector(".hero");
  const catbarWrap = document.querySelector(".catbar-wrap");
  const bf = document.getElementById("black-friday");
  const pv = document.getElementById("partner-view");
  const homeDescs = document.getElementById("home-category-descriptions");

  [hero, catbarWrap, bf, homeDescs].forEach((el) => {
    if (el) el.classList.add("hidden");
  });
  if (pv) pv.classList.add("hidden");

  CATEGORY_IDS.forEach((id) => {
    const sec = document.getElementById(id);
    if (sec) sec.classList.add("hidden");
  });

  const ak = document.getElementById("akciok");
  if (ak) ak.classList.remove("hidden");

  renderAkcioFullPage(1);
  smoothScrollTo("#akciok");
}

// ===== 3. KATEGÓRIA BLOKKOK FELÉPÍTÉSE (FŐOLDAL) – JSON FEED, kategória-feed ahol lehet =====
async function buildCategoryBlocks() {
  const PAGE_SIZE = 6; // 6 kártya / partner / oldal
  const MAX_PAGES_PER_PARTNER = 5; // max 5 oldal / partner / kategória főoldali mintához

  // Tisztítás
  CATEGORY_IDS.forEach((catId) => {
    CATEGORY_PAGES[catId] = [];
    CATEGORY_CURRENT[catId] = 0;
  });
  Object.keys(PARTNER_CATEGORY_ITEMS).forEach((k) => {
    delete PARTNER_CATEGORY_ITEMS[k];
  });

  // buffers[catId][pid] = [{ pid, item }, ...]
  const buffers = {};

  const partnerIds = Array.from(PARTNERS.keys());

  for (const pid of partnerIds) {
    try {
      const cfg = PARTNERS.get(pid);
      if (!cfg) continue;

      const canUseCategoryFeed =
        cfg.categoryPagePattern && cfg.categoryMetaPattern;

      if (canUseCategoryFeed) {
        // ÚJ: partner (pl. ALZA) – közvetlenül a kategória-feedeket használjuk
        for (const catId of CATEGORY_IDS) {
          const backendSlug = CATID_TO_BACKEND[catId];
          if (!backendSlug) continue;

          const catMeta = await getCategoryMeta(pid, catId);
          if (!catMeta) continue;

          const pageSize = metaPageSize(catMeta, 20);
          const totalPages = metaPageCount(catMeta, pageSize) || 1;
          const limit = Math.min(totalPages, MAX_PAGES_PER_PARTNER);

          for (let pg = 1; pg <= limit; pg++) {
            const arr = await getCategoryFeedItems(pid, catId, pg);
            (arr || []).forEach((it) => {
              // catId itt már ismert (kategória feed szerint)
              if (!CATEGORY_IDS.includes(catId)) return;

              if (!buffers[catId]) buffers[catId] = {};
              if (!buffers[catId][pid]) buffers[catId][pid] = [];
              buffers[catId][pid].push({ pid, item: it });

              if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};
              if (!PARTNER_CATEGORY_ITEMS[pid][catId]) {
                PARTNER_CATEGORY_ITEMS[pid][catId] = [];
              }
              PARTNER_CATEGORY_ITEMS[pid][catId].push({ pid, item: it });
            });
          }
        }
      } else {
        // RÉGI: globál page-000X.json + getCategoriesForItem()
        const meta = await getMeta(pid);
        const pageSize = metaPageSize(meta, 300);
        const totalPages = metaPageCount(meta, pageSize) || 1;

        const limit = Math.min(totalPages, MAX_PAGES_PER_PARTNER);

        for (let pg = 1; pg <= limit; pg++) {
          const arr = await getPageItems(pid, pg);
          (arr || []).forEach((it) => {
            const cats = getCategoriesForItem(pid, it) || [];
            const catId = cats[0] || "kat-multi";
            if (!CATEGORY_IDS.includes(catId)) return;

            if (!buffers[catId]) buffers[catId] = {};
            if (!buffers[catId][pid]) buffers[catId][pid] = [];
            buffers[catId][pid].push({ pid, item: it });

            if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};
            if (!PARTNER_CATEGORY_ITEMS[pid][catId]) {
              PARTNER_CATEGORY_ITEMS[pid][catId] = [];
            }
            PARTNER_CATEGORY_ITEMS[pid][catId].push({ pid, item: it });
          });
        }
      }
    } catch (e) {
      console.error("buildCategoryBlocks hiba partnernél:", pid, e);
    }
  }

  // oldalak felépítése kategóriánként
  CATEGORY_IDS.forEach((catId) => {
    const perPartner = buffers[catId] || {};
    const partnerPages = {};
    let maxPagesForCat = 0;

    // partnerenként dedupe + 6-os lapokra vágás, max 5 lap
    Object.keys(perPartner).forEach((pid) => {
      const rawList = perPartner[pid] || [];
      const list = dedupeRowsStrong(rawList);
      const pages = [];

      for (
        let i = 0;
        i < list.length && pages.length < MAX_PAGES_PER_PARTNER;
        i += PAGE_SIZE
      ) {
        pages.push(list.slice(i, i + PAGE_SIZE));
      }

      if (pages.length) {
        partnerPages[pid] = pages;
        if (pages.length > maxPagesForCat) {
          maxPagesForCat = pages.length;
        }
      }
    });

    // globális kategória-lapok: adott pageIndex-en összefűzzük az összes partner adott 6-os blokkját
    const catPages = [];
    for (let pageIndex = 0; pageIndex < maxPagesForCat; pageIndex++) {
      const combined = [];
      Object.keys(partnerPages).forEach((pid) => {
        const arr = partnerPages[pid][pageIndex];
        if (arr && arr.length) combined.push(...arr);
      });
      if (combined.length) {
        catPages.push(combined);
      }
    }

    CATEGORY_PAGES[catId] = catPages;
    CATEGORY_CURRENT[catId] = catPages.length ? 1 : 0;
  });
}

// ===== INIT =====
async function init() {
  try {
    attachScrollHandlers();
    attachNavHandlers();
    attachSearchForm();
    attachPartnerViewHandlers();
    attachAkcioTitleHandler();

    await loadPartners();
    await loadCategoryMap();
    await buildAkciosBlokk();
    await buildCategoryBlocks();

    showAllSections();
  } catch (e) {
    console.error("Init hiba:", e);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}




