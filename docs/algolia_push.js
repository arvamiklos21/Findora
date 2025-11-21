// docs/algolia_push.js
//
// Findora → Algolia index frissítés
// - Beolvassa az összes partner feedet a docs/feeds/* mappákból
// - Összefűzi az itemeket
// - Feltölti az Algolia indexbe (findora_products)
// - Egységes mezők: title, desc, price, discount, url, image, partnerId, partnerName, cat, findora_main, categoryPath

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

/**
 * Segédfüggvény: biztonságos olvasás JSON-hoz
 */
function readJsonSafe(p) {
  try {
    const txt = fs.readFileSync(p, "utf8");
    return JSON.parse(txt);
  } catch (e) {
    console.error("Nem sikerült beolvasni JSON-t:", p, e.message);
    return null;
  }
}

/**
 * Összes partner feed beolvasása
 * Struktúra: docs/feeds/<partner>/page-0001.json, meta.json, stb.
 */
function loadAllItems() {
  const partners = [];
  if (!fs.existsSync(FEEDS_DIR)) {
    console.error("❌ FEEDS_DIR nem létezik:", FEEDS_DIR);
    process.exit(1);
  }

  const partnerDirs = fs.readdirSync(FEEDS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  let allItems = [];

  for (const pdir of partnerDirs) {
    const fullDir = path.join(FEEDS_DIR, pdir);
    const metaPath = path.join(fullDir, "meta.json");
    const meta = readJsonSafe(metaPath) || {};
    const partnerId = meta.partner || pdir;

    console.log(`→ Partner: ${partnerId} (${pdir})`);

    const files = fs.readdirSync(fullDir)
      .filter((fn) => /^page-\d+\.json$/i.test(fn))
      .sort();

    let count = 0;

    for (const fn of files) {
      const pagePath = path.join(fullDir, fn);
      const page = readJsonSafe(pagePath);
      if (!page || !Array.isArray(page.items)) continue;

      for (const it of page.items) {
        const id = it.id || it.sku || it.url || it.title;
        if (!id) continue;

        // Kép mező – több forrásnév támogatása
        const image =
          it.img ||
          it.image ||
          it.image_url ||
          it.image_link ||
          it.g_image_link ||
          "";

        // Kategória mező – egységesítve algoliához: categoryPath
        const categoryPath =
          it.categoryPath ||
          it.category_path ||
          it.category ||
          "";

        const cat =
          it.cat ||
          it.findora_main ||
          null;

        const obj = {
          objectID: `${partnerId}::${id}`,
          title: it.title || "",
          desc: it.desc || "",
          price: it.price ?? null,
          discount: it.discount ?? null,
          url: it.url || "",
          image,
          partner: partnerId,
          partnerId,
          partnerName: partnerId,
          cat,
          findora_main: it.findora_main || cat || null,
          categoryPath, // ← EZZEL kerül be ALGOLIÁBA egységesen
        };

        allItems.push(obj);
        count++;
      }
    }

    console.log(`   ${count} db termék került be ebből a feedből.`);
    partners.push({ partnerId, dir: pdir, items: count });
  }

  console.log(`Összes Algolia rekord: ${allItems.length}`);
  return allItems;
}

async function main() {
  const records = loadAllItems();
  if (!records.length) {
    console.error("❌ Nincs feltölthető rekord.");
    process.exit(1);
  }

  console.log(`Algolia index (${INDEX_NAME}) törlése és újratöltése…`);

  // Egyszerű megoldás: teljes újraírás
  await index.clearObjects();

  // nagyobb tömeget is bír az index.saveObjects, de chunkoljuk biztonságból
  const chunkSize = 5000;
  for (let i = 0; i < records.length; i += chunkSize) {
    const chunk = records.slice(i, i + chunkSize);
    console.log(`   Mentés chunk ${(i / chunkSize) + 1} (size=${chunk.length})…`);
    await index.saveObjects(chunk, { autoGenerateObjectIDIfNotExist: false });
  }

  console.log("✅ Algolia index frissítés kész.");
}

main().catch((err) => {
  console.error("❌ Algolia frissítés hiba:", err);
  process.exit(1);
});
