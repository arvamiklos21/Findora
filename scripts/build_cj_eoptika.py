import csv
import json
import math
from pathlib import Path

# BEMENET: CJ txt feed kicsomagolva ide
IN_DIR = Path("cj-eoptika-feed")

# KIMENET: GitHub Pages alá, innen megy ki: https://www.findora.hu/feeds/cj-eoptika/...
OUT_DIR = Path("docs/feeds/cj-eoptika")

PAGE_SIZE = 200

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- RÉGI OLDALAK TÖRLÉSE, HOGY NE MARADJON ROSSZ page-0001.json ----
for old in OUT_DIR.glob("page-*.json"):
    try:
        old.unlink()
    except OSError:
        pass

txt_files = sorted(IN_DIR.glob("*.txt"))
if not txt_files:
    raise SystemExit("Nincs .txt fájl a CJ eOptika feedben :(")

feed_file = txt_files[0]
items = []


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


# ---- CSV olvasás / delimiter felismerés ----
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

        item = {
            "id": pid,
            "title": title,
            "desc": description,
            "url": url,
            "image": image,
            "price": final_price,
            "original_price": original_price,
            "currency": currency or "HUF",
            "brand": brand,
            "category": category,
            "partner": "eOptika (CJ)",
            "discount": discount,
        }
        items.append(item)

total = len(items)
print(f"DEBUG CJ EOPTIKA: összes termék: {total}")

# Ha tényleg nincs egyetlen termék sem: generáljunk egy üres 1. oldalt, hogy ne legyen 404
if total == 0:
    empty_payload = {
        "ok": True,
        "partner": "cj-eoptika",
        "page": 1,
        "total": 0,
        "items": [],
    }
    with (OUT_DIR / "page-0001.json").open("w", encoding="utf-8") as f:
        json.dump(empty_payload, f, ensure_ascii=False)

    meta = {
        "ok": True,
        "partner": "cj-eoptika",
        "total": 0,
        "pages": 1,
        "page_size": PAGE_SIZE,
        "pageSize": PAGE_SIZE,
    }
    with (OUT_DIR / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    print("⚠️ CJ eOptika: nincs termék → üres page-0001.json létrehozva.")
    raise SystemExit(0)

# ---- NEM ÜRES FEED: normál lapozás, page-0001.json MINDIG TELE LESZ ----
pages = math.ceil(total / PAGE_SIZE)

for page_num in range(1, pages + 1):
    start = (page_num - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = items[start:end]

    if not chunk:
        continue  # elvileg nem fordulhat elő, de biztos ami biztos

    payload = {
        "ok": True,
        "partner": "cj-eoptika",
        "page": page_num,
        "total": total,
        "items": chunk,
    }

    out_path = OUT_DIR / f"page-{page_num:04d}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

# ---- META ÍRÁSA ----
meta = {
    "ok": True,
    "partner": "cj-eoptika",
    "total": total,
    "pages": pages,
    "page_size": PAGE_SIZE,  # backend oldali név
    "pageSize": PAGE_SIZE,   # frontend JS is tudja olvasni
}

with (OUT_DIR / "meta.json").open("w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False)

print(f"✅ CJ eOptika kész: {total} termék, {pages} oldal.")
