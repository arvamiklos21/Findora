import csv, json, math
from pathlib import Path

IN_DIR = Path("cj-karcher-feed")
OUT_DIR = Path("docs/feeds/cj-karcher")
PAGE_SIZE = 200

OUT_DIR.mkdir(parents=True, exist_ok=True)

txt_files = list(IN_DIR.glob("*.txt"))
if not txt_files:
    raise SystemExit("Nincs .txt fájl a CJ feedben :(")

feed_file = txt_files[0]

items = []

def first_nonempty(row, *keys):
    """Adj vissza az első nem üres mezőt a megadott kulcsnevek közül."""
    for key in keys:
        if key in row and row[key]:
            return row[key].strip()
    return None

def parse_price(raw_value, row_currency=None):
    """Kezeli a '1234.56 HUF' és a '1234.56' + külön currency mező formátumot is."""
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
    reader = csv.DictReader(f, delimiter="\t")

    # Debug: logoljuk az oszlopneveket az első sor alapján
    first_row = None
    for idx, row in enumerate(reader):
        if idx == 0:
            first_row = row
            print("DEBUG CJ KARCHER HEADERS:", list(row.keys()))

        # --- FIELD MAPPING ---

        # ID – lehet 'id', 'sku', 'catalog-id' stb.
        pid = first_nonempty(
            row,
            "id",
            "item_id",
            "item-id",
            "sku",
            "manufacturer-sku",
            "catalog-id",
            "catalog_id"
        )

        # TITLE / NAME
        title = first_nonempty(
            row,
            "title",
            "name",
            "product-name",
            "product_name",
            "item_name"
        )

        # DESCRIPTION
        description = first_nonempty(
            row,
            "description",
            "long-description",
            "long_description",
            "short-description",
            "short_description"
        ) or ""

        # URL – vásárlási link
        url = first_nonempty(
            row,
            "link",
            "buy-url",
            "buy_url",
            "product-url",
            "product_url"
        )

        # KÉP
        image = first_nonempty(
            row,
            "image_link",
            "image-url",
            "image_url"
        )

        # CURRENCY – külön mező is lehet
        row_currency = first_nonempty(
            row,
            "currency",
            "currency-code",
            "currency_code"
        )

        # ÁR – sale -> retail -> price
        raw_sale = first_nonempty(
            row,
            "sale_price",
            "sale-price",
            "sale-price-amount",
            "sale_price_amount"
        )
        raw_price = first_nonempty(
            row,
            "price",
            "retail-price",
            "retail_price",
            "price-amount",
            "price_amount"
        )

        sale_val, currency = parse_price(raw_sale, row_currency)
        price_val, currency2 = parse_price(raw_price, row_currency or currency)
        if not currency and currency2:
            currency = currency2

        final_price = sale_val or price_val
        original_price = price_val if sale_val and price_val and sale_val < price_val else None

        discount = None
        if original_price and final_price and final_price < original_price:
            discount = round((original_price - final_price) / original_price * 100)

        # BRAND
        brand = first_nonempty(
            row,
            "brand",
            "manufacturer-name",
            "manufacturer",
            "brand-name"
        )

        # CATEGORY
        category = first_nonempty(
            row,
            "google_product_category",
            "product_type",
            "category",
            "advertiser-category"
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
            "partner": "Kärcher (CJ)",
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
        "partner": "cj-karcher",
        "page": page_num,
        "total": total,
        "items": chunk,
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

meta = {
    "ok": True,
    "partner": "cj-karcher",
    "total": total,
    "pages": pages,
    "page_size": PAGE_SIZE,
}
with (OUT_DIR / "meta.json").open("w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False)

print(f"✅ CJ Karcher kész: {total} termék, {pages} oldal.")
