import os, json, math, xml.etree.ElementTree as ET, requests
from datetime import datetime
import re

FEED_URL  = os.environ.get("FEED_LAIFENSHOP_URL")
OUT_DIR   = "docs/feeds/laifenshop"
PAGE_SIZE = 300


# -------------- HELPEREK --------------

def clean_xml(text):
    if not text:
        return text
    # '&'-ek javítása, hogy az XML megfeleljen a szabványnak
    text = text.replace("& ", "&amp; ")
    text = text.replace(" &", " &amp;")
    if text == "&":
        text = "&amp;"
    return text


def get_child_text(prod, keylist):
    """
    Case-insensitive keresés: bármelyik tag megfejtése.
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
    except:
        return None


# -------------- MAIN ------------------

def main():
    if not FEED_URL:
        raise SystemExit("FEED_LAIFENSHOP_URL nincs beállítva.")

    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Letöltés: {FEED_URL}")
    r = requests.get(FEED_URL, timeout=60)
    r.raise_for_status()

    # XML javítás
    xml_text = clean_xml(r.text)
    root = ET.fromstring(xml_text)

    items = []

    for prod in root.findall(".//Product"):
        title = get_child_text(prod, ["Name", "ProductName", "Title"])
        if not title:
            continue

        pid = get_child_text(prod, ["Identifier", "ProductNumber", "Id"])
        if not pid:
            pid = title

        url = get_child_text(prod, ["ProductUrl", "ProductURL", "Url", "Product_Link"])
        img = get_child_text(prod, [
            "ImageUrl", "ImageURL", "Image",
            "Image1", "ImageUrl1", "ImageURL1"
        ])

        desc = get_child_text(prod, ["Description", "LongDescription", "ShortDescription"])
        price_raw = get_child_text(prod, ["Price", "SalePrice", "NetPrice"])
        price = to_price(price_raw)

        # fallback – ha nincs img → ProductUrl alapján is lehet képet keresni
        if not img:
            # Nincs thumbnail → üresen hagyjuk, Findora kezeli
            img = ""

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
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    # pages
    for i in range(pages):
        start = i * PAGE_SIZE
        end   = start + PAGE_SIZE
        chunk = items[start:end]

        page_path = os.path.join(OUT_DIR, f"page-{i+1:04d}.json")
        with open(page_path, "w", encoding="utf-8") as f:
            json.dump({"items": chunk}, f, ensure_ascii=False)

        print("Írva:", page_path)


if __name__ == "__main__":
    main()
