// docs/algolia_push.js

// ===== DEPENDENCIÁK =====
const fs = require("fs");
const path = require("path");

// FONTOS: .default kell, különben "algoliasearch is not a function" hibát kapsz
const algoliasearch = require("algoliasearch");

// ===== KÖRNYEZETI VÁLTOZÓK =====
const APP_ID = process.env.ALGOLIA_APP_ID;
const ADMIN_KEY = process.env.ALGOLIA_ADMIN_API_KEY;
const INDEX_NAME = process.env.ALGOLIA_INDEX_NAME || "findora_products";

// Itt jön az, amit kérdeztél: ha hiányzik valamelyik env, azonnal megállunk
if (!APP_ID || !ADMIN_KEY) {
  console.error(
    "[FATAL] Hiányzik ALGOLIA_APP_ID vagy ALGOLIA_ADMIN_API_KEY a környezeti változók közül."
  );
  process.exit(1);
}

// ===== KISEGÍTŐ: alap kategória partner alapján (lazább, mint a frontenden) =====
function baseCategoryForPartner(partnerCfg) {
  const g = (partnerCfg && partnerCfg.group) || "";
  switch (g) {
    case "games":
      return "jatekok";
    case "vision":
      return "latas";
    case "sport":
      return "sport";
    case "tech":
      return "elektronika";
    case "otthon":
      return "otthon";
    case "travel":
      return "utazas";
    default:
      return "multi";
  }
}

// ===== FEED-EK BEOLVASÁSA docs/feeds ALÓL =====
function loadPartnersConfig() {
  const partnersPath = path.join(__dirname, "feeds", "partners.json");
  try {
    const raw = fs.readFileSync(partnersPath, "utf8");
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr;
  } catch (e) {
    console.warn("[WARN] Nem sikerült beolvasni a partners.json-t:", e.message);
    return [];
  }
}

function collectFeedFiles() {
  const feedsRoot = path.join(__dirname, "feeds");
  const result = [];

  if (!fs.existsSync(feedsRoot)) {
    console.warn("[WARN] Nincs feeds mappa:", feedsRoot);
    return result;
  }

  const entries = fs.readdirSync(feedsRoot, { withFileTypes: true });

  for (const ent of entries) {
    if (!ent.isDirectory()) continue;
    const partnerId = ent.name; // pl. tchibo, jateksziget…
    const dir = path.join(feedsRoot, partnerId);

    const files = fs
      .readdirSync(dir)
      .filter((f) => /^page-\d+\.json$/.test(f))
      .sort();

    for (const f of files) {
      result.push({
        partnerId,
        filePath: path.join(dir, f),
        fileName: f,
      });
    }
  }

  return result;
}

function loadItemsFromFile(filePath) {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    const json = JSON.parse(raw);
    const items = Array.isArray(json.items) ? json.items : [];
    return items;
  } catch (e) {
    console.warn("[WARN] Nem sikerült beolvasni a JSON-t:", filePath, e.message);
    return [];
  }
}

// ===== ITEM → ALGOLIA RECORD MAPPELÉS =====
function buildAlgoliaRecords(partnersCfg, feedFiles) {
  const partnerMap = new Map();
  partnersCfg.forEach((p) => partnerMap.set(p.id, p));

  const records = [];
  let globalCounter = 0;

  for (const { partnerId, filePath, fileName } of feedFiles) {
    const partnerCfg = partnerMap.get(partnerId) || { id: partnerId };
    const partnerName = partnerCfg.name || partnerId;
    const baseCat = baseCategoryForPartner(partnerCfg);

    const items = loadItemsFromFile(filePath);

    items.forEach((it, idx) => {
      globalCounter++;

      const title =
        (it && (it.title || it.name || it.product_title)) || "";
      const desc =
        (it && (it.desc || it.description || it.short_description)) || "";
      const url =
        (it && (it.url || it.link || it.deeplink)) || "";
      const image =
        (it &&
          (it.image ||
            it.img ||
            it.image_link ||
            it.thumbnail)) ||
        "";
      const price =
        it && typeof it.price === "number" && isFinite(it.price)
          ? it.price
          : null;

      // objectID – Algolia-nak kötelező, legyen stabil:
      // partnerId + esetleges feed-id + file név + lokális index
      const objectID =
        (it && it.objectID) ||
        (it && it.id && `${partnerId}_${String(it.id)}`) ||
        `${partnerId}_${fileName}_${idx}`;

      const record = {
        objectID,
        title,
        desc,
        url,
        image,
        price,
        partnerId,
        partnerName,
        category: baseCat,
        // egy kis meta debughoz
        _meta: {
          file: fileName,
        },
      };

      records.push(record);
    });
  }

  return records;
}

// ===== FŐ FUTTATÁS =====
async function main() {
  console.log("[INFO] Algolia kliens inicializálása…");
  console.log("[DEBUG] APP_ID:", APP_ID);
  console.log("[DEBUG] INDEX_NAME:", INDEX_NAME);

  const client = algoliasearch(APP_ID, ADMIN_KEY);
  const index = client.initIndex(INDEX_NAME);

  console.log("[INFO] partners.json betöltése…");
  const partnersCfg = loadPartnersConfig();

  console.log("[INFO] feed fájlok összegyűjtése…");
  const feedFiles = collectFeedFiles();
  console.log("[INFO] Talált feed fájlok száma:", feedFiles.length);

  console.log("[INFO] Rekordok összeállítása Algoliához…");
  const records = buildAlgoliaRecords(partnersCfg, feedFiles);
  console.log("[INFO] Összes termék Algoliához:", records.length);

  if (!records.length) {
    console.warn("[WARN] Nincs egyetlen rekord sem, nincs mit feltölteni Algoliára.");
    return;
  }

  // Feltöltés chunkokban (1000-esével)
  const CHUNK_SIZE = 1000;
  for (let i = 0; i < records.length; i += CHUNK_SIZE) {
    const chunk = records.slice(i, i + CHUNK_SIZE);
    console.log(
      `[INFO] Chunk feltöltése: ${i}–${i + chunk.length - 1} / ${records.length - 1}`
    );
    await index.saveObjects(chunk, {
      autoGenerateObjectIDIfNotExist: true,
    });
  }

  console.log("[INFO] Algolia index frissítés kész. ✅");
}

main().catch((err) => {
  console.error("[FATAL] Algolia push hiba:", err);
  process.exit(1);
});

