import csv, json, math
from pathlib import Path

# Bemenet: a CJ ZIP-ből kibontott Shopping (Google) TXT
IN_DIR = Path("cj-karcher-feed")
OUT_DIR = Path("docs/feeds/cj-karcher")
PAGE_SIZE = 200  # hány termék/JSON oldal

OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1) TXT fájl keresése
txt_files = list(IN_DIR.glob("*.txt"))
if not txt_files:
    raise SystemExit("Nincs .txt fájl a CJ feedben :(")

feed_file = txt_files[0]

items = []

def parse_price(raw: str):
    """'1234.56 HUF' -> float(1234.56), currency 'HUF'"""
    if not raw:
        return None, None
    raw = raw.strip()
    parts = raw.split()
    amount = parts[0].replace(",", ".")
    currency = parts[1] if len(parts) > 1 else "HUF"
    try:
        value = float(amount)
    except ValueError:
        return None, currency
    return value, currency

with feed_file.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        raw_price = (row.get("price") or "").strip()
        raw_sale = (row.get("sale_price") or "").strip()

        price_val, currency = parse_price(raw_price)
        sale_val, _ = parse_price(raw_sale)

        final_price = sale_val or price_val
        original_price = price_val if sale_val and price_val and sale_val < price_val else None

        discount = None
        if original_price and final_price and final_price < original_price:
            discount = round((original_price - final_price) / original_price * 100)

        item = {
            "id": row.get("id"),
            "title": row.get("title"),
            "description": row.get("description") or "",
            "url": row.get("link"),
            "image": row.get("image_link"),
            "price": final_price,
            "original_price": original_price,
            "currency": currency or "HUF",
            "brand": row.get("brand"),
            "category": row.get("google_product_category") or row.get("product_type"),
            "partner": "Kärcher (CJ)",
            "discount": discount,
        }
        items.append(item)

total = len(items)
pages = max(1, math.ceil(total / PAGE_SIZE))

# 2) page-0001.json, page-0002.json, ...
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

# 3) meta.json
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
