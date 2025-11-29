# scripts/build_cj_eoptika.py
#
# CJ eOptika feed → Findora JSON oldalak (globál + kategória + akciós blokk)
#
# Kategorizálás: category_assignbase.assign_category
#   - partner: "cj-eoptika"
#   - partner_default: "latas" (ha nem talál semmit, visszarakja "latas"-ba, NEM multi-ba)
#
# Kimenet:
#   docs/feeds/cj-eoptika/meta.json, page-0001.json...           (globál)
#   docs/feeds/cj-eoptika/<findora_cat>/meta.json, page-....json (kategória)
#   docs/feeds/cj-eoptika/akcio/meta.json, page-....json         (akciós blokk, discount >= 10%)

import csv
import json
import math
from pathlib import Path

from category_assignbase import assign_category, FINDORA_CATS

# Findora fő kategória SLUG-ok – a 25 menühöz igazítva + "akciok"
FINDORA_CATS = [
    "akciok",
    "elektronika",
    "haztartasi_gepek",
    "szamitastechnika",
    "mobil",
    "gaming",
    "smart_home",
    "otthon",
    "lakberendezes",
    "konyha_fozes",
    "kert",
    "jatekok",
    "divat",
    "szepseg",
    "drogeria",
    "baba",
    "sport",
    "egeszseg",
    "latas",
    "allatok",
    "konyv",
    "utazas",
    "iroda_iskola",
    "szerszam_barkacs",
    "auto_motor",
    "multi",
]

# BEMENET: CJ txt feed kicsomagolva ide
IN_DIR = Path("cj-eoptika-feed")

# KIMENET: GitHub Pages alá, innen megy ki: https://www.findora.hu/feeds/cj-eoptika/...
OUT_DIR = Path("docs/feeds/cj-eoptika")

# Globál feed: nagyobb lapméret
PAGE_SIZE_GLOBAL = 200

# Kategória feedek: 20/lap
PAGE_SIZE_CAT = 20

# Akciós blokk: 20/lap
PAGE_SIZE_AKCIO_BLOCK = 20

OUT_DIR.mkdir(parents=True, exist_ok=True)


# ====================== SEGÉDFÜGGVÉNYEK ======================

def first_nonempty(row, *keys):
    """Adj vissza az első nem üres mezőt a kulcsok közül."""
    for key in keys:
        if key in row and row[key]:
            return str(row[key]).strip()
    return None


def parse_price(raw_value, row_currency=None):
    """
    Kezeli a:
      - '1234.56 HUF'
      - '1234,56 HUF'
      - '1234.56' + külön currency mezőt.
    """
    if not raw_value:
        return None, row_currency or "HUF"

    raw_value = str(raw_value).strip()
    parts = raw_value.split()

    if len(parts) >= 2:
        amount = parts[0].replace(",", ".")
        currency = parts[1]
    else:
        amount = raw_value.replace(",", ".")
        currency = row_currency or "HUF"

    try:
        value = float(amount)
    except ValueError:
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


# ====================== RÉGI FÁJLOK TAKARÍTÁSA ======================

# Minden régi JSON törlése (globál + kategória + akcio)
for old_json in OUT_DIR.rglob("*.json"):
    try:
        old_json.unlink()
    except OSError:
        pass


# ====================== FEED BETÖLTÉS ======================

txt_files = sorted(IN_DIR.glob("*.txt"))
if not txt_files:
    raise SystemExit("Nincs .txt fájl a CJ eOptika feedben :(")

feed_file = txt_files[0]
raw_items = []

with feed_file.open("r", encoding="utf-8", newline="") as f:
    sample = f.read(4096)
    f.seek(0)

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,;|")
        print("DEBUG CJ EOPTIKA DIALECT delimiter:", repr(dialect.delimiter))
    except csv.Error:
        dialect = csv.excel_tab
        print("DEBUG CJ EOPTIKA DIALECT fallback: TAB")

    reader = csv.DictReader(f, dialect=dialect)

    for idx, row in enumerate(reader):
        if idx == 0:
            print("DEBUG CJ EOPTIKA HEADERS:", list(row.keys()))

        pid = first_nonempty(row, "ID", "id", "ITEM_ID")
        title = first_nonempty(row, "TITLE", "title")
        description = first_nonempty(row, "DESCRIPTION", "description") or ""
        url = first_nonempty(row, "LINK", "link", "ADS_REDIRECT")
        image = first_nonempty(row, "IMAGE_LINK", "image_link")

        # Ha nincs cím vagy URL, akkor nem fogjuk tudni listázni → skip
        if not (title and url):
            continue

        row_currency = first_nonempty(row, "CURRENCY", "currency")

        raw_sale = first_nonempty(row, "SALE_PRICE", "sale_price")
        raw_price = first_nonempty(row, "PRICE", "price")

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

        brand = first_nonempty(row, "BRAND", "brand")
        category = first_nonempty(
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

total_raw = len(raw_items)
print(f"DEBUG CJ EOPTIKA: nyers termékek: {total_raw}")


# ====================== NORMALIZÁLÁS + KATEGORIZÁLÁS ======================

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

    # Kategória besorolás – közös base
    findora_main = assign_category(
        title=title,
        desc=desc,
        category_path=category_path,
        brand=brand,
        partner="cj-eoptika",
        partner_default="latas",  # eOptika: alapértelmezett "látás"
    )

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
        "partner": "cj-eoptika",
        "category_path": category_path,
        "findora_main": findora_main,
        "cat": findora_main,
    }
    rows.append(row)

total = len(rows)
print(f"[INFO] CJ eOptika: normalizált sorok: {total}")

# ====================== HA NINCS EGYETLEN TERMÉK SEM ======================

if total == 0:
    # Globál üres meta + üres page-0001
    paginate_and_write(
        OUT_DIR,
        [],
        PAGE_SIZE_GLOBAL,
        meta_extra={
            "partner": "cj-eoptika",
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
                "partner": "cj-eoptika",
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
            "partner": "cj-eoptika",
            "scope": "akcio",
        },
    )

    print("⚠️ CJ eOptika: nincs termék → csak üres meta-k + page-0001.json készült.")
    raise SystemExit(0)


# ====================== GLOBÁL FEED ======================

paginate_and_write(
    OUT_DIR,
    rows,
    PAGE_SIZE_GLOBAL,
    meta_extra={
        "partner": "cj-eoptika",
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
            "partner": "cj-eoptika",
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
        "partner": "cj-eoptika",
        "scope": "akcio",
    },
)

print(
    f"✅ CJ eOptika kész: {total} termék, "
    f"{len(buckets)} kategória (mindegyiknek meta + legalább page-0001.json), "
    f"akciós blokk tételek: {len(akcios_items)} → {OUT_DIR / 'akcio'}"
)
