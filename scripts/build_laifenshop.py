import os, json, math, xml.etree.ElementTree as ET, requests
from datetime import datetime

FEED_URL  = os.environ.get("FEED_LAIFENSHOP_URL")
OUT_DIR   = "docs/feeds/laifenshop"
PAGE_SIZE = 300  # elég, mert 17 termék van

# ---------- kis helper függvények ----------

def txt(node, tag):
    """Biztonságos .find(tag).text"""
    if node is None:
        return ""
    el = node.find(tag)
    if el is None or el.text is None:
        return ""
    return el.text.strip()

def first_non_empty(node, tags):
    """Az első nem üres tag a listából"""
    for t in tags:
        v = txt(node, t)
        if v:
            return v
    return ""

def to_price(v):
    if not v:
        return None
    s = str(v).strip().replace(" ", "").replace(",", ".")
    try:
        return int(round(float(s)))
    except Exception:
        return None

# ---------- main ----------

def main():
    if not FEED_URL:
        raise SystemExit("FEED_LAIFENSHOP_URL nincs beállítva.")

    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Letöltés: {FEED_URL}")
    r = requests.get(FEED_URL, timeout=60)
    r.raise_for_status()

    root = ET.fromstring(r.content)

    items = []

    # A feed szerkezete: <Products><Product>...</Product>...</Products>
    for prod in root.findall(".//Product"):
        title = first_non_empty(prod, ["Name", "ProductName"])
        if not title:
            # ha nincs neve, inkább kihagyjuk
            continue

        pid = first_non_empty(prod, ["Identifier", "ProductNumber"])
        if not pid:
            pid = title

        url = first_non_empty(prod, ["ProductUrl", "ProductURL", "ProductUrl1", "ProductURL1"])
        img = first_non_empty(prod, [
            "ImageUrl", "ImageURL", "Image",
            "ImageUrl1", "ImageURL1"
        ])

        desc = first_non_empty(prod, ["Description", "LongDescription", "ShortDescription"])

        price_raw = first_non_empty(prod, ["Price", "SalePrice", "NetPrice"])
        price = to_price(price_raw)

        item = {
            "id":       pid,
            "title":    title,
            "img":      img,
            "desc":     desc,
            "price":    price,
            "discount": None,
            "url":      url,
        }
        items.append(item)

    total = len(items)
    pages = math.ceil(total / PAGE_SIZE) if total else 0

    meta = {
        "partner":     "laifenshop",
        "pageSize":    PAGE_SIZE,
        "total":       total,
        "pages":       pages or 1,
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "source":      "feed",
    }

    # meta.json
    meta_path = os.path.join(OUT_DIR, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print("Írva:", meta_path)

    # page-0001.json, page-0002.json, ...
    if total == 0:
        page_path = os.path.join(OUT_DIR, "page-0001.json")
        with open(page_path, "w", encoding="utf-8") as f:
            json.dump({"items": []}, f, ensure_ascii=False)
        print("Írva:", page_path)
        return

    for i in range(pages):
        start = i * PAGE_SIZE
        end   = start + PAGE_SIZE
        chunk = items[start:end]
        page_name = f"page-{i+1:04d}.json"
        page_path = os.path.join(OUT_DIR, page_name)
        with open(page_path, "w", encoding="utf-8") as f:
            json.dump({"items": chunk}, f, ensure_ascii=False)
        print("Írva:", page_path)


if __name__ == "__main__":
    main()
