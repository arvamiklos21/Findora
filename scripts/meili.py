# scripts/meili.py
#
# ÖSSZES PARTNER → MEILISEARCH (products_all)
#
# Logika:
#   - Végigmegy a docs/feeds/* mappákon
#   - Partnerenként kétféle layoutot kezel:
#       (A) GLOBÁL:
#           docs/feeds/<partner>/meta.json
#           docs/feeds/<partner>/page-0001.json, page-0002.json, ...
#
#       (B) KATEGÓRIA-ALAPÚ:
#           docs/feeds/<partner>/<cat>/meta.json
#           docs/feeds/<partner>/<cat>/page-0001.json, ...
#         (pl. onlinemarkabolt, ahol a gyökérben NINCS page-0001.json)
#
#   - Csak EGYFORRÁSBÓL tölt (vagy (A) vagy (B)), hogy ne duplázzon:
#       - Ha van globál page-0001.json a gyökérben → (A)
#       - Különben, ha vannak kategória mappák page-0001.json-nel → (B)
#
#   - Beolvasott item → Meili dokumentum:
#       id            = "<partner>-<item_id>"
#       title         = item["title"] / ["name"] / ...
#       description   = item["desc"] / ["description"] / ...
#       img           = item["img"] / ["image"] / ...
#       url           = item["url"] / ["link"] / ...
#       price         = normalizált integer (Ft)
#       old_price     = különböző mezőkből (old_price, price_old, ...)
#       discount      = int (%) ha értelmezhető
#       partner       = item["partner"] vagy partner azonosító
#       partner_name  = emberi név (térkép alapján)
#       category      = item["findora_main"] / ["cat"] / ["category"] / partner-default / "multi"
#       brand         = item["brand"] / ["manufacturer"]
#       category_path = item["category_path"] / ["product_type"]
#
#   - Meili:
#       MEILI_HOST, MEILI_API_KEY, MEILI_INDEX_PRODUCTS
#       MEILI_CLEAR_INDEX_FIRST="1" esetén elején törli az indexet.
#
# Futás:
#   - GitHub Actions-ből:
#       env:
#         MEILI_HOST: https://meili.findora.hu
#         MEILI_API_KEY: ${{ secrets.MEILI_MASTER_KEY }}
#         MEILI_INDEX_PRODUCTS: products_all
#         MEILI_CLEAR_INDEX_FIRST: 1
#
#   - Vagy helyben:
#       MEILI_HOST=http://127.0.0.1:7700 \
#       MEILI_API_KEY=xxxxx \
#       python scripts/meili.py

import os
import sys
import json
import re
from pathlib import Path

import requests

# ===== KONFIG =====

BASE_FEEDS_DIR = Path("docs/feeds")

MEILI_HOST = os.environ.get("MEILI_HOST", "http://127.0.0.1:7700")
MEILI_API_KEY = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY")
MEILI_INDEX_PRODUCTS = os.environ.get("MEILI_INDEX_PRODUCTS", "products_all")
MEILI_CLEAR_INDEX_FIRST = os.environ.get("MEILI_CLEAR_INDEX_FIRST", "0") == "1"

# partner → emberi név
PARTNER_NAME_MAP = {
    "alza": "Alza",
    "tchibo": "Tchibo.hu",
    "regiojatek": "REGIO Játék",
    "jateksziget": "Játéksziget",
    "pepita": "Pepita.hu",
    "decathlon": "Decathlon",
    "onlinemarkabolt": "Onlinemárkaboltok",
    "otthonmarket": "OtthonMarket",
    "kozmetikaotthon": "KozmetikaOtthon",
    "ekszereshop": "Ékszer-Eshop.hu",
    "karacsonydekor": "Karácsonyi Dekor",
    "eoptika": "eOptika",
    "cj-eoptika": "eOptika",
    "cj-karcher": "Kärcher",
    "cj-jateknet": "JátékNet",
    "cj-jatekshop": "Játékshop",
    # bővíthető
}

# partner → default Findora fő kategória slug (amit a frontend a "category" mezőben vár)
# (ez pont ugyanaz a név, amit az app.js BACKEND_SYNONYM_TO_CATID kulcsként használ)
PARTNER_DEFAULT_CATEGORY = {
    "tchibo": "otthon",
    "karacsonydekor": "otthon",
    "otthonmarket": "otthon",
    "onlinemarkabolt": "otthon",

    "alza": "elektronika",

    "decathlon": "sport",

    "regiojatek": "jatekok",
    "jateksziget": "jatekok",
    "cj-jatekshop": "jatekok",
    "cj-jateknet": "jatekok",

    "cj-eoptika": "latas",
    "eoptika": "latas",

    "ekszereshop": "divat",
    "kozmetikaotthon": "szepseg",

    "pepita": "multi",
    "cj-karcher": "kert",
    # ide nyugodtan vehetsz fel újakat, ha kell
}


# ===== SEGÉDFÜGGVÉNYEK A JSON OLDALAKHOZ =====

def load_meta(meta_path: Path):
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] meta.json beolvasási hiba: {meta_path} – {e}")
        return {}


def load_items_from_page_dir(dir_path: Path, label: str):
    """
    Egy KONKRÉT mappa (pl. docs/feeds/alza vagy docs/feeds/onlinemarkabolt/haztartasi_gepek)
    meta.json + page-*.json → itemek listája.
    """
    meta = load_meta(dir_path / "meta.json")
    page_count = meta.get("page_count") or meta.get("pages") or 0

    if not page_count:
        # ha meta nem mondja meg, akkor próbáljuk végig page-0001, page-0002 ... létezésig
        page_count = 0
        while True:
            page_count += 1
            candidate = dir_path / f"page-{page_count:04d}.json"
            if not candidate.exists():
                page_count -= 1
                break

    if page_count <= 0:
        print(f"[INFO] {label}: meta.json alapján nincs oldal (page_count=0)")
        return []

    print(f"[INFO] {label}: page_count = {page_count}")

    all_items = []
    for page_no in range(1, page_count + 1):
        path = dir_path / f"page-{page_no:04d}.json"
        if not path.exists():
            print(f"[WARN] {label}: hiányzó oldal: {path}")
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] {label}: page-{page_no:04d}.json parse hiba: {e}")
            continue

        items = data.get("items") or []
        print(f"[INFO] {label}: page-{page_no:04d} → {len(items)} termék")
        for it in items:
            if isinstance(it, dict):
                all_items.append(it)

    print(f"[INFO] {label}: összes termék (JSON-ből): {len(all_items)}")
    return all_items


def iter_partner_sources(base: Path):
    """
    Végigmegy a docs/feeds/* mappákon, és partnerenként eldönti:
      - van-e GLOBÁL feed (base/page-0001.json),
      - ha nincs, vannak-e KATEGÓRIA mappák (base/<cat>/page-0001.json).

    Yield:
      (partner_id, mode, source_dirs)

      mode:
        "global"     → source_dirs: [ partner_dir ]
        "categories" → source_dirs: [ cat_dir1, cat_dir2, ... ]
    """
    if not base.exists():
        print(f"[WARN] Feeds mappa nem létezik: {base}")
        return

    for partner_dir in base.iterdir():
        if not partner_dir.is_dir():
            continue

        partner_id = partner_dir.name

        root_meta = partner_dir / "meta.json"
        root_page1 = partner_dir / "page-0001.json"

        if root_meta.exists() and root_page1.exists():
            # GLOBÁL feed van, ez az elsődleges
            yield (partner_id, "global", [partner_dir])
            continue

        # különben keresünk kategória mappákat
        cat_dirs = []
        for sub in partner_dir.iterdir():
            if not sub.is_dir():
                continue
            meta = sub / "meta.json"
            page1 = sub / "page-0001.json"
            if meta.exists() and page1.exists():
                cat_dirs.append(sub)

        if cat_dirs:
            yield (partner_id, "categories", cat_dirs)
        else:
            # se globál, se kategória – logoljuk, de nem fatal
            print(
                f"[WARN] {partner_id}: sem globál page-0001.json, sem kategória mappák page-0001.json-nel – kihagyom."
            )


def normalize_price(v):
    """
    Ha szám, visszaadja.
    Ha string, megpróbál belőle számot csinálni (pl. "12 990 Ft").
    Ha semmi értelme, None.
    """
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v)
    s_norm = re.sub(r"[^\d.,-]", "", s).replace(" ", "")
    if not s_norm:
        return None
    try:
        return int(round(float(s_norm.replace(",", "."))))
    except Exception:
        digits = re.sub(r"[^\d]", "", s)
        return int(digits) if digits else None


def normalize_item(partner_id: str, raw: dict):
    """
    Egy nyers JSON item → egységes Meili dokumentum (Python dict).
    """
    item_id = (
        raw.get("id")
        or raw.get("sku")
        or raw.get("code")
        or raw.get("item_id")
        or raw.get("product_id")
        or raw.get("identifier")
        or raw.get("url")
        or raw.get("link")
        or raw.get("deeplink")
        or ""
    )
    item_id = str(item_id).strip() or "noid"

    doc_id = f"{partner_id}-{item_id}"

    title = (
        raw.get("title")
        or raw.get("name")
        or raw.get("product_name")
        or raw.get("g:title")
        or ""
    )

    description = (
        raw.get("desc")
        or raw.get("description")
        or raw.get("long_description")
        or raw.get("short_description")
        or ""
    )

    img = (
        raw.get("img")
        or raw.get("image")
        or raw.get("image_link")
        or raw.get("image_url")
        or raw.get("thumbnail")
        or ""
    )

    url = (
        raw.get("url")
        or raw.get("link")
        or raw.get("deeplink")
        or raw.get("product_url")
        or ""
    )

    price = normalize_price(
        raw.get("price")
        or raw.get("sale_price")
        or raw.get("price_vat")
        or raw.get("price_with_vat")
        or raw.get("price_final")
        or raw.get("price_huf")
    )

    old_price = normalize_price(
        raw.get("old_price")
        or raw.get("price_old")
        or raw.get("was_price")
        or raw.get("regular_price")
        or raw.get("list_price")
        or raw.get("original_price")
    )

    discount = raw.get("discount")
    if discount is not None:
        try:
            discount = int(round(float(discount)))
        except Exception:
            discount = None

    # --- partner mező: biztosan string legyen ---
    partner_field_raw = raw.get("partner") or partner_id
    partner_field = str(partner_field_raw).strip() or partner_id

    partner_name = (
        raw.get("partner_name")
        or PARTNER_NAME_MAP.get(
            partner_field,
            PARTNER_NAME_MAP.get(partner_id, partner_field),
        )
    )

    # --- KATEGÓRIA BLOKK ---
    # 1) próbáljuk kivenni a feedből (findora_main / cat / category)
    raw_category = (
        raw.get("findora_main")
        or raw.get("cat")
        or raw.get("category")
        or ""
    )
    category = str(raw_category).strip().lower()

    # 2) ha nincs értelmes, vagy "multi", próbáljuk partner-defaultból
    if not category or category == "multi":
        default_cat = PARTNER_DEFAULT_CATEGORY.get(partner_id)
        if default_cat:
            category = default_cat

    # 3) ha még mindig üres, legyen "multi"
    if not category:
        category = "multi"

    brand = raw.get("brand") or raw.get("manufacturer") or ""

    category_path = raw.get("category_path") or raw.get("product_type") or ""

    doc = {
        "id": doc_id,
        "title": title,
        "description": description,
        "img": img,
        "url": url,
        "price": price,
        "old_price": old_price,
        "discount": discount,
        "partner": partner_field,
        "partner_name": partner_name,
        "category": category,
        "brand": brand,
        "category_path": category_path,
        "raw_id": item_id,
        "raw": raw,
    }
    return doc


def chunked(iterable, size):
    buf = []
    for it in iterable:
        buf.append(it)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


# ===== MEILISEARCH =====

def meili_request(method: str, path: str, **kwargs):
    url = f"{MEILI_HOST.rstrip('/')}{path}"
    headers = kwargs.pop("headers", {})
    if MEILI_API_KEY:
        headers["Authorization"] = f"Bearer {MEILI_API_KEY}"
    if "Content-Type" not in headers and method in ("POST", "PUT", "PATCH"):
        headers["Content-Type"] = "application/json"

    resp = requests.request(method, url, headers=headers, **kwargs)
    return resp


def clear_index(index_uid: str):
    print(f"[INFO] Meili: index törlése: {index_uid}")
    resp = meili_request("DELETE", f"/indexes/{index_uid}/documents")
    if resp.status_code >= 400:
        print(f"[WARN] Meili index törlés hiba ({resp.status_code}): {resp.text[:500]}")
    else:
        print(f"[INFO] Meili index dokumentumok törölve: {index_uid}")


def push_docs_to_meili(index_uid: str, docs):
    if not docs:
        return
    path = f"/indexes/{index_uid}/documents"
    payload = json.dumps(docs, ensure_ascii=False)
    resp = meili_request("POST", path, data=payload.encode("utf-8"))
    if resp.status_code >= 400:
        print(
            f"[WARN] Meili batch hiba index={index_uid}, status={resp.status_code}: {resp.text[:500]}"
        )
    else:
        try:
            data = resp.json()
            task_uid = data.get("taskUid")
            print(f"[INFO] Meili batch OK index={index_uid}, taskUid={task_uid}, docs={len(docs)}")
        except Exception:
            print(f"[INFO] Meili batch OK index={index_uid}, docs={len(docs)}")


# ===== MAIN =====

def main():
    print(f"[INFO] MEILI_HOST = {MEILI_HOST}")
    print(f"[INFO] MEILI_INDEX_PRODUCTS = {MEILI_INDEX_PRODUCTS}")
    if not MEILI_API_KEY:
        print("[WARN] MEILI_API_KEY hiányzik – a Meili hívások auth hibával fognak elhasalni.")

    partners = list(iter_partner_sources(BASE_FEEDS_DIR))
    if not partners:
        print(f"[WARN] Nincs egyetlen felvehető feed sem a {BASE_FEEDS_DIR} alatt.")
        sys.exit(0)

    print("[INFO] Partnerek és forrás módok:")
    for pid, mode, dirs in partners:
        if mode == "global":
            print(f"  - {pid}: GLOBAL ({dirs[0]})")
        else:
            print(f"  - {pid}: CATEGORIES ({len(dirs)} mappa)")

    # index törlés, ha kérted
    if MEILI_CLEAR_INDEX_FIRST:
        clear_index(MEILI_INDEX_PRODUCTS)

    total_docs = 0

    for partner_id, mode, dirs in partners:
        print(f"\n===== PARTNER: {partner_id} – mód: {mode} =====")

        all_items = []
        seen_keys = set()

        if mode == "global":
            # csak a gyökér mappát vesszük
            items = load_items_from_page_dir(dirs[0], f"{partner_id} (global)")
            all_items.extend(items)
        else:
            # kategória mappák – dedup ugyanarra az ID-re / URL-re
            for cat_dir in dirs:
                cat_label = f"{partner_id}/{cat_dir.name}"
                items = load_items_from_page_dir(cat_dir, cat_label)
                for it in items:
                    key = (
                        str(it.get("id") or it.get("identifier") or it.get("code") or "").strip(),
                        str(it.get("url") or it.get("link") or it.get("deeplink") or "").strip(),
                    )
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    all_items.append(it)

        if not all_items:
            print(f"[INFO] {partner_id}: nincs termék, továbblépünk.")
            continue

        docs = [normalize_item(partner_id, it) for it in all_items]

        for batch in chunked(docs, 1000):
            push_docs_to_meili(MEILI_INDEX_PRODUCTS, batch)
            total_docs += len(batch)

    print(f"\n✅ KÉSZ: Összesen {total_docs} dokumentum került a Meilibe (index = {MEILI_INDEX_PRODUCTS}).")


if __name__ == "__main__":
    main()
