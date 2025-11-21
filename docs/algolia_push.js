#!/usr/bin/env node

/**
 * Algolia index feltöltő script – Findora
 *
 * Helye: docs/algolia_push.js
 *
 * Környezeti változók (GitHub Actions-ben állítjuk):
 *   ALGOLIA_APP_ID          – Algolia Application ID (pl. WS9VUS9HJB)
 *   ALGOLIA_ADMIN_API_KEY   – Write API Key (SECRET-ben)
 *   ALGOLIA_INDEX_NAME      – pl. "findora_products" (ha nincs, erre esik vissza)
 *
 * A script a docs/feeds/<partner>/ mappákat olvassa:
 *   docs/feeds/tchibo/meta.json
 *   docs/feeds/tchibo/page-0001.json
 *   docs/feeds/tchibo/page-0002.json
 *   ...
 *
 * Minden item → 1 Algolia rekord.
 */

console.log("[INFO] Algolia kliens inicializálása…");

const fs = require("fs");
const path = require("path");
const algoliasearch = require("algoliasearch"); // v4-et használunk (workflow-ban így telepítjük)

// --- Környezeti változók ---
const APP_ID = process.env.ALGOLIA_APP_ID;
const ADMIN_KEY = process.env.ALGOLIA_ADMIN_API_KEY;
const INDEX_NAME = process.env.ALGOLIA_INDEX_NAME || "findora_products";

if (!APP_ID || !ADMIN_KEY) {
  console.error(
    "[FATAL] Hiányzik ALGOLIA_APP_ID vagy ALGOLIA_ADMIN_API_KEY a környezeti változók közül."
  );
  process.exit(1);
}

console.log("[DEBUG] APP_ID:", APP_ID);
console.log("[DEBUG] INDEX_NAME:", INDEX_NAME);

// --- Helper: JSON beolvasása biztonságosan ---
function readJsonSafe(filePath) {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    return JSON.parse(raw);
  } catch (e) {
    console.error("[ERROR] Nem sikerült beolvasni JSON-t:", filePath, e.message);
    return null;
  }
}

// --- Helper: létezik-e fájl ---
function fileExists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.F_OK);
    return true;
  } catch (_) {
    return false;
  }
}

// --- Algolia rekord építése egy feed itemből ---
function makeRecordFromItem(partnerId, partnerName, pageNumber, indexInPage, item) {
  const rec = {};

  // Stabil objectID: partnerId + oldalszám + index + (ha van) item.id
  const rawId =
    (item && (item.id || item.sku || item.code || item.productId)) || "";
  rec.objectID = `${partnerId}::p${String(pageNumber).padStart(4, "0")}::${indexInPage}::${rawId}`;

  // Partner mezők
  rec.partnerId = partnerId;
  rec.partnerName = partnerName || partnerId;
  rec.partner = partnerId; // Algolia facetinghez / filterhez (app.js-ben is használható)

  // Tipikus mezők – ha léteznek, átvesszük
  if (item.title) rec.title = item.title;
  if (item.name && !rec.title) rec.title = item.name;

  if (item.desc) rec.desc = item.desc;
  if (item.description && !rec.desc) rec.desc = item.description;

  if (typeof item.price !== "undefined") rec.price = item.price;
  if (typeof item.oldPrice !== "undefined") rec.oldPrice = item.oldPrice;
  if (typeof item.discount !== "undefined") rec.discount = item.discount;

  if (item.url || item.link || item.deeplink) {
    rec.url = item.url || item.link || item.deeplink;
  }

  if (item.image || item.img || item.image_link || item.thumbnail) {
    rec.image = item.image || item.img || item.image_link || item.thumbnail;
  }

  // Ha van kategória információ a feedben, megpróbáljuk átvenni
  if (item.categories) rec.categories = item.categories;
  if (item.category && !rec.categories) rec.categories = [item.category];

  // Backend findora_main / cat mezők – ezekre fogunk Algoliában facetezni / filterezni
  const backendCatRaw =
    (item && (item.findora_main || item.cat || item.catid || item.catId || item.categoryId || item.category_id)) ||
    null;

  if (backendCatRaw) {
    const backendCat = String(backendCatRaw).toLowerCase().trim();
    if (backendCat) {
      // két külön attribute, hogy a Dashboardon is kényelmes legyen:
      rec.findora_main = backendCat; // pl. elektronika, otthon, jatekok, stb.
      rec.cat = backendCat;          // app.js: filters: `cat:${backendKey}`
    }
  }

  // Eredeti categoryPath mentése, ha van – későbbi finomabb kategóriázáshoz
  if (item.categoryPath || item.category_path) {
    rec.categoryPath = item.categoryPath || item.category_path;
  }

  // Bármilyen extra mezőt opcionálisan átvehetsz itt később

  return rec;
}

async function main() {
  // Algolia kliens
  const client = algoliasearch(APP_ID, ADMIN_KEY);
  const index = client.initIndex(INDEX_NAME);

  const feedsRoot = path.join(__dirname, "feeds");
  console.log("[INFO] Feeds gyökér:", feedsRoot);

  if (!fs.existsSync(feedsRoot)) {
    console.error("[FATAL] A docs/feeds mappa nem létezik:", feedsRoot);
    process.exit(1);
  }

  // Partner mappák felderítése: docs/feeds/<partner>/
  const partnerDirs = fs
    .readdirSync(feedsRoot, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  if (!partnerDirs.length) {
    console.error("[FATAL] Nem találtam partner mappákat a docs/feeds alatt.");
    process.exit(1);
  }

  console.log("[INFO] Talált partner mappák:", partnerDirs.join(", "));

  const allRecords = [];
  let totalItems = 0;

  // Minden partner
  for (const pid of partnerDirs) {
    const partnerDir = path.join(feedsRoot, pid);
    const metaPath = path.join(partnerDir, "meta.json");

    if (!fileExists(metaPath)) {
      console.warn("[WARN] meta.json hiányzik, kihagyom partnert:", pid);
      continue;
    }

    const meta = readJsonSafe(metaPath);
    if (!meta) {
      console.warn("[WARN] meta.json hibás, kihagyom partnert:", pid);
      continue;
    }

    const partnerName = meta.partnerName || pid;
    const pageSize = meta.pageSize || 300;
    const total = meta.total || 0;
    const pages = meta.pages || (total && pageSize ? Math.ceil(total / pageSize) : 1);

    console.log(
      `[INFO] Partner: ${pid} (${partnerName}) – total=${total}, pages=${pages}, pageSize=${pageSize}`
    );

    // Végigmegyünk az összes oldalon
    for (let pg = 1; pg <= pages; pg++) {
      const fileName = `page-${String(pg).padStart(4, "0")}.json`;
      const pagePath = path.join(partnerDir, fileName);
      if (!fileExists(pagePath)) {
        console.warn("[WARN] Hiányzó oldal, továbblépek:", pagePath);
        continue;
      }

      const pageJson = readJsonSafe(pagePath);
      if (!pageJson || !Array.isArray(pageJson.items)) {
        console.warn("[WARN] Hibás vagy üres page JSON:", pagePath);
        continue;
      }

      const items = pageJson.items;
      console.log(
        `[DEBUG] Partner ${pid}, ${fileName} – ${items.length} db termék`
      );

      items.forEach((item, idx) => {
        const rec = makeRecordFromItem(pid, partnerName, pg, idx, item);
        allRecords.push(rec);
        totalItems += 1;
      });
    }
  }

  console.log("[INFO] Összes rekord, amit Algoliára küldünk:", totalItems);

  if (!allRecords.length) {
    console.error("[FATAL] Nincs egyetlen rekord sem, nincs mit feltölteni.");
    process.exit(1);
  }

  // Először tisztítjuk az indexet
  console.log("[INFO] Régi index tartalom törlése (clearObjects)...");
  await index.clearObjects();

  // Mentés batch-ekben (pl. 1000-es csomagok)
  const batchSize = 1000;
  let from = 0;
  let batchIndex = 1;

  while (from < allRecords.length) {
    const to = Math.min(from + batchSize, allRecords.length);
    const batch = allRecords.slice(from, to);
    console.log(
      `[INFO] Mentés Algoliára – batch ${batchIndex}, rekordok: ${from}–${to - 1}`
    );

      await index.saveObjects(batch, {
      autoGenerateObjectIDIfNotExist: false,
    });

    from = to;
    batchIndex += 1;
  }

  console.log("[INFO] Algolia index feltöltése sikeresen lefutott.");
}

main().catch((err) => {
  console.error("[FATAL] Algolia push hiba:", err);
  process.exit(1);
});
