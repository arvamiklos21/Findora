# scripts/meili.py
#
# ÖSSZES PARTNER → MEILISEARCH (products_all)
#
# ÚJ LOGIKA (javított):
#   - Ha vannak kategória mappák → azokat használja.
#   - Ha nincs kategória mappa, de VAN page-0001.json → globál feedként beolvassa
#       → akkor is működik, ha NINCS meta.json!
#   - Csak akkor hagyja ki a partnert, ha még page-0001.json sincs.
#
# Ez biztosítja, hogy:
#   - Alza
#   - OtthonMarket
#   - Onlinemarkabolt
#   - Pepita
#   - Karácsonydekor
#   - KozmetikaOtthon
#   - Ékszereshop
# ne tűnjenek el többé a Meiliből.

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
    except:
        return {}

def load_items_from_page_dir(dir_path: Path, label: str):
    meta = load_meta(dir_path / "meta.json")
    page_count = meta.get("page_count") or meta.get("pages") or 0

    # ha nincs meta.json → számoljuk meg a page-*.json fájlokat
    if not page_count:
        page_count = 0
        while True:
            page_count += 1
            candidate = dir_path / f"page-{page_count:04d}.json"
            if not candidate.exists():
                page_count -= 1
                break

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
        except:
            continue
        items = data.get("items") or []
        all_items.extend([it for it in items if isinstance(it, dict)])

    print(f"[INFO] {label}: összes: {len(all_items)}")
    return all_items

# ===== Partner forrás keresés (KULCS MÓDOSÍTÁS) =====

def iter_partner_sources(base: Path):
    if not base.exists():
        return

    for partner_dir in base.iterdir():
        if not partner_dir.is_dir():
            continue

        partner_id = partner_dir.name

        # 1) kategória mappák (prioritás)
        cat_dirs = []
        for sub in partner_dir.iterdir():
            if sub.is_dir():
                if (sub / "page-0001.json").exists():
                    cat_dirs.append(sub)

        if cat_dirs:
            yield (partner_id, "categories", cat_dirs)
            continue

        # 2) globál feed – meta.json NEM kötelező!
        global_page1 = partner_dir / "page-0001.json"
        if global_page1.exists():
            yield (partner_id, "global", [partner_dir])
            continue

        print(f"[WARN] {partner_id}: nincs page-0001.json → teljesen kihagyva.")


# ===== Ár normalizálás =====

def normalize_price(v):
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
    except:
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
    old_price = normalize_price(raw.get("old_price") or raw.get("price_old"))
    discount = raw.get("discount")
    try:
        if discount is not None:
            discount = int(round(float(discount)))
    except:
        discount = None

    partner_field = raw.get("partner") or partner_id
    partner_name = raw.get("partner_name") or PARTNER_NAME_MAP.get(partner_field, partner_field)

    raw_category = raw.get("findora_main") or raw.get("category") or ""
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
        "raw": raw,
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

def push_docs(index_uid: str, docs):
    if not docs:
        return
    payload = json.dumps(docs, ensure_ascii=False)
    resp = meili_request("POST", f"/indexes/{index_uid}/documents", data=payload.encode("utf-8"))
    try:
        data = resp.json()
        print(f"[INFO] batch → {len(docs)} docs (taskUid={data.get('taskUid')})")
    except:
        print(f"[INFO] batch → {len(docs)} docs")


# ===== MAIN =====

def main():
    print(f"[INFO] MEILI_INDEX_PRODUCTS = {MEILI_INDEX_PRODUCTS}")

    partners = list(iter_partner_sources(BASE_FEEDS_DIR))
    if not partners:
        print("[WARN] nincs partner")
        return

    print("[INFO] betöltendő:")
    for pid, mode, dirs in partners:
        print(f"  - {pid}: {mode} ({len(dirs)} mappa)")

    if MEILI_CLEAR_INDEX_FIRST:
        clear_index(MEILI_INDEX_PRODUCTS)

    total = 0

    for partner_id, mode, dirs in partners:
        print(f"\n===== {partner_id} ({mode}) =====")

        all_items = []
        seen = set()

        if mode == "global":
            all_items.extend(load_items_from_page_dir(dirs[0], partner_id))
        else:
            for cat_dir in dirs:
                for it in load_items_from_page_dir(cat_dir, f"{partner_id}/{cat_dir.name}"):
                    key = (it.get("id"), it.get("url"))
                    if key in seen:
                        continue
                    seen.add(key)
                    all_items.append(it)

        if not all_items:
            print(f"[INFO] {partner_id}: nincs item")
            continue

        docs = [normalize_item(partner_id, it) for it in all_items]

        for chunk in chunks(docs, 1000):
            push_docs(MEILI_INDEX_PRODUCTS, chunk)
            total += len(chunk)

    print(f"\n[OK] Összes dokumentum: {total}")


def chunks(lst, n):
    buf = []
    for x in lst:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf


if __name__ == "__main__":
    main()
