// ===== Alap URL-ek =====
const FEEDS_BASE = "";
const PARTNERS_URL = "feeds/partners.json";

// ===== Meilisearch =====
const MEILI_HOST = "https://meili.findora.hu"; // NINCS :7700!
const MEILI_INDEX_UID = "products_all";
const MEILI_HEADERS = {
  "Content-Type": "application/json",
  // FIGYELEM: élesben ezt kereső kulcsra cseréld!
  "Authorization": "Bearer FINDORA_MASTER_KEY_123",
};

async function meiliSearch(params) {
  const body = {
    q: params.q || "",
    limit: typeof params.limit === "number" ? params.limit : 20,
    offset: typeof params.offset === "number" ? params.offset : 0,
  };

  if (params.filter) {
    body.filter = params.filter;
  }
  if (params.sort) {
    // pl. "price:asc"
    body.sort = [params.sort];
  }

  const res = await fetch(`${MEILI_HOST}/indexes/${MEILI_INDEX_UID}/search`, {
    method: "POST",
    headers: MEILI_HEADERS,
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    throw new Error(
      "Meilisearch hiba: " + res.status + " " + (await res.text())
    );
  }
  return res.json(); // { hits, estimatedTotalHits, ... }
}

// ===== Meili: összes találat letöltése offset lapozással (NINCS KORLÁT) =====
async function meiliFetchAll(params, opts = {}) {
  const pageSize = typeof opts.pageSize === "number" ? opts.pageSize : 1000;

  let offset = 0;
  let all = [];

  while (true) {
    const res = await meiliSearch({
      q: params.q || "",
      filter: params.filter,
      sort: params.sort,
      limit: pageSize,
      offset,
    });

    const hits = res.hits || [];
    if (!hits.length) break;

    all.push(...hits);
    offset += hits.length;

    // Ha kevesebb jött, mint a pageSize, akkor elfogyott
    if (hits.length < pageSize) break;
  }

  return all;
}

// ===== PARTNEREK =====
const PARTNERS = new Map();

// partners.json – id, name, deeplinkPartner, stb.
async function loadPartners() {
  const r = await fetch(PARTNERS_URL, { cache: "no-cache" });
  if (!r.ok) throw new Error("partners.json nem elérhető: " + r.status);
  const arr = await r.json();
  if (!Array.isArray(arr) || !arr.length) {
    throw new Error("partners.json üres vagy hibás");
  }
  PARTNERS.clear();
  arr.forEach((p) => {
    if (!p.id || !p.deeplinkPartner) return;
    PARTNERS.set(p.id, p);
  });
  console.log("PARTNEREK BETÖLTVE:", PARTNERS.size);
}

function getPartnerName(pid) {
  const cfg = PARTNERS.get(pid);
  return (cfg && cfg.name) || pid;
}

// ===== Deeplink =====
function dlUrl(pid, rawUrl) {
  if (!rawUrl) return "#";
  return FEEDS_BASE + "/api/dl?u=" + encodeURIComponent(rawUrl) + "&p=" + pid;
}

// ===== Helper =====
function priceText(v) {
  if (typeof v === "number" && isFinite(v)) return v.toLocaleString("hu-HU") + " Ft";
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
    .replace(/\b(?:szín|szin|color)\s*[:\-]?\s*[a-záéíóöőúüű0-9\-]+/gi, " ")
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

// ===== Discount / akció =====
function getDiscountNumber(it) {
  if (it && typeof it.discount === "number" && isFinite(it.discount)) {
    const d = Math.round(it.discount);
    if (d >= 10 && d <= 90) return d;
  }
  return null;
}

function getAkcioPrices(it) {
  if (!it) return { current: null, original: null };

  let current = null;

  if (typeof it.price === "number" && isFinite(it.price)) {
    current = it.price;
  } else if (typeof it.sale_price === "number" && isFinite(it.sale_price)) {
    current = it.sale_price;
  }

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

  const disc = getDiscountNumber(it);
  if (!original && current && disc !== null) {
    const base = current / (1 - disc / 100);
    if (isFinite(base) && base > 0) {
      original = Math.round(base);
    }
  }

  return { current, original };
}

// ===== KATEGÓRIA KONFIG =====
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

// backend slug (findora_main) → kat-* ID
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

// CATID → backend slug (amit a Meili-ben a "category" mezőben használunk)
const CATID_TO_BACKEND = {};
Object.entries(BACKEND_SYNONYM_TO_CATID).forEach(([backendKey, catId]) => {
  CATID_TO_BACKEND[catId] = backendKey;
});

// ===== Akciók állapot =====
let AKCIO_PAGES = [2];
let AKCIO_CURRENT = 1;
let AKCIO_FULL_STATE = {
  items: [],
  page: 1,
  pageSize: 20,
};

// ===== Kategória állapot =====
const CATEGORY_PAGES = {};
const CATEGORY_CURRENT = {};
window.catPager = window.catPager || {};

const PARTNER_CATEGORY_ITEMS = {}; // Meili-ből töltjük fel
const FULL_CATEGORY_STATE = {
  catId: null,
  items: [],
  page: 1,
  pageSize: 20,
};
window.fullCatPager = window.fullCatPager || {};

// ===== PARTNER VIEW STATE =====
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

// ===== Render helper =====
function getCategoryName(catId) {
  const el = document.querySelector("#" + catId + " .section-header h2");
  return el ? el.textContent.trim() : "";
}

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
      const currentText = priceText(prices.current != null ? prices.current : item && item.price);
      const originalText = prices.original != null ? priceText(prices.original) : null;

      const partnerName = (cfg && cfg.name) || pid;

      let priceHtml = "";

      if (originalText && currentText && prices.original !== prices.current) {
        priceHtml =
          '<div class="price">' +
          '<span class="old-price" style="text-decoration:line-through;opacity:0.7;margin-right:4px;">' +
          originalText +
          "</span>" +
          '<span class="new-price" style="font-weight:bold;margin-right:4px;">' +
          currentText +
          "</span>" +
          (disc
            ? '<span class="disc" style="color:#c00;font-weight:bold;">-' + disc + "%</span>"
            : "") +
          "</div>";
      } else {
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
    grid.innerHTML = '<div class="empty">Jelenleg nem találtunk akciós ajánlatot.</div>';
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
    grid.innerHTML = '<div class="empty">Jelenleg nem találtunk akciós ajánlatot.</div>';
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

// ===== AKCIÓS BLOKK – Meiliből (NINCS KORLÁT) =====
async function buildAkciosBlokk() {
  const host = document.getElementById("akciok-grid");
  if (!host) return;

  const nav = document.getElementById("akciok-nav");
  host.innerHTML =
    '<div class="card"><div class="thumb">⏳</div><div class="title">Akciók betöltése…</div></div>';
  if (nav) nav.innerHTML = "";

  try {
    // Meiliben: discount >= 10, csökkenő sorrendben – NINCS limit: lapozva mindet lehúzzuk
    const hits = await meiliFetchAll(
      {
        q: "",
        filter: "discount >= 10",
        sort: "discount:desc",
      },
      { pageSize: 1000 }
    );

    if (!hits.length) {
      host.innerHTML = '<div class="empty">Jelenleg nem találtunk akciós ajánlatot.</div>';
      if (nav) nav.innerHTML = "";
      const bfGrid = document.getElementById("bf-grid");
      if (bfGrid) {
        bfGrid.innerHTML =
          '<div class="empty">Jelenleg nincs kifejezetten Black Friday / Black Weekend jelölésű ajánlat.</div>';
      }
      return;
    }

    const rows = hits.map((item) => ({
      pid: item.partner || "ismeretlen",
      item,
    }));

    const dedRows = dedupeRowsStrong(rows);

    AKCIO_FULL_STATE.items = dedRows;
    AKCIO_FULL_STATE.page = 1;

    const PREVIEW_PAGE_SIZE = 12;
    const MAX_PREVIEW_PAGES = 2;

    AKCIO_PAGES = [];
    for (let i = 0; i < dedRows.length && AKCIO_PAGES.length < MAX_PREVIEW_PAGES; i += PREVIEW_PAGE_SIZE) {
      AKCIO_PAGES.push(dedRows.slice(i, i + PREVIEW_PAGE_SIZE));
    }

    renderAkcioPage(1);

    // Black Friday blokk
    const bfGrid = document.getElementById("bf-grid");
    if (bfGrid) {
      const bfItems = dedRows.filter(({ item }) => {
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
    host.innerHTML = '<div class="empty">Hiba történt az akciók betöltése közben.</div>';
    if (nav) nav.innerHTML = "";
    const bfGrid = document.getElementById("bf-grid");
    if (bfGrid) {
      bfGrid.innerHTML = '<div class="empty">Hiba történt a Black Friday ajánlatok betöltése közben.</div>';
    }
  }
}

// ===== Kategória kártyák =====
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

// ===== FŐOLDALI kategória blokkok – Meiliből (partnerenként) =====
async function buildCategoryBlocks() {
  const PAGE_SIZE_PER_PARTNER = 3;
  // NINCS KORLÁT: mindent lehúzunk Meiliből (offset lapozással)

  // Állapot nullázása
  CATEGORY_IDS.forEach((catId) => {
    CATEGORY_PAGES[catId] = [];
    CATEGORY_CURRENT[catId] = 0;
  });
  Object.keys(PARTNER_CATEGORY_ITEMS).forEach((k) => {
    delete PARTNER_CATEGORY_ITEMS[k];
  });

  // catId → pid → [] sorok
  const categoryBuckets = {};
  CATEGORY_IDS.forEach((catId) => {
    categoryBuckets[catId] = {};
  });

  // PARTNERS Map-ből megyünk végig az összes bekötött partneren
  for (const [pid] of PARTNERS.entries()) {
    try {
      // 1) partner összes terméke (NINCS LIMIT)
      const hits = await meiliFetchAll(
        {
          q: "",
          filter: `partner = "${pid}"`,
        },
        { pageSize: 1000 }
      );

      if (!hits.length) continue;

      const rows = hits.map((item) => ({
        pid: item.partner || pid,
        item,
      }));

      // erős dedupe partner szinten
      const dedRows = dedupeRowsStrong(rows);

      if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};

      // 2) szétosztjuk kategóriákra
      dedRows.forEach((row) => {
        const it = row.item || {};
        const catSlug = it.category || it.findora_main || it.cat || "multi"; // backend slug (pl. "jatekok")

        const catId = BACKEND_SYNONYM_TO_CATID[catSlug];
        if (!catId) return; // olyan kategória, amit a főoldal nem mutat

        // globális partner-kategória mátrix (partner view-hoz is)
        if (!PARTNER_CATEGORY_ITEMS[pid][catId]) {
          PARTNER_CATEGORY_ITEMS[pid][catId] = [];
        }
        PARTNER_CATEGORY_ITEMS[pid][catId].push(row);

        // főoldali kategória-bucket
        if (!categoryBuckets[catId][pid]) {
          categoryBuckets[catId][pid] = [];
        }
        categoryBuckets[catId][pid].push(row);
      });
    } catch (e) {
      console.error("buildCategoryBlocks hiba partnernél:", pid, e);
    }
  }

  // 3) kategóriánként lapokra vágjuk: minden partnernek 3-3 termék / oldal
  for (const catId of CATEGORY_IDS) {
    const perPartner = categoryBuckets[catId];
    const partnerIds = Object.keys(perPartner || {});
    if (!partnerIds.length) {
      CATEGORY_PAGES[catId] = [];
      CATEGORY_CURRENT[catId] = 0;
      continue;
    }

    const partnerPages = {};
    let maxPagesForCat = 0;

    partnerIds.forEach((pid) => {
      const list = perPartner[pid] || [];
      if (!list.length) return;

      const pages = [];
      for (let i = 0; i < list.length; i += PAGE_SIZE_PER_PARTNER) {
        pages.push(list.slice(i, i + PAGE_SIZE_PER_PARTNER));
      }

      if (pages.length) {
        partnerPages[pid] = pages;
        if (pages.length > maxPagesForCat) {
          maxPagesForCat = pages.length;
        }
      }
    });

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
  }
}

function renderCategory(catId, page) {
  const grid = document.getElementById(catId + "-grid");
  const nav = document.getElementById(catId + "-nav");
  if (!grid || !nav) return;

  const pages = CATEGORY_PAGES[catId] || [];
  if (!pages.length) {
    grid.innerHTML = '<div class="empty">Jelenleg nincs termék ebben a kategóriában.</div>';
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

// ===== FULL kategória (20/lap) – Meiliből =====
async function buildFullCategoryState(catId) {
  const backendSlug = CATID_TO_BACKEND[catId];
  if (!backendSlug) {
    FULL_CATEGORY_STATE.catId = catId;
    FULL_CATEGORY_STATE.items = [];
    FULL_CATEGORY_STATE.page = 1;
    return;
  }

  try {
    // NINCS limit: mindet lehúzzuk Meiliből
    const hits = await meiliFetchAll(
      {
        q: "",
        filter: `category = "${backendSlug}"`,
      },
      { pageSize: 1000 }
    );

    const rows = hits.map((item) => ({
      pid: item.partner || "ismeretlen",
      item,
    }));

    FULL_CATEGORY_STATE.catId = catId;
    FULL_CATEGORY_STATE.items = dedupeRowsStrong(rows);
    FULL_CATEGORY_STATE.page = 1;
  } catch (e) {
    console.error("buildFullCategoryState hiba:", catId, e);
    FULL_CATEGORY_STATE.catId = catId;
    FULL_CATEGORY_STATE.items = [];
    FULL_CATEGORY_STATE.page = 1;
  }
}

function renderFullCategoryPage(catId, page) {
  const grid = document.getElementById(catId + "-grid");
  const nav = document.getElementById(catId + "-nav");
  if (!grid || !nav) return;

  if (FULL_CATEGORY_STATE.catId !== catId) {
    grid.innerHTML = '<div class="empty">Betöltés folyamatban…</div>';
    nav.innerHTML = "";
    return;
  }

  const total = FULL_CATEGORY_STATE.items.length;
  if (!total) {
    grid.innerHTML = '<div class="empty">Jelenleg nincs termék ebben a kategóriában.</div>';
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

// ===== PARTNER VIEW – keresés, rendezés, lapozás =====
function updatePartnerSubtitle() {
  const subEl = document.getElementById("partner-view-subtitle");
  if (!subEl || !PARTNER_VIEW_STATE.pid || !PARTNER_VIEW_STATE.catId) return;

  const name = getPartnerName(PARTNER_VIEW_STATE.pid);
  const catName = getCategoryName(PARTNER_VIEW_STATE.catId);
  const total = (PARTNER_VIEW_STATE.filtered && PARTNER_VIEW_STATE.filtered.length) || 0;

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
      const dd = ((item && item.description) || "").toLowerCase();
      return t.includes(q) || d.includes(q) || dd.includes(q);
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
      const pa = a.item && typeof a.item.price === "number" ? a.item.price : Infinity;
      const pb = b.item && typeof b.item.price === "number" ? b.item.price : Infinity;
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
      grid.innerHTML = '<div class="empty">Nincs találat ennél a partnernél.</div>';
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

// Meili-ből tölti a partner + kategória összes termékét (NINCS KORLÁT)
async function hydratePartnerCategoryItems(pid, catId) {
  if (!pid || !catId) return;

  const backendSlug = CATID_TO_BACKEND[catId];
  if (!backendSlug) {
    if (PARTNER_VIEW_STATE.pid === pid && PARTNER_VIEW_STATE.catId === catId) {
      PARTNER_VIEW_STATE.loading = false;
      PARTNER_VIEW_STATE.items = [];
      applyPartnerFilters();
      renderPartnerViewPage(1);
    }
    return;
  }

  if (!PARTNER_CATEGORY_ITEMS[pid]) PARTNER_CATEGORY_ITEMS[pid] = {};
  if (PARTNER_CATEGORY_ITEMS[pid][catId] && PARTNER_CATEGORY_ITEMS[pid][catId].length) {
    if (PARTNER_VIEW_STATE.pid === pid && PARTNER_VIEW_STATE.catId === catId) {
      PARTNER_VIEW_STATE.loading = false;
      PARTNER_VIEW_STATE.items = PARTNER_CATEGORY_ITEMS[pid][catId].slice();
      applyPartnerFilters();
      renderPartnerViewPage(PARTNER_VIEW_STATE.page || 1);
    }
    return;
  }

  try {
    // NINCS limit: mindet lehúzzuk Meiliből
    const hits = await meiliFetchAll(
      {
        q: "",
        filter: `partner = "${pid}" AND category = "${backendSlug}"`,
      },
      { pageSize: 1000 }
    );

    const rows = hits.map((item) => ({
      pid: item.partner || pid,
      item,
    }));
    const ded = dedupeRowsStrong(rows);

    PARTNER_CATEGORY_ITEMS[pid][catId] = ded;

    if (PARTNER_VIEW_STATE.pid === pid && PARTNER_VIEW_STATE.catId === catId) {
      PARTNER_VIEW_STATE.loading = false;
      PARTNER_VIEW_STATE.items = ded.slice();
      applyPartnerFilters();
      renderPartnerViewPage(PARTNER_VIEW_STATE.page || 1);
    }
  } catch (e) {
    console.error("hydratePartnerCategoryItems hiba:", pid, catId, e);
    if (PARTNER_VIEW_STATE.pid === pid && PARTNER_VIEW_STATE.catId === catId) {
      PARTNER_VIEW_STATE.loading = false;
      PARTNER_VIEW_STATE.items = [];
      applyPartnerFilters();
      renderPartnerViewPage(1);
    }
  }
}

function openPartnerView(pid, catId) {
  const sec = document.getElementById("partner-view");
  const titleEl = document.getElementById("partner-view-title");
  const subEl = document.getElementById("partner-view-subtitle");
  if (!sec || !titleEl || !subEl) return;

  const name = getPartnerName(pid);
  const catName = getCategoryName(catId);

  const itemsForCombo = (PARTNER_CATEGORY_ITEMS[pid] && PARTNER_CATEGORY_ITEMS[pid][catId]) || [];

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

// ===== KATEGÓRIA nézet (csak ez a kategória) =====
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

// FULL kategória – 20/lap, Meiliből
async function showFullCategoryList(catId) {
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

  const grid = document.getElementById(catId + "-grid");
  const nav = document.getElementById(catId + "-nav");
  if (grid) {
    grid.innerHTML = '<div class="empty">Betöltés folyamatban…</div>';
  }
  if (nav) nav.innerHTML = "";

  await buildFullCategoryState(catId);
  renderFullCategoryPage(catId, 1);
  smoothScrollTo("#" + catId);
}

// ===== Hero kereső → search.html (Meili-re átírható ott) =====
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

// ===== Scroll helper =====
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

// ===== Felső nav =====
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

function handleNavClick(event) {
  const btn = event.target.closest(".nav-btn[data-view]");
  if (!btn) return;

  const view = btn.getAttribute("data-view");

  if (view === "home") {
    event.preventDefault();
    showAllSections();
    return;
  }

  if (view === "akciok") {
    event.preventDefault();
    showAkcioOnly();
    return;
  }

  if (view === "category") {
    const catId = btn.getAttribute("data-cat");
    if (!catId) return;
    event.preventDefault();
    showCategoryOnly(catId);
    return;
  }

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

// ===== Partner view UI eventek =====
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

// ===== Akció cím kattintás: teljes 20/lap nézet =====
function attachAkcioTitleHandler() {
  const title = document.querySelector("#akciok .section-header h2");
  if (!title) return;
  title.style.cursor = "pointer";
  title.addEventListener("click", function () {
    showAkcioOnly();
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
    // category-map.json itt már nem kell, minden kategóriát a Meili "category" mező ad
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
