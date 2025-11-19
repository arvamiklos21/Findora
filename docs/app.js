// ===== Alap beállítások =====
const FEEDS_BASE = "";
const PARTNERS_URL = "feeds/partners.json";

const PARTNERS = new Map();
const META = new Map();
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
    const data = await r.json();
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
// ===== Beállítások – éles Findora feedek használata =====
const FEEDS_BASE = "";
const PARTNERS_URL = "feeds/partners.json";

const PARTNERS = new Map();
const META = new Map();
const PAGES = new Map();

// ===== Kategória-mapping külső JSON-ből (fallback a backend cat mező mellé) =====
const CATEGORY_MAP_URL = FEEDS_BASE + "/feeds/category-map.json";
const CATEGORY_MAP = {}; // { partnerId: [ { pattern, catId }, ... ] }

function normalizeCategoryText(str) {
  return (str || "")
    .toString()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // ékezet le
    .replace(/\s+/g, " ")
    .trim();
}

async function loadCategoryMap() {
  try {
    const r = await fetch(CATEGORY_MAP_URL, { cache: "no-cache" });
    if (!r.ok) {
      console.warn("category-map.json nem elérhető:", r.status);
      return;
    }
    const data = await r.json();
    if (!data || typeof data !== "object") {
      console.warn("category-map.json formátum hiba");
      return;
    }
    Object.keys(data).forEach((pid) => {
      const rules = data[pid];
      if (!Array.isArray(rules)) return;
      CATEGORY_MAP[pid] = rules
        .map((rule) => ({
          pattern: normalizeCategoryText(rule.pattern || ""),
          catId: rule.catId || ""
        }))
        .filter((r) => r.catId);
    });
    console.log(
      "Kategória-mapping betöltve partnerekhez:",
      Object.keys(CATEGORY_MAP)
    );
  } catch (e) {
    console.warn("category-map betöltési hiba:", e);
  }
}

function mapCategoryByPartner(pid, it) {
  const rules = CATEGORY_MAP[pid];
  if (!rules || !rules.length) return null;

  // Alap: partner által adott kategória mezők
  const baseCat =
    (it && (it.categoryPath || it.category_path || it.category || "")) || "";

  // Plusz: cím + leírás (hogy a "nadrág", "szoknya", "póló" stb. is számítson)
  const title = (it && it.title) || "";
  const desc = (it && (it.desc || it.description)) || "";

  const text = normalizeCategoryText(baseCat + " " + title + " " + desc);

  // ha nincs semmi szöveg, de van üres patternes szabály: "mindent ide"
  if (!text) {
    const fallback = rules.find((r) => !r.pattern);
    return fallback ? fallback.catId : null;
  }

  for (const rule of rules) {
    if (!rule.pattern) continue; // üres pattern csak fallbacknek jó
    if (text.includes(rule.pattern)) {
      return rule.catId;
    }
  }
  return null;
}

// Deeplink építése – minden gomb: Megnézem🔗
function dlUrl(partnerId, rawUrl) {
  if (!rawUrl) return "#";
  return (
    FEEDS_BASE + "/api/dl?u=" + encodeURIComponent(rawUrl) + "&p=" + partnerId
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

// Méret / szín variánsok erős deduplikálása (TITLE alapú)
const SIZE_TOKENS = new RegExp(
  [
    "\\b(?:XXS|XS|S|M|L|XL|XXL|3XL|4XL|5XL)\\b",
    "\\b(?:\\d{2,3}[\\/-]\\d{2,3})\\b",
    "\\bEU\\s?\\d{2,3}\\b",
    "[\\(\\[]\\s*(?:XXS|XS|S|M|L|XL|XXL|3XL|4XL|5XL|EU\\s?\\d{2,3}|\\d{2,3}[\\/-]\\d{2,3})\\s*[\\)\\]]",
    "\\b(?:méret|meret)\\b\\s*[:\\-]?\\s*[A-Za-z0-9\\/-]+"
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
      "variant"
    ];
    for (const k of Array.from(x.searchParams.keys())) {
      if (drop.indexOf(k.toLowerCase()) > -1) x.searchParams.delete(k);
    }
    return x.toString();
  } catch (_) {
    return u;
  }
}

// Dedup: csak item objektumokra (akciós blokk)
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

// Dedup: { pid, item } sorokra (kategória, partner-nézet)
function dedupeRowsStrong(rows) {
  const out = [];
  const seen = new Set();
  (rows || []).forEach((row) => {
    if (!row || !row.item) return;
    const pid = row.pid || "";
    const it = row.item;
    const raw = itemUrl(it);
    const key =
      pid +
      "|" +
      basePath(stripVariantParams(raw)) +
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

// ===== Diszkont százalék kinyerése – CSAK a backend numeric mezőt fogadjuk el =====
function getDiscountNumber(it) {
  if (it && typeof it.discount === "number" && isFinite(it.discount)) {
    const d = Math.round(it.discount);
    // csak 10–70% közti kedvezményt tekintünk valósnak
    if (d >= 10 && d <= 70) return d;
  }
  // nincs több szövegben keresgélés, regex, „felkerekített” kedvezmény
  return null;
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
  pepita: "kat-utazas",
  ekszereshop: "kat-szepseg",
  karacsonydekor: "kat-otthon",
  otthonmarket: "kat-otthon",
  onlinemarkabolt: "kat-otthon" // ne Elektronikában legyenek a csaptelepek
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
  "kat-multi"
];

// ===== Kategória meghatározás egy termékre – BACKEND cat + category-map + partner default =====
function getCategoriesForItem(pid, it) {
  const cfg = PARTNERS.get(pid) || {};

  // 0) Backend (Python) által kitöltött kategória mező – többféle névvel is működjön
  const backendCat =
    it &&
    (it.cat || it.catid || it.catId || it.categoryId || it.category_id || null);

  if (backendCat && CATEGORY_IDS.includes(backendCat)) {
    return [backendCat];
  }

  // 1) Külső category-map.json alapján (partner kategória mezőiből)
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

// ===== Helper a partner/kategória címekhez =====
function getPartnerName(pid) {
  const cfg = PARTNERS.get(pid);
  return (cfg && cfg.name) || pid;
}

function getCategoryName(catId) {
  const el = document.querySelector("#" + catId + " .section-header h2");
  return el ? el.textContent.trim() : "";
}

// ===== Akciós blokk (általános akciók – korrekt % kijelzéssel) =====
let AKCIO_PAGES = [];
let AKCIO_CURRENT = 1;

const DEFAULT_BF_SCAN_PAGES = 2;
const DEFAULT_BF_MIN_DISCOUNT = 10;

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
    }
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
    const partnerTasks = [];

    for (const [pid, cfg] of PARTNERS.entries()) {
      const plc = cfg.placements || {};
      const anyEnabled = Object.keys(plc).some((k) => {
        const v = plc[k];
        return (v && v.enabled) || (v && v.full && v.full.enabled);
      });
      if (!anyEnabled) continue;

      const task = (async () => {
        const bfCfg = cfg.bf || {};
        if (bfCfg.enabled === false) return;

        let scanPagesMax = parseInt(bfCfg.scanPages, 10);
        if (!Number.isFinite(scanPagesMax) || scanPagesMax <= 0) {
          scanPagesMax = DEFAULT_BF_SCAN_PAGES;
        }

        let minDiscount = parseInt(bfCfg.minDiscount, 10);
        if (
          !Number.isFinite(minDiscount) ||
          minDiscount < 10 ||
          minDiscount > 70
        ) {
          minDiscount = DEFAULT_BF_MIN_DISCOUNT;
        }

        const meta = await getMeta(pid);
        const pageSize = meta.pageSize || 300;
        const totalPages =
          meta.pages || Math.ceil((meta.total || 0) / pageSize) || 1;
        const scanPages = Math.min(scanPagesMax, totalPages);

        for (let pg = 1; pg <= scanPages; pg++) {
          const arr = await getPageItems(pid, pg);
          for (const it of arr) {
            const d = getDiscountNumber(it);
            if (d === null || d < minDiscount) continue;
            collected.push({ pid, item: it });
          }
        }
      })();

      partnerTasks.push(task);
    }

    await Promise.all(partnerTasks);

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

    const PAGE_SIZE = 12;
    AKCIO_PAGES = [];
    for (let i = 0; i < merged.length; i += PAGE_SIZE) {
      AKCIO_PAGES.push(merged.slice(i, i + PAGE_SIZE));
    }

    // Akciós blokk
    renderAkcioPage(1);

    // Külön Black Friday blokk – csak „black friday / black weekend” szöveggel
    const bfGrid = document.getElementById("bf-grid");
    if (bfGrid) {
      const bfItems = merged.filter(({ item }) => {
        const txt =
          ((item && item.title ? item.title : "") +
            " " +
            (item && item.desc ? item.desc : "") +
            " " +
            (item && item.description ? item.description : "")
          ).toLowerCase();
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

// ===== KATEGÓRIA BLOKKOK – FŐOLDAL + KÜLÖN KATEGÓRIA NÉZET =====
const CATEGORY_PAGES = {};
const CATEGORY_CURRENT = {};
window.catPager = window.catPager || {};

// Partner + kategória mátrix
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
  loading: false
};

// Kártyák renderelése
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

// FŐOLDALI kategória-render (lapozóval, mixelve, max 5 lap / kategória)
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

  const catName = getCategoryName(catId);
  let html = "";

  groups.forEach((items, pid) => {
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
    }
  };
}

// KATEGÓRIA NÉZET (felső menü) – minden partner külön blokkban, max 6 termék/partner
function renderCategoryFull(catId) {
  const grid = document.getElementById(catId + "-grid");
  const nav = document.getElementById(catId + "-nav");
  if (!grid || !nav) return;

  const catName = getCategoryName(catId);
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
    const titleText = partnerName + (catName ? " – " + catName : "");
    const slice = perCat.slice(0, 6); // max 6 / partner

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
  nav.innerHTML = ""; // külön kategória nézetben nincs lapozó
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

      const allRowsRaw = [];

      const processPage = (arr) => {
        for (const it of arr) {
          const cats = getCategoriesForItem(pid, it) || [];
          if (cats.includes(catId)) {
            allRowsRaw.push({ pid, item: it });
          }
        }
      };

      if (pagesToScan && pagesToScan.length) {
        for (const pg of pagesToScan) {
          const arr = await getPageItems(pid, pg);
          processPage(arr);
        }
      } else {
        for (let pg = 1; pg <= totalPages; pg++) {
          const arr = await getPageItems(pid, pg);
          processPage(arr);
        }
      }

      const allRows = dedupeRowsStrong(allRowsRaw);

      if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};
      PARTNER_CATEGORY_ITEMS[pid][catId] = allRows;

      if (PARTNER_VIEW_STATE.pid === pid && PARTNER_VIEW_STATE.catId === catId) {
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
      if (PARTNER_VIEW_STATE.pid === pid && PARTNER_VIEW_STATE.catId === catId) {
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
    loading: true
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

// ===== Hero kereső → Algolia keresőoldalra irányítás =====
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
    behavior: "smooth"
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

// ===== FELSŐ NAV – FŐOLDAL vs KATEGÓRIA NÉZET =====
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

  // Kategória nézet: minden partner külön blokkban, max 6 termék/partner
  renderCategoryFull(catId);

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

// ===== 3. KATEGÓRIA BLOKKOK FELÉPÍTÉSE (FŐOLDAL + KATEGÓRIA-NÉZET ALAP) =====
async function buildCategoryBlocks() {
  const buffers = {};
  const scanPagesMax = 1; // csak 1 oldal / partner a főoldalhoz – gyors betöltés

  const partnerTasks = [];

  for (const [pid, cfg] of PARTNERS.entries()) {
    const plc = cfg.placements || {};
    const anyEnabled = Object.keys(plc).some((k) => {
      const v = plc[k];
      return (v && v.enabled) || (v && v.full && v.full.enabled);
    });
    if (!anyEnabled) continue;

    const task = (async () => {
      const meta = await getMeta(pid);
      const pageSize = meta.pageSize || 300;
      const totalPages =
        meta.pages || Math.ceil((meta.total || 0) / pageSize) || 1;
      const scanPages = Math.min(scanPagesMax, totalPages);

      for (let pg = 1; pg <= scanPages; pg++) {
        const arr = await getPageItems(pid, pg);
        for (const it of arr) {
          const cats = getCategoriesForItem(pid, it) || [];
          const catId = cats[0] || "kat-multi";

          if (!buffers[catId]) buffers[catId] = [];
          buffers[catId].push({ pid, item: it });

          if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};
          if (!PARTNER_CATEGORY_ITEMS[pid][catId]) {
            PARTNER_CATEGORY_ITEMS[pid][catId] = [];
          }
          PARTNER_CATEGORY_ITEMS[pid][catId].push({ pid, item: it });
        }
      }
    })();

    partnerTasks.push(task);
  }

  await Promise.all(partnerTasks);

  const PAGE_SIZE = 6; // főoldali kategória 6 termék / lap (mixelt)
  const MAX_PAGES_PER_CAT = 5; // max 5 lap / kategória a főoldalon

  CATEGORY_IDS.forEach((catId) => {
    const rawList = buffers[catId] || [];
    const list = dedupeRowsStrong(rawList);
    const pages = [];

    for (
      let i = 0;
      i < list.length && pages.length < MAX_PAGES_PER_CAT;
      i += PAGE_SIZE
    ) {
      pages.push(list.slice(i, i + PAGE_SIZE));
    }

    CATEGORY_PAGES[catId] = pages;
    CATEGORY_CURRENT[catId] = pages.length ? 1 : 0;
  });
}

// ===== INIT =====
async function init() {
  try {
    attachScrollHandlers();
    attachNavHandlers();
    attachSearchForm();
    attachPartnerViewHandlers();

    await loadPartners();
    await loadCategoryMap(); // category-map.json belövése
    await buildAkciosBlokk(); // akciók + BF blokk
    await buildCategoryBlocks(); // főoldali kategória blokkok

    // FONTOS: első betöltéskor is rajzoljuk ki a főoldalt
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
// ===== partners.json betöltése =====
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

// ===== meta.json betöltése =====
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

// ===== page betöltése =====
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

// ===== Partner-alapú default kategória =====
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
  pepita: "kat-utazas",
  ekszereshop: "kat-szepseg",
  karacsonydekor: "kat-otthon",
  otthonmarket: "kat-otthon",
  onlinemarkabolt: "kat-otthon"
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

// ===== Fő kategóriák =====
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
  "kat-multi"
];

// ===== Termék → kategória meghatározás =====
function getCategoriesForItem(pid, it) {
  const cfg = PARTNERS.get(pid) || {};

  // 0) backend cat mező (Python)
  const backendCat =
    it &&
    (it.cat ||
      it.catid ||
      it.catId ||
      it.categoryId ||
      it.category_id ||
      null);

  if (backendCat && CATEGORY_IDS.includes(backendCat)) return [backendCat];

  // 1) category-map.json (ha talál a partner kulcsszót)
  const mapped = mapCategoryByPartner(pid, it);
  if (mapped && CATEGORY_IDS.includes(mapped)) return [mapped];

  // 2) partner alap kategória (pl. Tchibo → kat-otthon)
  const base = baseCategoryForPartner(pid, cfg);
  if (CATEGORY_IDS.includes(base)) return [base];

  // 3) alap fallback
  return ["kat-multi"];
}

// ===== Megjelenítés helper =====
function getPartnerName(pid) {
  const cfg = PARTNERS.get(pid);
  return (cfg && cfg.name) || pid;
}

function getCategoryName(catId) {
  const el = document.querySelector("#" + catId + " .section-header h2");
  return el ? el.textContent.trim() : "";
}
// ===== Akciós blokk =====
let AKCIO_PAGES = [];
let AKCIO_CURRENT = 1;

const DEFAULT_BF_SCAN_PAGES = 2;
const DEFAULT_BF_MIN_DISCOUNT = 10;

function renderAkcioCards(rows) {
  if (!rows || !rows.length)
    return '<div class="empty">Jelenleg nincs akciós ajánlat.</div>';

  return rows
    .map(({ pid, item }) => {
      const cfg = PARTNERS.get(pid);
      const img = itemImg(item);
      const raw = itemUrl(item);
      const price = priceText(item.price);
      const disc = getDiscountNumber(item);
      const partnerName = (cfg && cfg.name) || pid;

      return (
        '<div class="card">' +
        '<div class="thumb">' +
        (img
          ? `<img src="${img}" loading="lazy" decoding="async" style="max-width:100%;max-height:100%;object-fit:contain">`
          : "🛍️") +
        "</div>" +
        `<div class="title">${item.title || ""}</div>` +
        `<div class="price">${price}${disc ? " (-" + disc + "%)" : ""}</div>` +
        `<div class="partner">• ${partnerName}</div>` +
        (raw
          ? `<a class="btn-megnez akcios" href="${dlUrl(
              cfg ? cfg.deeplinkPartner : pid,
              raw
            )}" target="_blank" rel="nofollow sponsored noopener noreferrer">Megnézem🔗</a>`
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
      '<div class="empty">Jelenleg nincs akciós ajánlat.</div>';
    nav.innerHTML = "";
    return;
  }

  if (page < 1) page = 1;
  if (page > AKCIO_PAGES.length) page = AKCIO_PAGES.length;
  AKCIO_CURRENT = page;

  grid.innerHTML = renderAkcioCards(AKCIO_PAGES[page - 1]);

  nav.innerHTML =
    `<button class="btn-megnez" ${page <= 1 ? "disabled" : ""} onclick="window.akciokPager.go(${
      page - 1
    })">Előző</button>` +
    `<span style="align-self:center;font-size:13px;margin:0 8px;">${page}/${AKCIO_PAGES.length}</span>` +
    `<button class="btn-megnez" ${
      page >= AKCIO_PAGES.length ? "disabled" : ""
    } onclick="window.akciokPager.go(${page + 1})">Következő</button>`;

  window.akciokPager = { go: (p) => renderAkcioPage(p) };
}

async function buildAkciosBlokk() {
  const host = document.getElementById("akciok-grid");
  if (!host) return;

  host.innerHTML =
    '<div class="card"><div class="thumb">⏳</div><div class="title">Akciók betöltése…</div></div>';
  const nav = document.getElementById("akciok-nav");
  if (nav) nav.innerHTML = "";

  try {
    const collected = [];
    const tasks = [];

    for (const [pid, cfg] of PARTNERS.entries()) {
      const plc = cfg.placements || {};
      const anyEnabled = Object.values(plc).some(
        (v) => (v && v.enabled) || (v && v.full && v.full.enabled)
      );
      if (!anyEnabled) continue;

      tasks.push(
        (async () => {
          const bfCfg = cfg.bf || {};
          let scanPagesMax = parseInt(bfCfg.scanPages, 10);
          let minDiscount = parseInt(bfCfg.minDiscount, 10);

          if (!Number.isFinite(scanPagesMax) || scanPagesMax <= 0)
            scanPagesMax = DEFAULT_BF_SCAN_PAGES;
          if (!Number.isFinite(minDiscount) || minDiscount < 10)
            minDiscount = DEFAULT_BF_MIN_DISCOUNT;

          const meta = await getMeta(pid);
          const pageSize = meta.pageSize || 300;
          const totalPages =
            meta.pages || Math.ceil((meta.total || 0) / pageSize) || 1;
          const scanPages = Math.min(scanPagesMax, totalPages);

          for (let pg = 1; pg <= scanPages; pg++) {
            const arr = await getPageItems(pid, pg);
            for (const it of arr) {
              const d = getDiscountNumber(it);
              if (d !== null && d >= minDiscount)
                collected.push({ pid, item: it });
            }
          }
        })()
      );
    }

    await Promise.all(tasks);

    // dedupe → discount sort
    const ded = dedupeStrong(collected.map((r) => r.item));
    const back = new Map();

    collected.forEach((r) => {
      const key =
        basePath(stripVariantParams(itemUrl(r.item))) +
        "|" +
        imgPath(itemImg(r.item)) +
        "|" +
        normalizeTitleNoSize(r.item.title || "");
      if (!back.has(key)) back.set(key, r.pid);
    });

    const merged = ded
      .map((it) => {
        const key =
          basePath(stripVariantParams(itemUrl(it))) +
          "|" +
          imgPath(itemImg(it)) +
          "|" +
          normalizeTitleNoSize(it.title || "");
        return { pid: back.get(key), item: it };
      })
      .sort((a, b) => (getDiscountNumber(b.item) || 0) - (getDiscountNumber(a.item) || 0));

    // paginate
    const PAGE_SIZE = 12;
    AKCIO_PAGES = [];
    for (let i = 0; i < merged.length; i += PAGE_SIZE) {
      AKCIO_PAGES.push(merged.slice(i, i + PAGE_SIZE));
    }

    renderAkcioPage(1);

    // Black Friday blokk
    const bfHost = document.getElementById("bf-grid");
    if (bfHost) {
      const bf = merged.filter(({ item }) => {
        const t = ((item.title || "") + " " + (item.desc || "")).toLowerCase();
        return (
          t.includes("black friday") ||
          t.includes("black weekend") ||
          t.includes("blackweekend")
        );
      });

      bfHost.innerHTML = bf.length
        ? renderAkcioCards(bf.slice(0, 12))
        : '<div class="empty">Nincs kifejezetten Black Friday ajánlat.</div>';
    }
  } catch (e) {
    console.error("Akciós blokk hiba:", e);
    host.innerHTML =
      '<div class="empty">Hiba az akciók betöltése közben.</div>';
  }
}

// ===== Kategória blokkok (főoldal) =====
const CATEGORY_PAGES = {};
const CATEGORY_CURRENT = {};
window.catPager = window.catPager || {};

const PARTNER_CATEGORY_ITEMS = {};
const PARTNER_CATEGORY_LOAD_PROMISES = {};

async function buildCategoryBlocks() {
  const buffers = {};
  const scanPagesMax = 1; 

  const tasks = [];

  for (const [pid, cfg] of PARTNERS.entries()) {
    const plc = cfg.placements || {};
    const anyEnabled = Object.values(plc).some(
      (v) => (v && v.enabled) || (v && v.full && v.full.enabled)
    );
    if (!anyEnabled) continue;

    tasks.push(
      (async () => {
        const meta = await getMeta(pid);
        const totalPages = meta.pages || 1;
        const scanPages = Math.min(scanPagesMax, totalPages);

        for (let pg = 1; pg <= scanPages; pg++) {
          const arr = await getPageItems(pid, pg);

          for (const it of arr) {
            const cats = getCategoriesForItem(pid, it);
            const catId = cats[0] || "kat-multi";

            if (!buffers[catId]) buffers[catId] = [];
            buffers[catId].push({ pid, item: it });

            if (!PARTNER_CATEGORY_ITEMS[pid])
              PARTNER_CATEGORY_ITEMS[pid] = {};
            if (!PARTNER_CATEGORY_ITEMS[pid][catId])
              PARTNER_CATEGORY_ITEMS[pid][catId] = [];
            PARTNER_CATEGORY_ITEMS[pid][catId].push({ pid, item: it });
          }
        }
      })()
    );
  }

  await Promise.all(tasks);

  const PAGE_SIZE = 6;
  const MAX_PAGES_PER_CAT = 5;

  CATEGORY_IDS.forEach((catId) => {
    const list = dedupeRowsStrong(buffers[catId] || []);
    const pages = [];
    for (let i = 0; i < list.length && pages.length < MAX_PAGES_PER_CAT; i += PAGE_SIZE) {
      pages.push(list.slice(i, i + PAGE_SIZE));
    }
    CATEGORY_PAGES[catId] = pages;
    CATEGORY_CURRENT[catId] = pages.length ? 1 : 0;
  });
}

// ===== Partner nézet (20/lap) =====
let PARTNER_VIEW_STATE = {
  pid: null,
  catId: null,
  items: [],
  filtered: [],
  page: 1,
  pageSize: 20,
  sort: "default",
  query: "",
  loading: false
};

function applyPartnerFilters() {
  let arr = PARTNER_VIEW_STATE.items.slice();
  const q = PARTNER_VIEW_STATE.query.toLowerCase();

  if (q) {
    arr = arr.filter(({ item }) => {
      const t = (item.title || "").toLowerCase();
      const d = (item.desc || "").toLowerCase();
      return t.includes(q) || d.includes(q);
    });
  }

  const sort = PARTNER_VIEW_STATE.sort;
  if (sort === "name-asc" || sort === "name-desc") {
    arr.sort((a, b) => {
      const ta = (a.item.title || "").toLowerCase();
      const tb = (b.item.title || "").toLowerCase();
      if (ta < tb) return sort === "name-asc" ? -1 : 1;
      if (ta > tb) return sort === "name-asc" ? 1 : -1;
      return 0;
    });
  } else if (sort === "price-asc" || sort === "price-desc") {
    arr.sort((a, b) => {
      const pa = typeof a.item.price === "number" ? a.item.price : Infinity;
      const pb = typeof b.item.price === "number" ? b.item.price : Infinity;
      return sort === "price-asc" ? pa - pb : pb - pa;
    });
  }

  PARTNER_VIEW_STATE.filtered = arr;
}

function renderPartnerViewPage(page) {
  const grid = document.getElementById("partner-view-grid");
  const nav = document.getElementById("partner-view-nav");

  if (!PARTNER_VIEW_STATE.filtered || !PARTNER_VIEW_STATE.filtered.length) {
    grid.innerHTML = PARTNER_VIEW_STATE.loading
      ? '<div class="empty">Termékek betöltése…</div>'
      : '<div class="empty">Nincs találat.</div>';
    nav.innerHTML = "";
    return;
  }

  const total = PARTNER_VIEW_STATE.filtered.length;
  const pageSize = PARTNER_VIEW_STATE.pageSize;
  const maxPage = Math.ceil(total / pageSize);

  if (page < 1) page = 1;
  if (page > maxPage) page = maxPage;

  PARTNER_VIEW_STATE.page = page;

  const start = (page - 1) * pageSize;
  const slice = PARTNER_VIEW_STATE.filtered.slice(start, start + pageSize);

  grid.innerHTML = slice
    .map(({ pid, item }) => {
      const cfg = PARTNERS.get(pid);
      const img = itemImg(item);
      const price = priceText(item.price);
      const disc = getDiscountNumber(item);

      return (
        '<div class="card">' +
        `<div class="thumb">${
          img
            ? `<img src="${img}" loading="lazy" decoding="async" style="max-width:100%;max-height:100%;object-fit:contain">`
            : "🛍️"
        }</div>` +
        `<div class="title">${item.title}</div>` +
        `<div class="price">${price}${disc ? " (-" + disc + "%)" : ""}</div>` +
        `<a class="btn-megnez" href="${dlUrl(
          cfg.deeplinkPartner,
          itemUrl(item)
        )}" target="_blank" rel="nofollow sponsored noopener noreferrer">Megnézem🔗</a>` +
        "</div>"
      );
    })
    .join("");

  nav.innerHTML =
    `<button class="btn-megnez" ${page <= 1 ? "disabled" : ""} data-partner-page="${
      page - 1
    }">Előző</button>` +
    `<span style="align-self:center;font-size:13px;margin:0 8px;">${page}/${maxPage}</span>` +
    `<button class="btn-megnez" ${
      page >= maxPage ? "disabled" : ""
    } data-partner-page="${page + 1}">Következő</button>`;
}

async function hydratePartnerCategoryItems(pid, catId) {
  const key = pid + "||" + catId;
  if (PARTNER_CATEGORY_LOAD_PROMISES[key])
    return PARTNER_CATEGORY_LOAD_PROMISES[key];

  PARTNER_CATEGORY_LOAD_PROMISES[key] = (async () => {
    try {
      const cfg = PARTNERS.get(pid);
      if (!cfg) return;

      const meta = await getMeta(pid);
      const totalPages = meta.pages || 1;

      const all = [];

      for (let pg = 1; pg <= totalPages; pg++) {
        const arr = await getPageItems(pid, pg);
        for (const it of arr) {
          const cats = getCategoriesForItem(pid, it);
          if (cats.includes(catId)) all.push({ pid, item: it });
        }
      }

      const rows = dedupeRowsStrong(all);

      if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};
      PARTNER_CATEGORY_ITEMS[pid][catId] = rows;

      if (
        PARTNER_VIEW_STATE.pid === pid &&
        PARTNER_VIEW_STATE.catId === catId
      ) {
        PARTNER_VIEW_STATE.items = rows.slice();
        PARTNER_VIEW_STATE.loading = false;
        applyPartnerFilters();
        renderPartnerViewPage(PARTNER_VIEW_STATE.page);
      }
    } catch (e) {
      console.error("hydrate hiba:", pid, catId, e);
    } finally {
      delete PARTNER_CATEGORY_LOAD_PROMISES[key];
    }
  })();

  return PARTNER_CATEGORY_LOAD_PROMISES[key];
}

// ===== Partner view megnyitása =====
function openPartnerView(pid, catId) {
  const sec = document.getElementById("partner-view");
  const titleEl = document.getElementById("partner-view-title");
  const subEl = document.getElementById("partner-view-subtitle");

  const name = getPartnerName(pid);
  const catName = getCategoryName(catId);
  const baseItems =
    (PARTNER_CATEGORY_ITEMS[pid] &&
      PARTNER_CATEGORY_ITEMS[pid][catId]) ||
    [];

  PARTNER_VIEW_STATE = {
    pid,
    catId,
    items: baseItems.slice(),
    filtered: [],
    page: 1,
    pageSize: 20,
    sort: "default",
    query: "",
    loading: true
  };

  titleEl.textContent = `${name} – ${catName}`;
  subEl.textContent =
    "Betöltés folyamatban… (" + baseItems.length + " alap találat)";

  // Hero és fő blokkok eltüntetése
  ["hero", "catbar-wrap", "black-friday", "akciok"].forEach((id) => {
    const el = document.querySelector("." + id) || document.getElementById(id);
    if (el) el.classList.add("hidden");
  });

  CATEGORY_IDS.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.add("hidden");
  });

  sec.classList.remove("hidden");

  applyPartnerFilters();
  renderPartnerViewPage(1);

  hydratePartnerCategoryItems(pid, catId);
}

// ===== UI: kereső, szort, vissza, lapozó =====
function attachPartnerViewHandlers() {
  const search = document.getElementById("partner-search");
  const sort = document.getElementById("partner-sort");

  if (search) {
    search.addEventListener("input", () => {
      PARTNER_VIEW_STATE.query = search.value;
      applyPartnerFilters();
      renderPartnerViewPage(1);
    });
  }

  if (sort) {
    sort.addEventListener("change", () => {
      PARTNER_VIEW_STATE.sort = sort.value;
      applyPartnerFilters();
      renderPartnerViewPage(1);
    });
  }

  document.addEventListener("click", (e) => {
    const title = e.target.closest(".partner-block-title");
    if (title) {
      openPartnerView(
        title.getAttribute("data-partner"),
        title.getAttribute("data-cat")
      );
      return;
    }

    const back = e.target.closest(".btn-back-partner");
    if (back) {
      showCategoryOnly(PARTNER_VIEW_STATE.catId);
      return;
    }

    const home = e.target.closest(".btn-home-partner");
    if (home) {
      showAllSections();
      return;
    }

    const pager = e.target.closest("[data-partner-page]");
    if (pager) {
      const page = parseInt(pager.getAttribute("data-partner-page"), 10);
      renderPartnerViewPage(page);
    }
  });
}

// ===== Kategória nézet (felső menü) =====
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
  const rows = pages[page - 1];

  const groups = new Map();
  rows.forEach((r) => {
    if (!groups.has(r.pid)) groups.set(r.pid, []);
    groups.get(r.pid).push(r);
  });

  let html = "";
  const catName = getCategoryName(catId);

  groups.forEach((items, pid) => {
    const partnerName = getPartnerName(pid);
    const titleText = partnerName + (catName ? " – " + catName : "");

    html +=
      `<div class="partner-block" data-partner="${pid}" data-cat="${catId}">` +
      `<div class="partner-block-header">` +
      `<button type="button" class="partner-block-title" data-partner="${pid}" data-cat="${catId}">${titleText}</button>` +
      `</div>` +
      `<div class="grid partner-block-grid">` +
      renderAkcioCards(items) +
      `</div>` +
      `</div>`;
  });

  grid.innerHTML = html;

  nav.innerHTML =
    `<button class="btn-megnez" ${
      page <= 1 ? "disabled" : ""
    } onclick="window.catPager['${catId}'].go(${page - 1})">Előző</button>` +
    `<span style="align-self:center;font-size:13px;margin:0 8px;">${page}/${pages.length}</span>` +
    `<button class="btn-megnez" ${
      page >= pages.length ? "disabled" : ""
    } onclick="window.catPager['${catId}'].go(${page + 1})">Következő</button>`;

  window.catPager[catId] = { go: (p) => renderCategory(catId, p) };
}

function renderCategoryFull(catId) {
  const grid = document.getElementById(catId + "-grid");
  const nav = document.getElementById(catId + "-nav");
  if (!grid || !nav) return;

  let html = "";
  const catName = getCategoryName(catId);

  for (const [pid] of PARTNERS.entries()) {
    const arr =
      PARTNER_CATEGORY_ITEMS[pid] &&
      PARTNER_CATEGORY_ITEMS[pid][catId] &&
      PARTNER_CATEGORY_ITEMS[pid][catId].length
        ? PARTNER_CATEGORY_ITEMS[pid][catId]
        : null;

    if (!arr) continue;

    const first = arr.slice(0, 6);

    html +=
      `<div class="partner-block" data-partner="${pid}" data-cat="${catId}">` +
      `<div class="partner-block-header">` +
      `<button type="button" class="partner-block-title" data-partner="${pid}" data-cat="${catId}">${getPartnerName(pid)} – ${catName}</button>` +
      `</div>` +
      `<div class="grid partner-block-grid">` +
      renderAkcioCards(first) +
      `</div>` +
      `</div>`;
  }

  if (!html) {
    grid.innerHTML =
      '<div class="empty">Jelenleg nincs termék ebben a kategóriában.</div>';
    nav.innerHTML = "";
    return;
  }

  grid.innerHTML = html;
  nav.innerHTML = "";
}

// ===== Menü kattintás =====
function handleNavClick(event) {
  const btn = event.target.closest(".nav-btn[data-view]");
  if (!btn) return;

  const view = btn.getAttribute("data-view");

  if (view === "home") {
    showAllSections();
    return;
  }

  if (view === "category") {
    const catId = btn.getAttribute("data-cat");
    if (!catId) return;
    showCategoryOnly(catId);
  }
}

function attachNavHandlers() {
  document.addEventListener("click", handleNavClick);
}

// ===== Scroll fókusz =====
function smoothScrollTo(selector) {
  const el = document.querySelector(selector);
  if (!el) return;

  const y =
    el.getBoundingClientRect().top + window.scrollY - 70;

  window.scrollTo({
    top: y,
    behavior: "smooth"
  });
}

function handleScrollClick(event) {
  const t = event.target.closest("[data-scroll]");
  if (!t) return;

  event.preventDefault();
  const sel = t.getAttribute("data-scroll");
  if (sel) smoothScrollTo(sel);

  if (t.classList.contains("cat-pill")) {
    document
      .querySelectorAll(".cat-pill")
      .forEach((el) => el.classList.remove("active"));
    t.classList.add("active");
  }
}

function attachScrollHandlers() {
  document.addEventListener("click", handleScrollClick);
}

// ===== Hero kereső =====
function attachSearchForm() {
  const form = document.getElementById("searchFormAll");
  const input = document.getElementById("qAll");
  if (!form || !input) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = (input.value || "").trim();
    if (!q) return;

    window.location.href = "search.html?q=" + encodeURIComponent(q);
  });
}

// ===== Nézetváltás – főoldal vs kategória =====
function showCategoryOnly(catId) {
  ["hero", "catbar-wrap", "black-friday", "akciok"].forEach((sel) => {
    const el =
      document.querySelector("." + sel) ||
      document.getElementById(sel);
    if (el) el.classList.add("hidden");
  });

  const pv = document.getElementById("partner-view");
  if (pv) pv.classList.add("hidden");

  CATEGORY_IDS.forEach((id) => {
    const sec = document.getElementById(id);
    if (!sec) return;
    if (id === catId) sec.classList.remove("hidden");
    else sec.classList.add("hidden");
  });

  renderCategoryFull(catId);
  smoothScrollTo("#" + catId);
}

function showAllSections() {
  ["hero", "catbar-wrap", "black-friday", "akciok"].forEach((sel) => {
    const el =
      document.querySelector("." + sel) ||
      document.getElementById(sel);
    if (el) el.classList.remove("hidden");
  });

  const pv = document.getElementById("partner-view");
  if (pv) pv.classList.add("hidden");

  CATEGORY_IDS.forEach((id) => {
    const sec = document.getElementById(id);
    if (sec) sec.classList.remove("hidden");

    if (CATEGORY_PAGES[id] && CATEGORY_PAGES[id].length) {
      renderCategory(id, CATEGORY_CURRENT[id] || 1);
    }
  });

  smoothScrollTo("#akciok");
}

// ===== INIT =====
async function init() {
  try {
    attachScrollHandlers();
    attachNavHandlers();
    attachSearchForm();
    attachPartnerViewHandlers();

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
