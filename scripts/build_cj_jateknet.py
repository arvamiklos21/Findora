# scripts/build_cj_jateknet.py
#
# CJ JátékNet feed → Findora JSON oldalak (globál + kategória + akciós blokk)
#
# Kategorizálás:
#   - NEM használjuk a category_assign-et
#   - MINDEN JátékNet termék fixen a "jatekok" fő kategóriába kerül
#
# Kimenet:
#   docs/feeds/cj-jateknet/meta.json, page-0001.json...              (globál)
#   docs/feeds/cj-jateknet/<findora_cat>/meta.json, page-....json    (kategória – mind a 25 mappa létrejön)
#   docs/feeds/cj-jateknet/akcio/meta.json, page-....json            (akciós blokk, discount >= 10%)

import csv
import json
import math
from pathlib import Path

from category_assignbase import FINDORA_CATS  # csak a 25 fő kategória listája kell

IN_DIR = Path("cj-jateknet-feed")
OUT_DIR = Path("docs/feeds/cj-jateknet")

# Globál feed: 200/lap
PAGE_SIZE_GLOBAL = 200

# Kategória feedek: 20/lap
PAGE_SIZE_CAT = 20

# Akciós blokk: 20/lap
PAGE_SIZE_AKCIO_BLOCK = 20

OUT_DIR.mkdir(parents=True, exist_ok=True)


# ====================== SEGÉDFÜGGVÉNYEK ======================

def first(row, *keys):
    for k in keys:
        if k in row and row[k]:
            return str(row[k]).strip()
    return None


def parse_price(v):
    if not v:
        return None
    v = str(v).strip().replace(",", ".").split()[0]
    try:
        return float(v)
    except Exception:
        return None


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


# ====================== RÉGI FÁJLOK TAKARÍTÁSA ======================

for old_json in OUT_DIR.rglob("*.json"):
    try:
        old_json.unlink()
    except OSError:
        pass


# ====================== FEED BETÖLTÉS ======================

txt_files = list(IN_DIR.glob("*.txt"))
if not txt_files:
    raise SystemExit("Nincs .txt fájl a CJ JátékNet feedben :(")

feed_file = sorted(txt_files)[0]

raw_items = []

with feed_file.open("r", encoding="utf-8", newline="") as f:
    sample = f.read(2048)
    f.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,;|")
        print("DEBUG CJ JATEKNET DIALECT delimiter:", repr(dialect.delimiter))
    except Exception:
        dialect = csv.excel_tab
        print("DEBUG CJ JATEKNET DIALECT fallback: TAB")

    reader = csv.DictReader(f, dialect=dialect)

    for idx, row in enumerate(reader):
        if idx == 0:
            print("DEBUG CJ JATEKNET HEADERS:", list(row.keys()))

        title = first(row, "TITLE", "title")
        if not title:
            continue

        pid = first(row, "ID", "id", "ITEM_ID")
        url = first(row, "LINK", "ADS_REDIRECT", "link")
        img = first(row, "IMAGE_LINK", "image_link")
        desc = first(row, "DESCRIPTION", "description") or ""

        sale = parse_price(first(row, "SALE_PRICE", "sale_price"))
        price = parse_price(first(row, "PRICE", "price"))

        final = sale or price
        orig = price if sale and price and sale < price else None

        discount = None
        if orig and final and final < orig:
            discount = round((orig - final) / orig * 100)

        brand = first(row, "BRAND", "brand")
        category = first(
            row,
            "GOOGLE_PRODUCT_CATEGORY_NAME",
            "GOOGLE_PRODUCT_CATEGORY",
            "PRODUCT_TYPE",
            "product_type",
        )

        raw_items.append(
            {
                "id": pid,
                "title": title,
                "desc": desc,
                "url": url,
                "image": img,
                "price": final,
                "original_price": orig,
                "currency": "HUF",
                "brand": brand,
                "category_path": category or "",
                "discount": discount,
            }
        )

total_raw = len(raw_items)
print(f"[INFO] CJ JátékNet: nyers termékek: {total_raw}")


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

    # MINDEN JátékNet termék fő kategóriája: 'jatekok'
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
        "partner": "cj-jateknet",
        "category_path": category_path,
        "findora_main": findora_main,
        "cat": findora_main,
    }
    rows.append(row)

total = len(rows)
print(f"[INFO] CJ JátékNet: normalizált sorok: {total}")


# ====================== HA NINCS EGYETLEN TERMÉK SEM ======================

if total == 0:
    # Globál üres meta + üres page-0001
    paginate_and_write(
        OUT_DIR,
        [],
        PAGE_SIZE_GLOBAL,
        meta_extra={
            "partner": "cj-jateknet",
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
                "partner": "cj-jateknet",
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
            "partner": "cj-jateknet",
            "scope": "akcio",
        },
    )

    print("⚠️ CJ JátékNet: nincs termék → csak üres meta-k + page-0001.json készült.")
    raise SystemExit(0)


# ====================== GLOBÁL FEED ======================

paginate_and_write(
    OUT_DIR,
    rows,
    PAGE_SIZE_GLOBAL,
    meta_extra={
        "partner": "cj-jateknet",
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
            "partner": "cj-jateknet",
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
        "partner": "cj-jateknet",
        "scope": "akcio",
    },
)

print(
    f"✅ CJ JátékNet kész: {total} termék, "
    f"{len(buckets)} kategória (mindegyiknek meta + legalább page-0001.json), "
    f"akciós blokk tételek: {len(akcios_items)} → {OUT_DIR / 'akcio'}"
)
