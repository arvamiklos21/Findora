// docs/algolia_push.js
//
// Findora → Algolia index frissítés (FULL REBUILD)
//
// - Beolvassa az összes partner feedet a docs/feeds/* mappákból
// - Összefűzi az itemeket egységes struktúrába
// - Feltölti az Algolia indexbe (findora_products)
// - Kategória mező mindig: "kat" / "findora_main"
//   (Algolia faceting ezt keresi!)

const fs = require("fs");
const path = require("path");
const algoliasearch = require("algoliasearch");

const APP_ID = process.env.ALGOLIA_APP_ID;
const API_KEY = process.env.ALGOLIA_ADMIN_API_KEY;
const INDEX_NAME = process.env.ALGOLIA_INDEX_NAME || "findora_products";

if (!APP_ID || !API_KEY) {
  console.error("❌ ALGOLIA_APP_ID vagy ALGOLIA_ADMIN_API_KEY hiányzik (GitHub Secrets).");
  process.exit(1);
}

const client = algoliasearch(APP_ID, API_KEY);
const index = client.initIndex(INDEX_NAME);

const FEEDS_DIR = path.join(__dirname, "feeds");

// --- helpers ---

function toNumber(v) {
  if (typeof v === "number" && isFinite(v)) return v;
  if (typeof v === "string") {
    const s = v.replace(/\s/g, "").replace(",", ".");
    const n = Number(s);
    return isFinite(n) ? n : null;
  }
  return null;
}

// ár-normalizáló: current + original + discount
function normalizePrices(it) {
  if (!it || typeof it !== "object") {
    return {
      currentPrice: null,
      originalPrice: null,
      discount: null,
      sale_price: null,
      old_price: null,
      price_old: null,
      original_price: null,
      list_price: null,
      regular_price: null,
    };
  }

  const sale_price = toNumber(it.sale_price);
  const base_price = toNumber(it.price);
  const old_price = toNumber(it.old_price);
  const price_old = toNumber(it.price_old);
  const original_price = toNumber(it.original_price);
  const list_price = toNumber(it.list_price);
  const regular_price = toNumber(it.regular_price);

  // aktuális ár: preferált sorrend: sale_price → price
  let currentPrice = null;
  if (sale_price != null) currentPrice = sale_price;
  else if (base_price != null) currentPrice = base_price;

  // potenciális "eredeti" ár jelöltek
  const originals = [
    old_price,
    price_old,
    original_price,
    list_price,
    regular_price,
  ].filter((v) => v != null);

  let originalPrice = null;
  if (originals.length) {
    // vegyük a legnagyobbat a jelöltek közül – tipikusan ez a "régi ár"
    originalPrice = originals.reduce((max, v) => (v > max ? v : max), originals[0]);
  }

  // discount a feedből
  let discount = null;
  if (typeof it.discount === "number" && isFinite(it.discount)) {
    discount = Math.round(it.discount);
  }

  // ha nincs discount, de van current + original → számoljuk
  if (discount == null && currentPrice != null && originalPrice != null && originalPrice > currentPrice) {
    const ratio = 1 - currentPrice / originalPrice;
    const d = Math.round(ratio * 100);
    if (d >= 1 && d <= 90) {
      discount = d;
    }
  }

  return {
    currentPrice,
    originalPrice,
    discount,
    sale_price,
    old_price,
    price_old,
    original_price,
    list_price,
    regular_price,
  };
}

// Biztonságos JSON olvasó
function readJsonSafe(p) {
  try {
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch (e) {
    console.error("❌ JSON olvasási hiba:", p, e.message);
    return null;
  }
}

// Összes partner feed beolvasása
function loadAllItems() {
  if (!fs.existsSync(FEEDS_DIR)) {
    console.error("❌ Hiányzik mappa:", FEEDS_DIR);
    process.exit(1);
  }

  const partnerDirs = fs
    .readdirSync(FEEDS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  let all = [];

  for (const pdir of partnerDirs) {
    const full = path.join(FEEDS_DIR, pdir);
    const meta = readJsonSafe(path.join(full, "meta.json")) || {};
    const partnerId = meta.partner || pdir;

    console.log(`→ Partner: ${partnerId}`);

    const files = fs
      .readdirSync(full)
      .filter((fn) => /^page-\d+\.json$/i.test(fn))
      .sort();

    let c = 0;

    for (const fn of files) {
      const page = readJsonSafe(path.join(full, fn));
      if (!page || !Array.isArray(page.items)) continue;

      for (const it of page.items) {
        const id =
          it.id ||
          it.sku ||
          it.url ||
          it.title ||
          `${partnerId}-${c}`;

        // Kép
        const image =
          it.img ||
          it.image ||
          it.image_url ||
          it.image_link ||
          it.g_image_link ||
          "";

        // Kategória
        const kat =
          it.kat ||
          it.cat ||
          it.findora_main ||
          null;

        // categoryPath
        const categoryPath =
          it.categoryPath ||
          it.category_path ||
          it.category ||
          "";

        // árak + kedvezmény normalizálása
        const np = normalizePrices(it);

        const obj = {
          objectID: `${partnerId}::${id}`,
          title: it.title || "",
          desc: it.desc || "",
          // Algolia fő ármező: mindig a currentPrice (ha van), különben a nyers it.price
          price: np.currentPrice != null ? np.currentPrice : (it.price ?? null),

          // kedvezmény: feed-ből vagy számolva
          discount: np.discount != null ? np.discount : (it.discount ?? null),

          // nyers ármezők is menjenek, hogy a frontend tudjon velük számolni
          sale_price: np.sale_price,
          old_price: np.old_price,
          price_old: np.price_old,
          original_price: np.original_price,
          list_price: np.list_price,
          regular_price: np.regular_price,

          url: it.url || "",
          image,
          partner: partnerId,
          partnerId,
          partnerName: partnerId,

          // kategória mezők – ezekre épít az app.js
          kat,
          findora_main: kat,
          categoryPath,
        };

        all.push(obj);
        c++;
      }
    }

    console.log(`   ${c} db termék beolvasva.`);
  }

  console.log(`Összes feltöltendő tárgy: ${all.length}`);
  return all;
}

async function main() {
  const records = loadAllItems();
  if (!records.length) {
    console.error("❌ Nincs rekord.");
    process.exit(1);
  }

  console.log("Algolia index törlése…");
  await index.clearObjects();

  const chunkSize = 5000;
  for (let i = 0; i < records.length; i += chunkSize) {
    const chunk = records.slice(i, i + chunkSize);
    console.log(`   Mentés chunk ${(i / chunkSize) + 1} (${chunk.length} rekord)…`);
    await index.saveObjects(chunk);
  }

  console.log("✅ Kész. Algolia index frissítve.");
}

main().catch((err) => {
  console.error("❌ Hiba:", err);
  process.exit(1);
});
