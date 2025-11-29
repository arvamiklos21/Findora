# scripts/build-onlinemarkabolt.py
#
# OnlineMárkaboltok → Findora paginált JSON feed, kategóriákra bontva
#
# Bemenet:
#   - XML feed (FEED_ONLINEMARKABOLT_URL környezeti változó)
#
# Kimenet:
#   - docs/feeds/onlinemarkabolt/<findora_cat>/meta.json
#   - docs/feeds/onlinemarkabolt/<findora_cat>/page-0001.json, ...
#   - docs/feeds/onlinemarkabolt/akcio/meta.json
#   - docs/feeds/onlinemarkabolt/akcio/page-0001.json, ...
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
#         "discount": 23,
#         "url": "https://www.onlinemarkaboltok.hu/...",
#         "partner": "onlinemarkabolt",
#         "category_path": "BLANCO > ...",
#         "category_root": "BLANCO",
#         "findora_main": "haztartasi_gepek" | "otthon" | ...,
#         "cat": "haztartasi_gepek" | "otthon" | ...
#       }
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
from pathlib import Path

# --- hogy a scripts/ alatti modulok is látszódjanak ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from category_onlinemarkabolt_assign import assign_category  # partner-specifikus assigner
from category_assignbase import FINDORA_CATS  # közös 25 Findora fő kategória


# ====== KONFIG ======
FEED_URL = os.environ.get("FEED_ONLINEMARKABOLT_URL")
OUT_DIR = Path("docs/feeds/onlinemarkabolt")

# JSON oldal méret (kategória + akciós bucket)
PAGE_SIZE_CAT = 300
PAGE_SIZE_AKCIO_BLOCK = 300

# Minden elérhető Findora fő kategória – ÜRESRE IS csinálunk meta.json-t + page-0001.json-t
ALL_FINDORA_CATS = list(FINDORA_CATS)

# Akciós bucket slug – frontend: /feeds/onlinemarkabolt/akcio/...
AKCIO_SLUG = "akcio"

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
    Egy <product> → Findora item + kat (Findora fő kategória).
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
        # ha az assigner valami ismeretlen slugot dob, otthon-ba tereljük
        kat = "otthon"

    category_root = extract_category_root(category, manufacturer)

    item = {
        "id": identifier,
        "title": name,
        "img": img,
        "desc": short_desc(desc_html),
        "price": price,
        "discount": discount,
        "url": url,
        "partner": "onlinemarkabolt",
        "category_path": category or "",
        "category_root": category_root or "",
        "findora_main": kat,
        "cat": kat,
    }
    return item, kat


def paginate_and_write(base_dir: Path, items, page_size: int, meta_extra=None):
    """
    base_dir/meta.json
    base_dir/page-0001.json, page-0002.json, ...

    FONTOS:
    - Üres lista esetén is létrejön:
        - meta.json
        - page-0001.json ({"items": []})
      így a frontend soha nem kap 404-et a page-0001.json-re.
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    total = len(items)

    # Üres kategória / akció esetén is legyen legalább 1 oldal
    if total == 0:
        page_count = 1
    else:
        page_count = int(math.ceil(total / float(page_size)))

    # stabil sorrend
    items_sorted = sorted(items, key=lambda x: str(x.get("id", "")))

    if total == 0:
        # Egy üres oldal items: []-szel
        page_obj = {"items": []}
        fn = base_dir / "page-0001.json"
        with fn.open("w", encoding="utf-8") as f:
            json.dump(page_obj, f, ensure_ascii=False)
        print(f"[INFO] OnlineMárkaboltok – {base_dir} page-0001.json (0 db, üres lista)")
    else:
        for i in range(page_count):
            start = i * page_size
            end = start + page_size
            page_items = items_sorted[start:end]

            page_obj = {"items": page_items}
            page_no = i + 1
            fn = base_dir / f"page-{page_no:04d}.json"
            with fn.open("w", encoding="utf-8") as f:
                json.dump(page_obj, f, ensure_ascii=False)
            print(
                f"[INFO] OnlineMárkaboltok – {base_dir.name} page-{page_no:04d}.json "
                f"({len(page_items)} db)"
            )

    meta = {
        "total_items": total,
        "page_size": page_size,
        "page_count": page_count,
    }
    if meta_extra:
        meta.update(meta_extra)

    meta_fn = base_dir / "meta.json"
    with meta_fn.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[INFO] OnlineMárkaboltok – {base_dir.name} meta.json kész: {meta_fn}")


def main():
    if not FEED_URL:
        raise RuntimeError("Hiányzik a FEED_ONLINEMARKABOLT_URL környezeti változó!")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Régi JSON-ok törlése (kategóriák + akcio + top meta),
    # hogy ne maradjanak régi page-0002 stb.
    for old_json in OUT_DIR.rglob("*.json"):
        try:
            old_json.unlink()
        except OSError:
            pass

    print(f"[INFO] OnlineMárkaboltok feed letöltése: {FEED_URL}")
    resp = requests.get(FEED_URL, timeout=90)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Nem sikerült letölteni az OnlineMárkaboltok feedet "
            f"(HTTP {resp.status_code})"
        )

    products = parse_xml_products(resp.content)
    print(f"[INFO] OnlineMárkaboltok – XML termékek száma: {len(products)}")

    # kat → item lista MINDEN Findora-kategóriára
    items_by_cat = {slug: [] for slug in ALL_FINDORA_CATS}
    seen_ids = set()
    cat_counts = {slug: 0 for slug in ALL_FINDORA_CATS}

    all_items = []

    for prod in products:
        try:
            norm = normalize_item(prod)
        except Exception as e:
            print(f"[WARN] Hibás termék, kihagyva: {e!r}")
            continue

        if not norm:
            continue

        item, kat = norm

        if item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])

        if kat not in items_by_cat:
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

    # ===== MINDEN Findora-kategóriára page-*.json + meta.json (üresre is) =====
    for cat_slug in ALL_FINDORA_CATS:
        cat_items = items_by_cat.get(cat_slug, [])
        base_dir = OUT_DIR / cat_slug
        paginate_and_write(
            base_dir,
            cat_items,
            PAGE_SIZE_CAT,
            meta_extra={
                "partner": "onlinemarkabolt",
                "scope": f"category:{cat_slug}",
            },
        )

    # ===== Akciós bucket: minden, ahol discount >= 10% =====
    akcio_items = [
        it
        for it in all_items
        if (it.get("discount") is not None and it.get("discount") >= AKCIO_MIN_DISCOUNT)
    ]
    print(
        f"[INFO] OnlineMárkaboltok – akciós termékek (discount>={AKCIO_MIN_DISCOUNT}%): "
        f"{len(akcio_items)} db"
    )

    akcio_dir = OUT_DIR / AKCIO_SLUG
    paginate_and_write(
        akcio_dir,
        akcio_items,
        PAGE_SIZE_AKCIO_BLOCK,
        meta_extra={
            "partner": "onlinemarkabolt",
            "scope": "akcio",
            "akcio_min_discount": AKCIO_MIN_DISCOUNT,
        },
    )

    # Globális meta – összesített infó
    global_meta = {
        "partner": "onlinemarkabolt",
        "source_url": FEED_URL,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_items": total_items,
        "page_size": PAGE_SIZE_CAT,
        "categories": cat_counts,
        "categories_list": ALL_FINDORA_CATS,
        "akcio_items": len(akcio_items),
        "akcio_min_discount": AKCIO_MIN_DISCOUNT,
    }
    meta_fn = OUT_DIR / "meta.json"
    with meta_fn.open("w", encoding="utf-8") as f:
        json.dump(global_meta, f, ensure_ascii=False, indent=2)
    print(f"[INFO] OnlineMárkaboltok – globális meta.json kész: {meta_fn}")


if __name__ == "__main__":
    main()
