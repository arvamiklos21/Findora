# scripts/build_cj_jatekshop.py
#
# CJ Jatekshop.eu feed → Findora JSON oldalak (globál + kategória + akciós blokk)
#
# BEMENET:
#   - CJ ZIP HTTP-ről:
#       CJ_FEED_URL    – DataTransfer ZIP URL (amiben benne van a Jatekshop.eu XML is)
#       CJ_HTTP_USER   – HTTP felhasználó
#       CJ_HTTP_PASS   – HTTP jelszó
#       CJ_API_TOKEN   – (opcionális, most nem használjuk)
#
#   - A ZIP-ben lévő Jatekshop.eu XML fájl neve:
#       Jatekshop_eu-Jatekshop_eu_google_all-shopping.xml
#
# Kategorizálás:
#   - NEM használjuk a category_assign-et
#   - MINDEN Jatekshop termék fő kategóriája: "jatekok"
#
# Kimenet:
#   docs/feeds/cj-jatekshop/meta.json, page-0001.json...              (globál)
#   docs/feeds/cj-jatekshop/<findora_cat>/meta.json, page-....json    (kategória – mind a 25 mappa létrejön)
#   docs/feeds/cj-jatekshop/akcio/meta.json, page-....json            (akciós blokk, discount >= 10%)

import os
import json
import math
import io
import zipfile
from pathlib import Path

import requests
import xml.etree.ElementTree as ET

from category_assignbase import FINDORA_CATS  # a 25 fő kategória listája

# KIMENET: GitHub Pages alá, innen megy ki: https://www.findora.hu/feeds/cj-jatekshop/...
OUT_DIR = Path("docs/feeds/cj-jatekshop")

# Globál feed: 200/lap
PAGE_SIZE_GLOBAL = 200

# Kategória feedek: 20/lap
PAGE_SIZE_CAT = 20

# Akciós blokk: 20/lap
PAGE_SIZE_AKCIO_BLOCK = 20

OUT_DIR.mkdir(parents=True, exist_ok=True)

# CJ HTTP / ZIP beállítások
CJ_FEED_URL = os.environ.get("CJ_FEED_URL")
CJ_HTTP_USER = os.environ.get("CJ_HTTP_USER")
CJ_HTTP_PASS = os.environ.get("CJ_HTTP_PASS")
CJ_API_TOKEN = os.environ.get("CJ_API_TOKEN")  # jelenleg nem használjuk, csak elérhető


# ====================== SEGÉDFÜGGVÉNYEK ======================

def parse_price(v, row_currency=None):
    """
    Ár parse:
      - '1234.56 HUF'
      - '1234,56 HUF'
      - '1234.56'
    """
    if not v:
        return None, row_currency or "HUF"

    raw = str(v).strip()
    parts = raw.split()

    if len(parts) >= 2:
        amount = parts[0].replace(",", ".")
        currency = parts[1]
    else:
        amount = raw.replace(",", ".")
        currency = row_currency or "HUF"

    try:
        value = float(amount)
    except Exception:
        return None, currency

    return value, currency


def paginate_and_write(base_dir: Path, items, page_size: int, meta_extra=None):
    """
    Általános lapozó + fájlkiíró:
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

    # Üres lista esetén is legyen legalább 1 oldal
    if total == 0:
        page_count = 1
    else:
        page_count = int(math.ceil(total / page_size))

    meta = {
        "total_items": total,
        "page_size": page_size,
        "page_count": page_count,
    }
    if meta_extra:
        meta.update(meta_extra)

    meta_path = base_dir / "meta.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    if total == 0:
        # Üres kategória/globál/akció: 1 oldal, üres items
        out_path = base_dir / "page-0001.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump({"items": []}, f, ensure_ascii=False)
    else:
        for page_no in range(1, page_count + 1):
            start = (page_no - 1) * page_size
            end = start + page_size
            page_items = items[start:end]

            out_path = base_dir / f"page-{page_no:04d}.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump({"items": page_items}, f, ensure_ascii=False)


def fetch_cj_zip(url: str, user: str = None, password: str = None) -> bytes:
    if not url:
        raise RuntimeError("CJ_FEED_URL nincs beállítva")

    auth = (user, password) if (user and password) else None
    print(f"[INFO] CJ ZIP letöltése: {url}")
    resp = requests.get(url, auth=auth, timeout=120)
    resp.raise_for_status()
    print("[INFO] CJ ZIP méret:", len(resp.content), "byte")
    return resp.content


def parse_jatekshop_from_zip(zip_bytes: bytes):
    """
    ZIP → Jatekshop.eu XML(ek) → nyers item lista.

    Csak azokat a fájlokat nézzük, amelyek nevében benne van:
      'Jatekshop_eu_google_all'
    pl. Jatekshop_eu-Jatekshop_eu_google_all-shopping.xml
    """
    items = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        print("[INFO] ZIP fájlok a csomagban:")
        for n in names:
            print("   -", n)

        target_files = [
            n for n in names
            if "Jatekshop_eu_google_all" in n
            and n.lower().endswith(".xml")
        ]

        if not target_files:
            print("⚠️ Nincs Jatekshop.eu XML a ZIP-ben (nem találtam 'Jatekshop_eu_google_all' nevű fájlt).")
            return items

        for name in target_files:
            print("[INFO] Jatekshop.eu XML feldolgozása:", name)
            with zf.open(name) as f:
                tree = ET.parse(f)
                root = tree.getroot()

                # A CJ feed szerkezete: <feed><entry>...</entry></feed>
                for entry in root.findall(".//entry"):
                    def get_text(tag_name: str) -> str:
                        el = entry.find(tag_name)
                        return (el.text or "").strip() if el is not None and el.text else ""

                    pid = get_text("id")
                    title = get_text("title")
                    description = get_text("description")
                    url = get_text("link")
                    image = get_text("image_link")

                    # Ha nincs cím vagy URL, akkor nem fogjuk tudni listázni → skip
                    if not (title and url):
                        continue

                    row_currency = get_text("currency")

                    raw_sale = get_text("sale_price")
                    raw_price = get_text("price")

                    sale_val, currency = parse_price(raw_sale, row_currency)
                    price_val, currency2 = parse_price(raw_price, row_currency or currency)

                    if not currency and currency2:
                        currency = currency2

                    final_price = sale_val or price_val
                    original_price = (
                        price_val if sale_val and price_val and sale_val < price_val else None
                    )

                    discount = None
                    if original_price and final_price and final_price < original_price:
                        discount = round((original_price - final_price) / original_price * 100)

                    brand = get_text("brand")
                    category = (
                        get_text("google_product_category_name")
                        or get_text("google_product_category")
                        or get_text("product_type")
                    )

                    items.append(
                        {
                            "id": pid,
                            "title": title,
                            "desc": description,
                            "url": url,
                            "image": image,
                            "price": final_price,
                            "original_price": original_price,
                            "currency": currency or "HUF",
                            "brand": brand,
                            "category_path": category or "",
                            "discount": discount,
                        }
                    )

    return items


# ====================== RÉGI FÁJLOK TAKARÍTÁSA ======================

# Minden régi JSON törlése (globál + kategória + akcio)
for old_json in OUT_DIR.rglob("*.json"):
    try:
        old_json.unlink()
    except OSError:
        pass


# ====================== FEED BETÖLTÉS (CJ ZIP + XML) ======================

raw_items = []

if not CJ_FEED_URL:
    print("⚠️ CJ_FEED_URL nincs beállítva – üres feedet generálunk.")
else:
    try:
        zip_bytes = fetch_cj_zip(CJ_FEED_URL, CJ_HTTP_USER, CJ_HTTP_PASS)
        raw_items = parse_jatekshop_from_zip(zip_bytes)
    except Exception as e:
        print(f"⚠️ Hiba a CJ ZIP feldolgozásakor (Jatekshop.eu): {e}")
        raw_items = []

total_raw = len(raw_items)
print(f"[INFO] CJ Jatekshop.eu: nyers termékek: {total_raw}")


# ====================== NORMALIZÁLÁS + KATEGÓRIA (fixen 'jatekok') ======================

rows = []

for m in raw_items:
    pid = m["id"]
    title = m["title"]
    desc = m["desc"] or ""
    url = m["url"]
    img = m["image"]
    price = m["price"]
    original_price = m["original_price"]
    currency = m["currency"]
    brand = m["brand"] or ""
    category_path = m["category_path"] or ""
    discount = m["discount"]

    # MINDEN Jatekshop termék fő kategóriája: 'jatekok'
    findora_main = "jatekok"
    if findora_main not in FINDORA_CATS:
        findora_main = "multi"

    row = {
        "id": pid,
        "title": title,
        "img": img,
        "desc": desc,
        "price": price,
        "original_price": original_price,
        "currency": currency,
        "discount": discount,
        "url": url,
        "partner": "cj-jatekshop",
        "category_path": category_path,
        "findora_main": findora_main,
        "cat": findora_main,
    }
    rows.append(row)

total = len(rows)
print(f"[INFO] CJ Jatekshop.eu: normalizált sorok: {total}")


# ====================== HA NINCS EGYETLEN TERMÉK SEM ======================

if total == 0:
    # Globál üres meta + üres page-0001
    paginate_and_write(
        OUT_DIR,
        [],
        PAGE_SIZE_GLOBAL,
        meta_extra={
            "partner": "cj-jatekshop",
            "scope": "global",
        },
    )

    # Minden kategóriára üres meta + üres page-0001
    for slug in FINDORA_CATS:
        base_dir = OUT_DIR / slug
        paginate_and_write(
            base_dir,
            [],
            PAGE_SIZE_CAT,
            meta_extra={
                "partner": "cj-jatekshop",
                "scope": f"category:{slug}",
            },
        )

    # Akciós blokk üres meta + üres page-0001
    akcio_dir = OUT_DIR / "akcio"
    paginate_and_write(
        akcio_dir,
        [],
        PAGE_SIZE_AKCIO_BLOCK,
        meta_extra={
            "partner": "cj-jatekshop",
            "scope": "akcio",
        },
    )

    print("⚠️ CJ Jatekshop.eu: nincs termék → csak üres meta-k + page-0001.json készült.")
    raise SystemExit(0)


# ====================== GLOBÁL FEED ======================

paginate_and_write(
    OUT_DIR,
    rows,
    PAGE_SIZE_GLOBAL,
    meta_extra={
        "partner": "cj-jatekshop",
        "scope": "global",
    },
)


# ====================== KATEGÓRIA FEED-EK ======================

buckets = {slug: [] for slug in FINDORA_CATS}

for row in rows:
    slug = row.get("findora_main") or "multi"
    if slug not in buckets:
        slug = "multi"
    buckets[slug].append(row)

for slug, items in buckets.items():
    base_dir = OUT_DIR / slug
    paginate_and_write(
        base_dir,
        items,
        PAGE_SIZE_CAT,
        meta_extra={
            "partner": "cj-jatekshop",
            "scope": f"category:{slug}",
        },
    )


# ====================== AKCIÓS BLOKK (discount >= 10%) ======================

akcios_items = [
    row for row in rows
    if row.get("discount") is not None and row["discount"] >= 10
]

akcio_dir = OUT_DIR / "akcio"
paginate_and_write(
    akcio_dir,
    akcios_items,
    PAGE_SIZE_AKCIO_BLOCK,
    meta_extra={
        "partner": "cj-jatekshop",
        "scope": "akcio",
    },
)

print(
    f"✅ CJ Jatekshop.eu kész: {total} termék, "
    f"{len(buckets)} kategória (mindegyiknek meta + legalább page-0001.json), "
    f"akciós blokk tételek: {len(akcios_items)} → {akcio_dir}"
)
