# scripts/build-onlinemarkabolt.py
#
# OnlineMárkaboltok → Findora globál paginált JSON feed (NINCS kategória mappa, NINCS akció bucket)
#
# Bemenet:
#   - XML feed (FEED_ONLINEMARKABOLT_URL környezeti változó)
#
# Kimenet:
#   - docs/feeds/onlinemarkabolt/meta.json
#   - docs/feeds/onlinemarkabolt/page-0001.json, page-0002.json, ...
#
# Struktúra (page-*.json):
#   {
#     "items": [ { ... } ],
#     "page": 1,
#     "page_size": 1000,
#     "item_count": 1000
#   }
#
# META:
#   {
#     "partner": "onlinemarkabolt",
#     "source_url": "...",
#     "generated_at": "...",
#     "item_count": 12345,
#     "page_size": 1000,
#     "page_count": 13
#   }

import os
import sys
import re
import json
import math
import shutil
import xml.etree.ElementTree as ET
import requests

from datetime import datetime, timezone
from pathlib import Path

# --- hogy a scripts/ alatti modulok is látszódjanak ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from category_onlinemarkabolt_assign import assign_category  # partner-specifikus assigner
from category_assignbase import FINDORA_CATS  # közös 25 Findora fő kategória


# ====== KONFIG ======
PARTNER_ID = "onlinemarkabolt"
FEED_URL = os.environ.get("FEED_ONLINEMARKABOLT_URL")

OUT_DIR = Path("docs/feeds") / PARTNER_ID

PAGE_SIZE = 1000

ALL_FINDORA_CATS = list(FINDORA_CATS)  # valid slugok listája (biztonsági ellenőrzéshez)


# ====== SEGÉDFÜGGVÉNYEK ======
def ensure_clean_out_dir(out_dir: Path):
    """
    Teljes takarítás: mindent töröl a partner mappájában (régi kategória almappák is),
    majd újra létrehozza a kimeneti mappát.
    """
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)


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
    t = re.sub(r"<[^>]+>", " ", str(t))  # HTML tagek
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= maxlen:
        return t
    cut = t[: maxlen + 10]
    m = re.search(r"\s+\S*$", cut)
    if m:
        cut = cut[: m.start()].rstrip()
    return cut + "…"


def parse_xml_products(xml_bytes):
    """Visszaadja a <product> elemek listáját (Element)."""
    root = ET.fromstring(xml_bytes)
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
    Egy <product> → Findora item (globál listába).
    """
    identifier = get_text(prod, "identifier") or get_text(prod, "code")
    name = get_text(prod, "name")
    desc_html = get_text(prod, "description")
    price_raw = get_text(prod, "price")
    category = get_text(prod, "category")
    img = get_text(prod, "image_url")
    url = get_text(prod, "product_url")
    manufacturer = get_text(prod, "manufacturer")

    old_price_raw = (
        get_text(prod, "old_price")
        or get_text(prod, "oldprice")
        or get_text(prod, "price_old")
        or get_text(prod, "original_price")
        or get_text(prod, "price_without_discount")
    )

    # Kötelező mezők – ha ezek hiányoznak, a terméket eldobjuk
    if not identifier or not name or not url:
        return None

    price = norm_price(price_raw)
    old_price = norm_price(old_price_raw)
    discount = compute_discount(price, old_price)

    # assign_category input
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
        "productname": name,
        "categorytext": category,
    }
    fields = {str(k).lower(): (v if v is not None else "") for k, v in fields_raw.items()}

    kat = assign_category(fields) or "multi"
    if kat not in ALL_FINDORA_CATS:
        # ha az assigner valami ismeretlen slugot dob, multi-ba tereljük
        kat = "multi"

    category_root = extract_category_root(category, manufacturer)

    item = {
        "id": identifier,
        "title": name,
        "img": img,
        "desc": short_desc(desc_html),
        "price": price,
        "old_price": old_price,
        "discount": discount,
        "url": url,
        "partner": PARTNER_ID,
        "partner_name": "Onlinemárkaboltok",
        "category_path": category or "",
        "category_root": category_root or "",
        "findora_main": kat,
        "cat": kat,
    }
    return item


def write_pages(out_dir: Path, items: list[dict], page_size: int):
    """
    out_dir/meta.json
    out_dir/page-0001.json, page-0002.json, ...

    Üres lista esetén is létrejön meta.json + page-0001.json (items: []).
    """
    total = len(items)
    page_count = 1 if total == 0 else int(math.ceil(total / float(page_size)))

    # Stabil sorrend (id alapján)
    items_sorted = sorted(items, key=lambda x: str(x.get("id", "")))

    # pages
    for i in range(page_count):
        start = i * page_size
        end = start + page_size
        chunk = items_sorted[start:end] if total else []

        page_no = i + 1
        page_obj = {
            "items": chunk,
            "page": page_no,
            "page_size": page_size,
            "item_count": len(chunk),
        }

        fn = out_dir / f"page-{page_no:04d}.json"
        with fn.open("w", encoding="utf-8") as f:
            json.dump(page_obj, f, ensure_ascii=False)

        print(f"[INFO] {PARTNER_ID} page-{page_no:04d}.json → {len(chunk)} db")

    # meta
    meta = {
        "partner": PARTNER_ID,
        "source_url": FEED_URL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "item_count": total,
        "page_size": page_size,
        "page_count": page_count,
    }
    meta_fn = out_dir / "meta.json"
    with meta_fn.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[INFO] {PARTNER_ID} meta.json kész: {meta_fn}")


def main():
    if not FEED_URL:
        raise RuntimeError("Hiányzik a FEED_ONLINEMARKABOLT_URL környezeti változó!")

    # TELJES takarítás (régi kategória mappák is mennek)
    ensure_clean_out_dir(OUT_DIR)

    print(f"[INFO] {PARTNER_ID} feed letöltése: {FEED_URL}")
    resp = requests.get(FEED_URL, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Nem sikerült letölteni a feedet (HTTP {resp.status_code})")

    products = parse_xml_products(resp.content)
    print(f"[INFO] {PARTNER_ID} – XML termékek száma: {len(products)}")

    seen_ids = set()
    all_items = []

    for prod in products:
        try:
            item = normalize_item(prod)
        except Exception as e:
            print(f"[WARN] Hibás termék, kihagyva: {e!r}")
            continue

        if not item:
            continue

        # dedup id alapján
        pid = item.get("id")
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        all_items.append(item)

    print(f"[INFO] {PARTNER_ID} – normalizált sorok összesen: {len(all_items)}")

    write_pages(OUT_DIR, all_items, PAGE_SIZE)


if __name__ == "__main__":
    main()
