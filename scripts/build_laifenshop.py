import os, json, math, xml.etree.ElementTree as ET, requests
from datetime import datetime
import re

FEED_URL  = os.environ.get("FEED_LAIFENSHOP_URL")
OUT_DIR   = "docs/feeds/laifenshop"
PAGE_SIZE = 300


# -------------- HELPEREK --------------

def clean_xml(text: str) -> str:
    """
    XML szöveg minimális javítása: az olyan '&'-eket, amik NEM entitások,
    átalakítjuk '&amp;'-re. Így az XML parser nem száll el.
    """
    if not text:
        return text
    # & amelyet nem követ 'amp;', 'lt;', 'gt;', 'quot;', 'apos;' vagy numerikus entitás
    return re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;)', '&amp;', text)


def get_child_text(prod, keylist):
    """
    Case-insensitive közvetlen gyerek tag keresés: bármelyik tag megfejtése.
    Nem megy rekurzívan – itt a Laifen feedben a fontos mezők közvetlen
    a <Product> alatt vannak (Name, ProductUrl, ImageUrl, Price, Description, ...).
    """
    for child in prod:
        tag = child.tag.lower()
        for key in keylist:
            if tag == key.lower():
                return (child.text or "").strip()
    return ""


def to_price(v):
    if not v:
        return None
    s = str(v).strip().replace(" ", "").replace(",", ".")
    try:
        return int(round(float(s)))
    except Exception:
        return None


# -------------- MAIN ------------------

def main():
    if not FEED_URL:
        raise SystemExit("FEED_LAIFENSHOP_URL nincs beállítva.")

    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Letöltés: {FEED_URL}")
    r = requests.get(FEED_URL, timeout=60)
    r.raise_for_status()

    # XML javítás + parse
    xml_text = clean_xml(r.text)
    root = ET.fromstring(xml_text)

    items = []

    # A Laifen feedben a termékek <Products><Product> alatt vannak
    for prod in root.findall(".//Product"):
        title = get_child_text(prod, ["Name", "ProductName", "Title"])
        if not title:
            continue

        pid = get_child_text(prod, ["Identifier", "ProductNumber", "Id"])
        if not pid:
            pid = title

        # URL – ez kell a "Megnézem🔗" gombhoz
        url = get_child_text(prod, [
            "ProductUrl", "ProductURL", "Url", "Product_Link"
        ])

        # Kép – elsődlegesen ImageUrl, de több variánst is megpróbálunk
        img = get_child_text(prod, [
            "ImageUrl", "ImageURL", "Image",
            "Image1", "ImageUrl1", "ImageURL1"
        ])

        desc = get_child_text(prod, ["Description", "LongDescription", "ShortDescription"])

        # Ár – sorrend: Price, SalePrice, NetPrice
        price_raw = get_child_text(prod, ["Price", "SalePrice", "NetPrice"])
        price = to_price(price_raw)

        item = {
            "id":       pid,
            "title":    title,
            "img":      img or "",
            "desc":     desc,
            "price":    price,
            "discount": None,
            "url":      url or "",
        }
        items.append(item)

    total = len(items)
    pages = max(1, math.ceil(total / PAGE_SIZE))

    meta = {
        "partner":     "laifenshop",
        "pageSize":    PAGE_SIZE,
        "total":       total,
        "pages":       pages,
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "source":      "feed"
    }

    # meta.json
    meta_path = os.path.join(OUT_DIR, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print("Írva:", meta_path)

    # pages
    for i in range(pages):
        start = i * PAGE_SIZE
        end   = start + PAGE_SIZE
        chunk = items[start:end]

        page_path = os.path.join(OUT_DIR, f"page-{i+1:04d}.json")
        with open(page_path, "w", encoding="utf-8") as f:
            json.dump({"items": chunk}, f, ensure_ascii=False)
        print("Írva:", page_path)

    # Logoljunk egy teszt sort, hogy a GitHub Actions logban is lásd:
    if items:
        print("First item debug:", {
            "title": items[0]["title"],
            "img": items[0]["img"],
            "url": items[0]["url"],
            "price": items[0]["price"],
        })


if __name__ == "__main__":
    main()
