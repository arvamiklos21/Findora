# scripts/meili.py
#
# ÖSSZES PARTNER → MEILISEARCH (products_all)
#
# Logika:
#   - Végigmegy a docs/feeds/* mappákon
#   - Minden olyan partner, ahol:
#       docs/feeds/<partner>/meta.json létezik
#       és docs/feeds/<partner>/page-0001.json létezik
#     → GLOBÁLIS feedként kezeljük (page-0001.json, page-0002.json, ...).
#
#   - Beolvassa az összes page-*.json-t
#   - Minden terméket egységes Meili-dokummá alakít:
#       id            = "<partner>-<item_id>"
#       title         = item["title"]
#       description   = item["desc"] vagy "description" vagy ""
#       img           = item["img"] stb.
#       url           = item["url"] stb.
#       price         = item["price"] (szám lesz)
#       old_price     = item["old_price"] ha van
#       discount      = item["discount"] ha van
#       partner       = partner azonosító (pl. "alza")
#       partner_name  = szépen formázott név (Alza, Tchibo.hu, stb.) – minimális map
#       category      = item["findora_main"] / "cat" / "category" / "multi"
#       brand         = item["brand"] ha van
#       category_path = item["category_path"] ha van
#
#   - Meilisearch index:
#       host: MEILI_HOST (default: http://127.0.0.1:7700)
#       api key: MEILI_API_KEY vagy MEILI_MASTER_KEY
#       index: MEILI_INDEX_PRODUCTS (default: products_all)
#
#   - Opcionális:
#       MEILI_CLEAR_INDEX_FIRST = "1"  → futás elején törli az index összes dokumentumát
#
# Futás:
#   python scripts/meili.py
#
# Feltételezi, hogy a JSON oldalak ilyenek:
#   { "items": [ { ...termék... }, ... ] }
#
# Pl. az új Alza builder (build_alza.py) már pont ilyen struktúrát ír.

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

# partner → emberi név (nem kötelező, de szebben néz ki a frontenden)
PARTNER_NAME_MAP = {
    "alza": "Alza",
    "tchibo": "Tchibo.hu",
    "regiojatek": "REGIO Játék",
    "jateksziget": "Játéksziget",
    "pepita": "Pepita.hu",
    "decathlon": "Decathlon",
    "onlinemarkabolt": "Onlinemárkabolt",
    "otthonmarket": "OtthonMarket",
    "kozmetikaotthon": "KozmetikaOtthon",
    "eoptika": "eOptika",
    "cj-eoptika": "eOptika",
    "cj-karcher": "Kärcher",
    "cj-jateknet": "JátékNet",
    "cj-jatekshop": "Játékshop",
    # bővíthető
}


# ===== SEGÉDFÜGGVÉNYEK =====

def iter_global_partner_dirs(base: Path):
    """
    Végigmegy a docs/feeds/* mappákon, és visszaadja azokat,
    amik GLOBÁLIS feedként értelmezhetők:
      - van meta.json
      - van page-0001.json
    """
    if not base.exists():
        print(f"[WARN] Feeds mappa nem létezik: {base}")
        return

    for p in base.iterdir():
        if not p.is_dir():
            continue
        meta = p / "meta.json"
        page1 = p / "page-0001.json"
        if meta.exists() and page1.exists():
            yield p.name, p


def load_meta(meta_path: Path):
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] meta.json beolvasási hiba: {meta_path} – {e}")
        return {}


def load_items_from_partner_dir(partner_id: str, partner_dir: Path):
    """
    docs/feeds/<partner>/meta.json + page-*.json → összes terméklista
    """
    meta = load_meta(partner_dir / "meta.json")
    page_count = meta.get("page_count") or meta.get("pages") or 0
    if not page_count:
        # ha meta nem mondja meg, akkor próbáljuk végig page-0001, page-0002 ... létezésig
        page_count = 0
        while True:
            page_count += 1
            candidate = partner_dir / f"page-{page_count:04d}.json"
            if not candidate.exists():
                page_count -= 1
                break

    if page_count <= 0:
        print(f"[INFO] {partner_id}: meta.json alapján nincs oldal (page_count=0)")
        return []

    print(f"[INFO] {partner_id}: page_count = {page_count}")

    all_items = []
    for page_no in range(1, page_count + 1):
        path = partner_dir / f"page-{page_no:04d}.json"
        if not path.exists():
            print(f"[WARN] {partner_id}: hiányzó oldal: {path}")
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] {partner_id}: page-{page_no:04d}.json parse hiba: {e}")
            continue

        items = data.get("items") or []
        print(f"[INFO] {partner_id}: page-{page_no:04d} → {len(items)} termék")
        for it in items:
            if isinstance(it, dict):
                all_items.append(it)

    print(f"[INFO] {partner_id}: összes termék (JSON-ből): {len(all_items)}")
    return all_items


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
    # kivesszük a nem szám karaktereket, max egy pont / vessző
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
    # az eredeti item azonosítója
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
        or raw.get("list_price")
        or raw.get("regular_price")
    )

    discount = raw.get("discount")
    if discount is not None:
        try:
            discount = int(round(float(discount)))
        except Exception:
            discount = None

    partner_field = raw.get("partner") or partner_id

    partner_name = raw.get("partner_name") or PARTNER_NAME_MAP.get(partner_field, partner_field)

    category = (
        raw.get("findora_main")
        or raw.get("cat")
        or raw.get("category")
        or "multi"
    )

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
        # opcionálisan extra mezők:
        "raw_id": item_id,
        "raw": raw,  # ha túl nagy lenne, később kivehető
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
        print("[WARN] MEILI_API_KEY hiányzik – a Meili hívások valószínűleg el fognak hasalni auth hibával.")

    partners = list(iter_global_partner_dirs(BASE_FEEDS_DIR))
    if not partners:
        print(f"[WARN] Nincs egyetlen globális feed sem a {BASE_FEEDS_DIR} alatt (meta.json + page-0001.json).")
        sys.exit(0)

    print("[INFO] Globális feedet használó partnerek:")
    for pid, pdir in partners:
        print(f"  - {pid}: {pdir}")

    # MEILI index törlése, ha kérted
    if MEILI_CLEAR_INDEX_FIRST:
        clear_index(MEILI_INDEX_PRODUCTS)

    total_docs = 0

    for partner_id, partner_dir in partners:
        print(f"\n===== PARTNER: {partner_id} =====")
        items = load_items_from_partner_dir(partner_id, partner_dir)
        if not items:
            print(f"[INFO] {partner_id}: nincs termék, továbblépünk.")
            continue

        docs = [normalize_item(partner_id, it) for it in items]

        # batch-elve küldjük (1000-es csomagok)
        for batch in chunked(docs, 1000):
            push_docs_to_meili(MEILI_INDEX_PRODUCTS, batch)
            total_docs += len(batch)

    print(f"\n✅ KÉSZ: Összesen {total_docs} dokumentum került a Meilibe (index = {MEILI_INDEX_PRODUCTS}).")


if __name__ == "__main__":
    main()
