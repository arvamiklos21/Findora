#!/usr/bin/env node

// ===========================
//  Algolia push – Findora
// ===========================
const fs = require("fs");
const path = require("path");
const algoliasearch = require("algoliasearch");

// --- env változók ---
const APP_ID = process.env.ALGOLIA_APP_ID;
const ADMIN_KEY = process.env.ALGOLIA_ADMIN_API_KEY;
const INDEX_NAME = process.env.ALGOLIA_INDEX_NAME || "findora_products";

if (!APP_ID || !ADMIN_KEY) {
  console.error(
    "[FATAL] Hiányzik ALGOLIA_APP_ID vagy ALGOLIA_ADMIN_API_KEY a környezeti változók közül."
  );
  process.exit(1);
}

// --- feed-ek beolvasása: docs/feeds/<partner>/page-*.json ---
function getFeedsRoot() {
  // Ez a script a docs mappában van, innen megyünk a feeds-hez
  return path.join(__dirname, "feeds");
}

function safeReadJson(filePath) {
  try {
    const txt = fs.readFileSync(filePath, "utf8");
    return JSON.parse(txt);
  } catch (e) {
    console.warn("[WARN] JSON hiba:", filePath, e.message);
    return null;
  }
}

function collectRecordsFromFeeds() {
  const FEEDS_ROOT = getFeedsRoot();
  const records = [];

  if (!fs.existsSync(FEEDS_ROOT)) {
    console.warn("[WARN] Nincs feeds könyvtár:", FEEDS_ROOT);
    return records;
  }

  const partners = fs
    .readdirSync(FEEDS_ROOT, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  console.log("[INFO] Partnerek a feeds alatt:", partners.join(", ") || "(nincs)");

  for (const pid of partners) {
    const dir = path.join(FEEDS_ROOT, pid);
    const files = fs
      .readdirSync(dir)
      .filter((f) => f.startsWith("page-") && f.endsWith(".json"))
      .sort();

    console.log(`[INFO]  Partner: ${pid}, lapok: ${files.length} db`);

    for (const file of files) {
      const full = path.join(dir, file);
      const json = safeReadJson(full);
      if (!json || !Array.isArray(json.items)) continue;

      for (const item of json.items) {
        const rawUrl =
          (item.url || item.link || item.deeplink || "").toString() || "";
        const title = (item.title || "").toString();
        const desc = (item.desc || "").toString();
        const img =
          item.image ||
          item.img ||
          item.image_link ||
          item.thumbnail ||
          "";

        const price =
          typeof item.price === "number" && isFinite(item.price)
            ? item.price
            : null;

        // objectID: stabil, partner + (id / sku / url / fallback)
        const objectID =
          `${pid}__` +
          (item.id ||
            item.sku ||
            rawUrl ||
            `${file}__${Math.random().toString(36).slice(2)}`);

        records.push({
          objectID,
          partner: pid,
          title,
          desc,
          price,
          url: rawUrl,
          image: img,
        });
      }
    }
  }

  return records;
}

async function main() {
  console.log("[INFO] Algolia kliens inicializálása…");
  console.log("[DEBUG] APP_ID:", APP_ID);
  console.log("[DEBUG] INDEX_NAME:", INDEX_NAME);

  // FONTOS: így kell hívni → két paraméter: appId, apiKey
  const client = algoliasearch(APP_ID, ADMIN_KEY);

  // Itt biztosan van initIndex – a korábbi hiba pont az volt,
  // hogy a client nem ilyen típusú objektum volt.
  const index = client.initIndex(INDEX_NAME);

  console.log("[INFO] Rekordok összegyűjtése a feeds mappából…");
  const records = collectRecordsFromFeeds();
  console.log("[INFO] Összes rekord:", records.length);

  if (!records.length) {
    console.log("[INFO] Nincs feltölthető rekord, kilépek.");
    return;
  }

  console.log("[INFO] replaceAllObjects futtatása Algolia-ban…");
  await index.replaceAllObjects(records, {
    autoGenerateObjectIDIfNotExist: true,
  });

  console.log("[OK] Algolia index sikeresen frissítve.");
}

main().catch((err) => {
  console.error("[FATAL] Algolia push hiba:", err);
  process.exit(1);
});
