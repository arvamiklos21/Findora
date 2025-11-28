# scripts/build-onlinemarkabolt.py
#
# OnlineMárkaboltok → Findora paginált JSON feed, kategóriákra bontva
#
# Bemenet:
#   - XML feed (FEED_ONLINEMARKABOLT_URL környezeti változó)
#
# Kimenet:
#   - docs/feeds/onlinemarkabolt/haztartasi_gepek/meta.json
#   - docs/feeds/onlinemarkabolt/haztartasi_gepek/page-0001.json, ...
#   - docs/feeds/onlinemarkabolt/otthon/meta.json
#   - docs/feeds/onlinemarkabolt/otthon/page-0001.json, ...
#   - docs/feeds/onlinemarkabolt/akciok/meta.json
#   - docs/feeds/onlinemarkabolt/akciok/page-0001.json, ...
#
# Struktúra (page-*.json):
#   {
#     "items": [
#       {
#         "id": "553",
#         "title": "...",
#         "img": "https://...",
#         "desc": "rövid leírás",
#         "price": 151840,
#         "discount": 23,              # kedvezmény % (ha van, különben null)
#         "url": "https://www.onlinemarkaboltok.hu/...",
#         "partner": "onlinemarkabolt",
#         "category_path": "BLANCO > ...",
#         "category_root": "BLANCO",
#         "findora_main": "haztartasi_gepek" | "otthon",
#         "cat": "haztartasi_gepek" | "otthon"
#       },
#       ...
#     ]
#   }

import os
import sys
import re
import json
import math
import xml.etree.ElementTree as ET
import requests

from datetime import datetime, timezone

# --- hogy a scripts/ alatti assign modul is látszódjon ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from category_onlinemarkabolt_assign import assign_category  # saját kategória-assigner


# ====== KONFIG ======
FEED_URL = os.environ.get("FEED_ONLINEMARKABOLT_URL")
OUT_BASE = "docs/feeds/onlinemarkabolt"

# JSON oldal méret
PAGE_SIZE = 300

# Ennél a partnernél jelenleg csak ez a két Findora fő kategória játszik:
ONLINEMARKABOLT_CATS = [
    "haztartasi_gepek",
    "otthon",
]

# Akciós bucket slug
AKCIO_SLUG = "akciok"

# Akciós szabály: csak azok menjenek az akciós bucketbe,
# ahol a discount (százalék) legalább 10%
AKCIO_MIN_DISCOUNT = 10


# ====== SEGÉDFÜGGVÉNYEK ======
def norm_price(v):
    """Árat egész forintra normalizál (int vagy None)."""
    if v is None:
        return None
    s = re.sub(r"[^\d.,-]", "", str(v)).replace(" ", "")
    if not s or s in ("-", ""):
        return None
    try:
        return int(round(float(s.replace(",", "."))))
    except Exception:
        digits = re.sub(r"[^\d]", "", str(v))
        return int(digits) if digits else None


def short_desc(t, maxlen=280):
    """HTML-ből rövidített, plain-text leírás."""
    if not t:
        return None
    # HTML tagek lecsupaszítása
    t = re.sub(r"<[^>]+>", " ", str(t))
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= maxlen:
        return t
    # vágjuk szóhatáron
    cut = t[: maxlen + 10]
    m = re.search(r"\s+\S*$", cut)
    if m:
        cut = cut[: m.start()].rstrip()
    return cut + "…"


def ensure_clean_category_dir(path: str):
    """
    Létrehozza a mappát (ha nem létezik),
    és kitörli az esetleges régi page-*.json fájlokat.
    """
    os.makedirs(path, exist_ok=True)
    for fn in os.listdir(path):
        if fn.startswith("page-") and fn.endswith(".json"):
            os.remove(os.path.join(path, fn))


def parse_xml_products(xml_bytes):
    """Visszaadja a <product> elemek listáját (Element)."""
    root = ET.fromstring(xml_bytes)
    # tipikus struktúra: <products><product>...</product>...</products>
    return list(root.findall(".//product"))


def get_text(elem, tag):
    child = elem.find(tag)
    if child is None or child.text is None:
        return None
    return str(child.text).strip()


def extract_category_root(category: str, manufacturer: str | None) -> str:
    """
    A category_path első szintjét adja vissza (pl. BLANCO),
    ha nincs '>' benne, akkor fallback a manufacturer-re.
    """
    cat = (category or "").strip()
    if ">" in cat:
        return cat.split(">")[0].strip()
    if manufacturer:
        return str(manufacturer).strip()
    return cat


def compute_discount(price, old_price):
    """
    Kedvezmény százalék számítás (ha van értelme).
    Visszatér: int (%) vagy None.
    """
    if old_price and price and old_price > price:
        try:
            return round((1 - price / float(old_price)) * 100)
        except Exception:
            return None
    return None


def normalize_item(prod):
    """
    Egy <product> → Findora item + kat (Findora fő kategória).
    prod: xml.etree.ElementTree.Element
    """
    identifier = get_text(prod, "identifier") or get_text(prod, "code")
    name = get_text(prod, "name")
    desc_html = get_text(prod, "description")
    price_raw = get_text(prod, "price")
    category = get_text(prod, "category")
    img = get_text(prod, "image_url")
    url = get_text(prod, "product_url")
    manufacturer = get_text(prod, "manufacturer")

    # lehetséges régi ár mezők (ha a feed tartalmaz ilyet)
    old_price_raw = (
        get_text(prod, "old_price")
        or get_text(prod, "oldprice")
        or get_text(prod, "price_old")
        or get_text(prod, "original_price")
        or get_text(prod, "price_without_discount")
    )

    # kötelező mezők hiánya esetén dobjuk
    if not identifier or not name or not url:
        return None

    price = norm_price(price_raw)
    old_price = norm_price(old_price_raw)
    discount = compute_discount(price, old_price)

    # --- assign_category-hez mezők előkészítése ---
    fields_raw = {
        "id": identifier,
        "code": get_text(prod, "code"),
        "identifier": identifier,
        "name": name,
        "title": name,
        "description": desc_html,
        "category": category,
        "category_text": category,
        "manufacturer": manufacturer,
        # extra aliasok, ha az assigner ilyet keresne
        "productname": name,
        "categorytext": category,
    }

    # kulcsok kisbetűsítve, None → ""
    fields = {str(k).lower(): (v if v is not None else "") for k, v in fields_raw.items()}

    kat = assign_category(fields) or "multi"
    if kat not in ONLINEMARKABOLT_CATS:
        # fallback: ami ismeretlen, menjen "otthon"-ba
        kat = "otthon"

    category_root = extract_category_root(category, manufacturer)

    item = {
        "id": identifier,
        "title": name,
        "img": img,
        "desc": short_desc(desc_html),
        "price": price,
        "discount": discount,  # itt már számolt kedvezmény %
        "url": url,
        "partner": "onlinemarkabolt",
        "category_path": category or "",
        "category_root": category_root or "",
        "findora_main": kat,
        "cat": kat,
    }
    return item, kat


def write_category_pages(cat_slug: str, items_for_cat, page_size: int):
    """
    Egy konkrét Findora kategóriához (pl. 'haztartasi_gepek') kiírja
    a page-*.json oldalakat és a meta.json-t.
    """
    cat_dir = os.path.join(OUT_BASE, cat_slug)
    ensure_clean_category_dir(cat_dir)

    total = len(items_for_cat)
    if total == 0:
        pages = 0
    else:
        pages = int(math.ceil(total / float(page_size)))

    # stabil sorrend azonosító szerint
    items_for_cat.sort(key=lambda x: str(x["id"]))

    for i in range(pages):
        start = i * page_size
        end = start + page_size
        page_items = items_for_cat[start:end]

        page_obj = {"items": page_items}
        page_no = i + 1
        fn = os.path.join(cat_dir, f"page-{page_no:04d}.json")
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(page_obj, f, ensure_ascii=False, separators=(",", ":"))
        print(
            f"[INFO] OnlineMárkaboltok – kat='{cat_slug}' page-{page_no:04d}.json "
            f"({len(page_items)} db)"
        )

    meta = {
        "partner": "onlinemarkabolt",
        "category": cat_slug,
        "pageSize": page_size,
        "total": total,
        "pages": pages,
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
    }
    meta_fn = os.path.join(cat_dir, "meta.json")
    with open(meta_fn, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[INFO] OnlineMárkaboltok – kat='{cat_slug}' meta.json kész: {meta_fn}")


def main():
    if not FEED_URL:
        raise RuntimeError("Hiányzik a FEED_ONLINEMARKABOLT_URL környezeti változó!")

    print(f"[INFO] OnlineMárkaboltok feed letöltése: {FEED_URL}")
    resp = requests.get(FEED_URL, timeout=90)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Nem sikerült letölteni az OnlineMárkaboltok feedet "
            f"(HTTP {resp.status_code})"
        )

    products = parse_xml_products(resp.content)
    print(f"[INFO] OnlineMárkaboltok – XML termékek száma: {len(products)}")

    os.makedirs(OUT_BASE, exist_ok=True)

    # kat → item lista
    items_by_cat = {slug: [] for slug in ONLINEMARKABOLT_CATS}
    seen_ids = set()
    cat_counts = {slug: 0 for slug in ONLINEMARKABOLT_CATS}

    all_items = []  # akciós buckethez is jól jön

    for prod in products:
        try:
            norm = normalize_item(prod)
        except Exception as e:
            # egy termék se törje el az egész futást
            print(f"[WARN] Hibás termék, kihagyva: {e!r}")
            continue

        if not norm:
            continue

        item, kat = norm

        if item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])

        if kat not in items_by_cat:
            # ha valami fura slug jön, dobjuk "otthon"-ba
            kat = "otthon"
            item["findora_main"] = "otthon"
            item["cat"] = "otthon"

        items_by_cat[kat].append(item)
        cat_counts[kat] = cat_counts.get(kat, 0) + 1
        all_items.append(item)

    total_items = sum(cat_counts.values())
    print(f"[INFO] OnlineMárkaboltok – normalizált sorok összesen: {total_items}")
    print("[INFO] OnlineMárkaboltok – kategória statisztika:")
    for k in sorted(cat_counts.keys()):
        print(f"  - {k}: {cat_counts[k]} db")

    # ===== Kategória-specifikus page-*.json + meta.json =====
    for cat_slug in ONLINEMARKABOLT_CATS:
        cat_items = items_by_cat.get(cat_slug, [])
        write_category_pages(cat_slug, cat_items, PAGE_SIZE)

    # ===== Akciós bucket: minden, ahol discount >= 10% =====
    akcio_items = [
        it for it in all_items
        if (it.get("discount") is not None and it.get("discount") >= AKCIO_MIN_DISCOUNT)
    ]
    print(
        f"[INFO] OnlineMárkaboltok – akciós termékek (discount>={AKCIO_MIN_DISCOUNT}%): "
        f"{len(akcio_items)} db"
    )
    write_category_pages(AKCIO_SLUG, akcio_items, PAGE_SIZE)

    # opcionális globális meta (nem tartalmaz page-*.json-t)
    global_meta = {
        "partner": "onlinemarkabolt",
        "sourceUrl": FEED_URL,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totalItems": total_items,
        "pageSize": PAGE_SIZE,
        "categories": cat_counts,
        "categoriesList": ONLINEMARKABOLT_CATS,
        "akcioItems": len(akcio_items),
        "akcioMinDiscount": AKCIO_MIN_DISCOUNT,
    }
    meta_fn = os.path.join(OUT_BASE, "meta.json")
    with open(meta_fn, "w", encoding="utf-8") as f:
        json.dump(global_meta, f, ensure_ascii=False, indent=2)
    print(f"[INFO] OnlineMárkaboltok – globális meta.json kész: {meta_fn}")


if __name__ == "__main__":
    main()
