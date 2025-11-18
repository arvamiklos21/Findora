// algolia_push.js
// Algolia index feltöltése Node.js-ből (GitHub Actions-ből futtatva)

// 1) Külső függőségek
const fs = require("fs");
const path = require("path");
const { algoliasearch } = require('algoliasearch');

// 2) Algolia config – alapértelmezésben env változókból olvasunk
const APP_ID = process.env.ALGOLIA_APP_ID || "W95VUS9HJ8";
const ADMIN_API_KEY =
  process.env.ALGOLIA_ADMIN_API_KEY || "IDE_NEM_HAGYUNK_ÉLES_KEYT";
const INDEX_NAME = process.env.ALGOLIA_INDEX_NAME || "findora_products";

// 3) Feedek helye a repo-ban
// Ha nálad a JSON-ok a docs/feeds/... alatt vannak (GitHub Pages),
// akkor így jó. Ha nem, akkor állítsd át pl. path.join(__dirname, "feeds")-re.
const FEEDS_ROOT = path.join(__dirname, "docs", "feeds");

// 4) Partnerek listája – ugyanaz, mint a partners.json-ból
const PARTNERS = [
  "tchibo",
  "cj-karcher",
  "cj-eoptika",
  "cj-jateknet",
  "jateksziget",
  "regiojatek",
  "decathlon",
  "alza",
  "kozmetikaotthon",
  "pepita",
  "ekszereshop",
  "karacsonydekor",
  "otthonmarket",
  "onlinemarkabolt",
];

// Kisegítő: biztonságos JSON betöltés
function readJsonSafe(p) {
  if (!fs.existsSync(p)) {
    return null;
  }
  try {
    const txt = fs.readFileSync(p, "utf8");
    return JSON.parse(txt);
  } catch (e) {
    console.error("[HIBA] JSON parse hiba:", p, e.message);
    return null;
  }
}

// Egy partner összes page-*.json fájljának beolvasása
function loadPartnerItems(partnerId, maxPages) {
  const partnerDir = path.join(FEEDS_ROOT, partnerId);
  if (!fs.existsSync(partnerDir)) {
    console.warn("[WARN] Nincs ilyen partner mappa:", partnerDir);
    return [];
  }

  const metaPath = path.join(partnerDir, "meta.json");
  let totalPages = null;
  const meta = readJsonSafe(metaPath);
  if (meta && typeof meta.pages === "number") {
    totalPages = meta.pages;
  }

  const items = [];
  let page = 1;

  while (true) {
    if (maxPages != null && page > maxPages) break;
    if (totalPages != null && page > totalPages) break;

    const pageName = `page-${String(page).padStart(4, "0")}.json`;
    const pagePath = path.join(partnerDir, pageName);
    if (!fs.existsSync(pagePath)) {
      // Ha elfogytak a fájlok, leállunk
      break;
    }

    const data = readJsonSafe(pagePath) || {};
    const pageItems = Array.isArray(data.items) ? data.items : [];

    for (const it of pageItems) {
      const url =
        (it.url || it.link || it.deeplink || "").toString().trim();
      const title = (it.title || "").toString().trim();
      const desc =
        (it.desc || it.description || "").toString().trim();

      if (!title && !url) {
        continue; // értelmetlen rekord
      }

      const baseId =
        it.id || url || `${partnerId}::no-url::${items.length}`;

      const record = {
        objectID: `${partnerId}::${baseId}`,
        partnerId: partnerId,
        title: title,
        description: desc,
        price: typeof it.price === "number" ? it.price : null,
        currency: it.currency || "HUF",
        image:
          it.image ||
          it.img ||
          it.image_link ||
          it.thumbnail ||
          "",
        url: url,
        category:
          it.category || it.google_product_category || "",
        discount:
          typeof it.discount === "number" ? it.discount : null,
      };

      items.push(record);
    }

    console.log(
      `[OK] ${partnerId} – ${pageName} beolvasva, ${pageItems.length} termék`
    );
    page += 1;
  }

  console.log(
    `[INFO] ${partnerId}: összesen ${items.length} termék a feedből`
  );
  return items;
}

async function main() {
  if (!ADMIN_API_KEY || ADMIN_API_KEY === "IDE_NEM_HAGYUNK_ÉLES_KEYT") {
    console.error(
      "[HIBA] Nincs beállítva ALGOLIA_ADMIN_API_KEY env változó. (GitHub Secrets-ben add meg!)"
    );
    process.exit(1);
  }

  console.log("[INFO] Algolia kliens inicializálása…");
  const client = algoliasearch(APP_ID, ADMIN_API_KEY);
  const index = client.initIndex(INDEX_NAME);

  let allRecords = [];
  for (const pid of PARTNERS) {
    const items = loadPartnerItems(pid);
    allRecords = allRecords.concat(items);
  }

  console.log(`[INFO] Összes Algolia rekord: ${allRecords.length}`);

  console.log("[INFO] Régi index törlése (clearObjects)…");
  await index.clearObjects();

  console.log("[INFO] Rekordok feltöltése Algoliába (batch)…");
  const BATCH = 1000;
  for (let i = 0; i < allRecords.length; i += BATCH) {
    const chunk = allRecords.slice(i, i + BATCH);
    await index.saveObjects(chunk);
    console.log(
      `[OK] ${i + chunk.length} / ${allRecords.length} rekord feltöltve`
    );
  }

  console.log("[DONE] Algolia index frissítve.");
}

main().catch((err) => {
  console.error("[FATAL] Algolia push hiba:", err);
  process.exit(1);
});

