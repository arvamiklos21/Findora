import csv, json, math
from pathlib import Path

IN_DIR = Path("cj-jateknet-feed")
OUT_DIR = Path("docs/feeds/cj-jateknet")
PAGE_SIZE = 200

OUT_DIR.mkdir(parents=True, exist_ok=True)

txt_files = list(IN_DIR.glob("*.txt"))
if not txt_files:
    raise SystemExit("Nincs .txt fájl a CJ JátékNet feedben :(")

feed_file = txt_files[0]

items = []

def first(row, *keys):
    for k in keys:
        if k in row and row[k]:
            return row[k].strip()
    return None

def parse_price(v):
    if not v:
        return None
    v = v.replace(",", ".").split()[0]
    try:
        return float(v)
    except:
        return None

with feed_file.open("r", encoding="utf-8", newline="") as f:
    sample = f.read(2048)
    f.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,;|")
    except:
        dialect = csv.excel_tab

    reader = csv.DictReader(f, dialect=dialect)

    for row in reader:
        title = first(row, "TITLE")
        if not title:
            continue

        pid   = first(row, "ID")
        url   = first(row, "LINK", "ADS_REDIRECT")
        img   = first(row, "IMAGE_LINK")
        desc  = first(row, "DESCRIPTION") or ""

        sale  = parse_price(first(row, "SALE_PRICE"))
        price = parse_price(first(row, "PRICE"))

        final = sale or price
        orig  = price if sale and price and sale < price else None

        discount = None
        if orig and final and final < orig:
            discount = round((orig - final) / orig * 100)

        items.append({
            "id": pid,
            "title": title,
            "description": desc,
            "url": url,
            "image": img,
            "price": final,
            "original_price": orig,
            "currency": "HUF",
            "brand": first(row, "BRAND"),
            "category": first(
                row,
                "GOOGLE_PRODUCT_CATEGORY_NAME",
                "GOOGLE_PRODUCT_CATEGORY",
                "PRODUCT_TYPE"
            ),
            "partner": "JátékNet (CJ)",
            "discount": discount,
        })

total = len(items)
pages = max(1, math.ceil(total / PAGE_SIZE))

for i in range(pages):
    chunk = items[i*PAGE_SIZE:(i+1)*PAGE_SIZE]
    (OUT_DIR / f"page-{i+1:04d}.json").write_text(
        json.dumps({
            "ok": True,
            "partner": "cj-jateknet",
            "page": i+1,
            "total": total,
            "items": chunk
        }, ensure_ascii=False),
        encoding="utf-8"
    )

(OUT_DIR / "meta.json").write_text(json.dumps({
    "ok": True,
    "partner": "cj-jateknet",
    "total": total,
    "pages": pages,
    "page_size": PAGE_SIZE
}, ensure_ascii=False), encoding="utf-8")

print(f"OK JátékNet: {total} termék, {pages} oldal")
