import csv, json, math
from pathlib import Path

IN_DIR = Path("cj-eoptika-feed")
OUT_DIR = Path("docs/feeds/cj-eoptika")
PAGE_SIZE = 200

OUT_DIR.mkdir(parents=True, exist_ok=True)

txt_files = list(IN_DIR.glob("*.txt"))
if not txt_files:
    raise SystemExit("Nincs .txt fájl a CJ eOptika feedben :(")

feed_file = txt_files[0]

items = []

def first_nonempty(row, *keys):
    for key in keys:
        if key in row and row[key]:
            return row[key].strip()
    return None

def parse_price(raw_value, row_currency=None):
    if not raw_value:
        return None, row_currency or "HUF"
    raw_value = raw_value.strip()
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


with feed_file.open("r", encoding="utf-8", newline="") as f:
    sample = f.read(4096)
    f.seek(0)

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,;|")
        print("DEBUG CJ eOptika DIALECT delimiter:", repr(dialect.delimiter))
    except csv.Error:
        dialect = csv.excel_tab
        print("DEBUG CJ eOptika DIALECT fallback: TAB")

    reader = csv.DictReader(f, dialect=dialect)

    for idx, row in enumerate(reader):
        if idx == 0:
            print("DEBUG CJ eOptika HEADERS:", list(row.keys()))

        pid = first_nonempty(row, "ID")
        title = first_nonempty(row, "TITLE")
        description = first_nonempty(row, "DESCRIPTION") or ""
        url = first_nonempty(row, "LINK", "ADS_REDIRECT")
        image = first_nonempty(row, "IMAGE_LINK")

        row_currency = None
        raw_sale = first_nonempty(row, "SALE_PRICE")
        raw_price = first_nonempty(row, "PRICE")

        sale_val, currency = parse_price(raw_sale, row_currency)
        price_val, currency2 = parse_price(raw_price, row_currency or currency)

        if not currency and currency2:
            currency = currency2

        final_price = sale_val or price_val
        original_price = price_val if sale_val and price_val and sale_val < price_val else None

        discount = None
        if original_price and final_price and final_price < original_price:
            discount = round((original_price - final_price) / original_price * 100)

        brand = first_nonempty(row, "BRAND")
        category = first_nonempty(
            row,
            "GOOGLE_PRODUCT_CATEGORY_NAME",
            "GOOGLE_PRODUCT_CATEGORY",
            "PRODUCT_TYPE",
        )

        item = {
            "id": pid,
            "title": title,
            "description": description,
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
pages = max(1, math.ceil(total / PAGE_SIZE))

for i in range(pages):
    page_num = i + 1
    chunk = items[i * PAGE_SIZE : (i + 1) * PAGE_SIZE]
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

meta = {
    "ok": True,
    "partner": "cj-eoptika",
    "total": total,
    "pages": pages,
    "page_size": PAGE_SIZE,
}

with (OUT_DIR / "meta.json").open("w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False)

print(f"✅ CJ eOptika kész: {total} termék, {pages} oldal.")
