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

# Ha 0 termék születik, NE írjuk felül a régi JSON-t,
# inkább álljon le hibával (így a workflow is fail lesz).
if total == 0:
    raise SystemExit(
        "❌ CJ eOptika feed feldolgozva, de 0 termék született – nem frissítem a JSON oldalakat."
    )

# ---- OLDALAK KÉSZÍTÉSE (NINCS ÜRES page-0001) ----
chunks = []
for start in range(0, total, PAGE_SIZE):
    chunk = items[start : start + PAGE_SIZE]
    if not chunk:
        continue
    chunks.append(chunk)

pages = len(chunks)

# Biztonság kedvéért: ha valamiért mégis üres lista lenne (elméletileg nem),
# akkor itt is megállunk.
if pages == 0:
    raise SystemExit("❌ CJ eOptika: üres pages lista – nem írok ki JSON-t.")

# ---- OLDALAK ÍRÁSA: mindig az első nem üres chunk lesz page-0001 ----
for idx, chunk in enumerate(chunks):
    page_num = idx + 1
    out_path = OUT_DIR / f"page-{page_num:04d}.json"

    payload = {
        "ok": True,
        "partner": "cj-eoptika",
        "page": page_num,
        "total": total,
        "items": chunk,
    }

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
