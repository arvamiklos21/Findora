# scripts/meili.py
#
# ÖSSZES PARTNER → MEILISEARCH (products_all)
#
# GLOBAL-ONLY LOGIKA (végleges):
#   - Csak a docs/feeds/<partner>/page-0001.json (+page-0002...) fájlokat olvassa.
#   - NEM használ kategória mappákat, NEM olvas almappákat.
#   - meta.json opcionális (ha nincs, page-*.json fájlokból számol).
#   - Partnert csak akkor hagy ki, ha nincs docs/feeds/<partner>/page-0001.json.
#
# Biztonsági fixek:
#   - akcio/ és bármilyen almappa teljesen ignorálva
#   - Meili HTTP hibákra resp.raise_for_status()
#   - nincs "raw" mező (payload ne szálljon el)

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
    "cj-jatekshop": "Jatekshop.eu",
}

# partner → default Findora kategória
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
}

VALID_CATEGORY_SLUGS = {
    "elektronika","haztartasi_gepek","szamitastechnika","mobil","gaming",
    "smart_home","otthon","lakberendezes","konyha_fozes","kert","jatekok",
    "divat","szepseg","drogeria","baba","sport","egeszseg","latas","allatok",
    "konyv","utazas","iroda_iskola","szerszam_barkacs","auto_motor","multi",
}

# ===== JSON betöltők =====

def load_meta(meta_path: Path):
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def count_pages_by_files(dir_path: Path) -> int:
    # megszámolja a page-0001.json, page-0002.json... sorozatot
    n = 0
    while True:
        n += 1
        fp = dir_path / f"page-{n:04d}.json"
        if not fp.exists():
            return n - 1

def load_items_from_global_partner_dir(dir_path: Path, label: str):
    """
    Csak a partner root mappáját olvassa:
      docs/feeds/<partner>/page-0001.json ... page-XXXX.json
    meta.json opcionális
    """
    meta = load_meta(dir_path / "meta.json")
    page_count = meta.get("page_count") or meta.get("pages") or 0

    if not page_count:
        page_count = count_pages_by_files(dir_path)

    if page_count <= 0:
        print(f"[INFO] {label}: nincs egyetlen oldal sem.")
        return []

    print(f"[INFO] {label}: {page_count} oldal")

    all_items = []
    for page_no in range(1, page_count + 1):
        fp = dir_path / f"page-{page_no:04d}.json"
        if not fp.exists():
            continue
        try:
            with fp.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        items = data.get("items") or []
        if isinstance(items, list):
            all_items.extend([it for it in items if isinstance(it, dict)])

    print(f"[INFO] {label}: összes: {len(all_items)}")
    return all_items

# ===== Partner forrás keresés (GLOBAL-ONLY) =====

def iter_partner_sources_global_only(base: Path):
    if not base.exists():
        return

    for partner_dir in base.iterdir():
        if not partner_dir.is_dir():
            continue

        partner_id = partner_dir.name

        # GLOBAL-ONLY: csak a partner root page-0001.json számít
        global_page1 = partner_dir / "page-0001.json"
        if global_page1.exists():
            yield (partner_id, partner_dir)
        else:
            print(f"[WARN] {partner_id}: nincs page-0001.json → kihagyva.")

# ===== Ár normalizálás =====

def normalize_price(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        try:
            return int(round(float(v)))
        except Exception:
            return None
    s = str(v)
    s_norm = re.sub(r"[^\d.,-]", "", s).replace(" ", "")
    if not s_norm:
        return None
    try:
        return int(round(float(s_norm.replace(",", "."))))
    except Exception:
        digits = re.sub(r"[^\d]", "", s)
        return int(digits) if digits else None

# ===== Item normalizálás =====

def normalize_item(partner_id: str, raw: dict):
    item_id = (
        raw.get("id")
        or raw.get("sku")
        or raw.get("code")
        or raw.get("identifier")
        or raw.get("product_id")
        or raw.get("url")
        or raw.get("link")
        or "noid"
    )
    item_id = str(item_id).strip()
    doc_id = f"{partner_id}-{item_id}"

    title = raw.get("title") or raw.get("name") or ""
    description = raw.get("desc") or raw.get("description") or ""
    img = raw.get("img") or raw.get("image") or raw.get("thumbnail") or ""
    url = raw.get("url") or raw.get("link") or ""

    price = normalize_price(raw.get("price") or raw.get("sale_price"))
    old_price = normalize_price(raw.get("old_price") or raw.get("price_old") or raw.get("was_price"))
    discount = raw.get("discount")
    try:
        if discount is not None:
            discount = int(round(float(discount)))
    except Exception:
        discount = None

    partner_field = raw.get("partner") or partner_id
    partner_name = raw.get("partner_name") or PARTNER_NAME_MAP.get(partner_field, partner_field)

    raw_category = raw.get("findora_main") or raw.get("cat") or raw.get("category") or ""
    category = str(raw_category).strip().lower()
    if category not in VALID_CATEGORY_SLUGS:
        category = PARTNER_DEFAULT_CATEGORY.get(partner_id, "multi")

    brand = raw.get("brand") or raw.get("manufacturer") or ""
    category_path = raw.get("category_path") or raw.get("product_type") or ""

    return {
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
    }

# ===== Meili push =====

def meili_request(method: str, path: str, **kwargs):
    url = f"{MEILI_HOST.rstrip('/')}{path}"
    headers = kwargs.pop("headers", {})
    if MEILI_API_KEY:
        headers["Authorization"] = f"Bearer {MEILI_API_KEY}"
    if method in ("POST", "PUT", "PATCH") and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
    return requests.request(method, url, headers=headers, **kwargs)

def clear_index(index_uid: str):
    resp = meili_request("DELETE", f"/indexes/{index_uid}/documents")
    if resp.status_code >= 300:
        print(f"[ERROR] clear index failed: {resp.status_code} {resp.text[:500]}")
        resp.raise_for_status()

def push_docs(index_uid: str, docs):
    if not docs:
        return

    payload = json.dumps(docs, ensure_ascii=False).encode("utf-8")
    resp = meili_request("POST", f"/indexes/{index_uid}/documents", data=payload)

    if resp.status_code >= 300:
        print(f"[ERROR] Meili push failed: {resp.status_code} {resp.text[:500]}")
        resp.raise_for_status()

    try:
        data = resp.json()
        print(f"[INFO] batch → {len(docs)} docs (taskUid={data.get('taskUid')})")
    except Exception:
        print(f"[INFO] batch → {len(docs)} docs (no json response)")

def chunks(lst, n):
    buf = []
    for x in lst:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf

# ===== MAIN =====

def main():
    print(f"[INFO] MEILI_INDEX_PRODUCTS = {MEILI_INDEX_PRODUCTS}")
    print("[INFO] MODE = GLOBAL-ONLY (no category dirs)")

    partners = list(iter_partner_sources_global_only(BASE_FEEDS_DIR))
    if not partners:
        print("[WARN] nincs partner (nincs page-0001.json egyik mappában sem)")
        return

    print("[INFO] betöltendő partnerek:")
    for pid, pdir in partners:
        print(f"  - {pid}: {pdir}")

    if MEILI_CLEAR_INDEX_FIRST:
        print("[INFO] CLEAR INDEX FIRST = 1 → törlöm az index dokumentumait")
        clear_index(MEILI_INDEX_PRODUCTS)

    total_docs = 0

    for partner_id, partner_dir in partners:
        print(f"\n===== {partner_id} (global) =====")

        items = load_items_from_global_partner_dir(partner_dir, partner_id)
        if not items:
            print(f"[INFO] {partner_id}: nincs item")
            continue

        docs = [normalize_item(partner_id, it) for it in items]

        for chunk in chunks(docs, 1000):
            push_docs(MEILI_INDEX_PRODUCTS, chunk)
            total_docs += len(chunk)

    print(f"\n[OK] Összes dokumentum feltöltve: {total_docs}")

if __name__ == "__main__":
    main()
