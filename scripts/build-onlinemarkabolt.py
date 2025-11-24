# scripts/build-onlinemarkabolt.py
#
# OnlineMárkaboltok → Findora paginált JSON feed
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
#     "items": [
#       {
#         "id": "553",
#         "title": "...",
#         "img": "https://...",
#         "desc": "rövid leírás",
#         "price": 151840,
#         "discount": null,
#         "url": "https://www.onlinemarkaboltok.hu/...",
#         "categoryPath": "BLANCO > ...",
#         "kat": "otthon",
#         "findora_main": "otthon"
#       },
#       ...
#     ]
#   }

import os
import sys
import re
import json
import math
import shutil
import xml.etree.ElementTree as ET
import requests

from datetime import datetime

# --- hogy a scripts/ alatti assign modul is látszódjon ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from category_onlinemarkabolt_assign import assign_category  # saját kategória-assigner


# ====== KONFIG ======
FEED_URL  = os.environ.get("FEED_ONLINEMARKABOLT_URL")
OUT_DIR   = "docs/feeds/onlinemarkabolt"
PAGE_SIZE = 300  # forrásoldal / JSON page méret


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


def ensure_out_dir(path):
    os.makedirs(path, exist_ok=True)
    # régi page-*.json törlése, meta.json-t felülírjuk később
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


def normalize_item(prod):
    """
    Egy <product> → nyers dict + Findora item.
    prod: xml.etree.ElementTree.Element
    """
    identifier   = get_text(prod, "identifier") or get_text(prod, "code")
    name         = get_text(prod, "name")
    desc_html    = get_text(prod, "description")
    price_raw    = get_text(prod, "price")
    category     = get_text(prod, "category")
    img          = get_text(prod, "image_url")
    url          = get_text(prod, "product_url")
    manufacturer = get_text(prod, "manufacturer")

    # kötelező mezők hiánya esetén dobjuk
    if not identifier or not name or not url:
        return None

    price = norm_price(price_raw)

    # --- assign_category-hez mezők előkészítése ---
    fields_raw = {
        "id": identifier,
        "code": get_text(prod, "code"),
        "identifier": identifier,
        "name": name,
        "title": name,
        "description": desc_html,
        "category": category,
        "manufacturer": manufacturer,
        # extra aliasok, hogy a TEXT_TAG_KEYS biztosan találjon valamit
        "productname": name,
        "categorytext": category,
    }

    # kulcsok kisbetűsítve, None → ""
    fields = {str(k).lower(): (v if v is not None else "") for k, v in fields_raw.items()}

    kat = assign_category(fields) or "multi"
    findora_main = kat  # később ha akarod, itt lehet külön mappinget csinálni

    item = {
        "id": identifier,
        "title": name,
        "img": img,
        "desc": short_desc(desc_html),
        "price": price,
        "discount": None,          # a feedben jelenleg nincs külön akciós ár mező
        "url": url,
        "categoryPath": category or "",
        "kat": kat,
        "findora_main": findora_main,
    }
    return item, kat


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

    ensure_out_dir(OUT_DIR)

    items = []
    seen_ids = set()
    cat_counts = {}

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

        items.append(item)
        cat_counts[kat] = cat_counts.get(kat, 0) + 1

    print(f"[INFO] OnlineMárkaboltok – normalizált sorok: {len(items)}")
    print("[INFO] OnlineMárkaboltok – kategória statisztika:")
    for k in sorted(cat_counts.keys()):
        print(f"  - {k}: {cat_counts[k]} db")

    # ===== Pagelés + fájlírás =====
    total = len(items)
    if total == 0:
        print("[WARN] OnlineMárkaboltok – nincs egyetlen normalizált termék sem!")
    page_count = int(math.ceil(total / float(PAGE_SIZE))) if total else 0

    # stabil sorrend: azonosító szerint
    items.sort(key=lambda x: str(x["id"]))

    for i in range(page_count):
        start = i * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = items[start:end]

        page_obj = {"items": page_items}
        page_no = i + 1
        fn = os.path.join(OUT_DIR, f"page-{page_no:04d}.json")
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(page_obj, f, ensure_ascii=False, separators=(",", ":"))
        print(f"[INFO] OnlineMárkaboltok – írtam: {fn} ({len(page_items)} db)")

    # meta.json
    meta = {
        "partner": "onlinemarkabolt",
        "sourceUrl": FEED_URL,
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "totalItems": total,
        "pageSize": PAGE_SIZE,
        "pageCount": page_count,
        "categories": cat_counts,
    }
    meta_fn = os.path.join(OUT_DIR, "meta.json")
    with open(meta_fn, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[INFO] OnlineMárkaboltok – meta írás kész: {meta_fn}")


if __name__ == "__main__":
    main()
