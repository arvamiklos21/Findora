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
    # óvatosabb & kezelés – ne barmoljuk szét a URL-eket
    # csak a "magányos" &-eket próbáljuk javítani, de ez is minimálisan
    text = text.replace(" & ", " &amp; ")
    if text.strip() == "&":
        text = "&amp;"
    return text


def get_child_text(prod, keylist):
    """
    Case-insensitive, namespace- és formátum-toleráns keresés.
    - Minden leszármazottban keres (prod.iter())
    - Namespace levágása: {ns}Tag -> Tag
    - Kisbetűs, '_' kiszedve
    - Ha nincs .text, akkor attribútumokból is próbál olvasni (href, url, src, stb.)
    """
    target_keys = []
    for k in keylist:
        k_norm = k.lower().replace("_", "")
        target_keys.append(k_norm)

    for child in prod.iter():
        raw_tag = child.tag or ""
        # namespace levágás
        if "}" in raw_tag:
            raw_tag = raw_tag.split("}", 1)[1]
        tag_norm = raw_tag.lower().replace("_", "")

        if tag_norm in target_keys:
            txt = (child.text or "").strip()
            if txt:
                return txt

            # fallback: attribútumok (pl. <Url href="...">)
            for attr_val in child.attrib.values():
                val = (attr_val or "").strip()
                if val:
                    return val

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

    # Ha namespace lenne a Product-on, a findall(".//Product") lehet, hogy nem találja.
    # Ezért fallback: minden elem közül azokat nézzük, ahol a localname "Product".
    products = []
    for el in root.iter():
        tag = el.tag or ""
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        if tag.lower() == "product":
            products.append(el)

    print(f"Talált Product elemek száma: {len(products)}")

    for prod in products:
        title = get_child_text(prod, ["Name", "ProductName", "Title"])
        if not title:
            continue

        pid = get_child_text(prod, ["Identifier", "ProductNumber", "Id"])
        if not pid:
            pid = title

        url = get_child_text(
            prod,
            ["ProductUrl", "ProductURL", "Url", "Product_Link", "Link"]
        )
        img = get_child_text(
            prod,
            [
                "ImageUrl", "ImageURL", "Image",
                "Image1", "ImageUrl1", "ImageURL1",
                "ImageUrl2", "ImageURL2"
            ]
        )

        desc = get_child_text(prod, ["Description", "LongDescription", "ShortDescription"])
        price_raw = get_child_text(prod, ["Price", "SalePrice", "NetPrice"])
        price = to_price(price_raw)

        # ha valamiért még mindig nincs url / img, legyen inkább üres string
        url = url or ""
        img = img or ""

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
