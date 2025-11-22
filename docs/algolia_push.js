// docs/algolia_push.js
//
// Findora → Algolia index frissítés (FULL REBUILD)
//
// - Beolvassa az összes partner feedet a docs/feeds/* mappákból
// - Összefűzi az itemeket egységes struktúrába
// - Feltölti az Algolia indexbe (findora_products)
// - Kategória mező mindig: "kat"
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
          kat, // ← EZ KELL AZ ALGOLIÁNAK!
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
