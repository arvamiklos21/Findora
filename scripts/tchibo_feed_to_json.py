# scripts/tchibo_feed_to_json.py
import json, re, requests, xml.etree.ElementTree as ET

FEED_URL = "https://transport.productsup.io/92670536fcbd28a5708a/channel/695671/HU_heureka.xml"
OUT_PATH = "docs/tchibo.json"

def strip_ns(elem):
    """Eltávolítja az XML namespace-eket a fa egészéről."""
    for e in elem.iter():
        if isinstance(e.tag, str) and e.tag.startswith("{"):
            e.tag = e.tag.split("}", 1)[1]
    return elem

def txt(node, names):
    """Az első létező gyermek textjét adja vissza a 'names' listából."""
    for name in names:
        el = node.find(name)
        if el is not None and (el.text or "").strip():
            return el.text.strip()
    return ""

def clean_price(s: str) -> str:
    if not s: return ""
    s = s.strip()
    m = re.findall(r"[\d\.\,]+", s)
    return m[0] if m else ""

def ensure_https(u: str) -> str:
    if not u: return ""
    try:
        from urllib.parse import urlsplit, urlunsplit
        sp = urlsplit(u.strip())
        if not sp.scheme:
            sp = sp._replace(scheme="https")
        if not sp.netloc:
            return ""
        # Biztos, hogy Tchibo domainre mutat? (ha nem, nem baj – a frontenden dt-wrap úgyis átvisz)
        sp = sp._replace(fragment="")
        return urlunsplit(sp)
    except Exception:
        return ""

def main():
    print(f"Letöltés: {FEED_URL}")
    r = requests.get(FEED_URL, timeout=90)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    root = strip_ns(root)

    # Próbáljuk a legtipikusabb csomópontokat
    items_nodes = root.findall(".//SHOPITEM")
    if not items_nodes:
        items_nodes = root.findall(".//item")
    if not items_nodes:
        items_nodes = root.findall(".//PRODUCT")
    print(f"Talált csomópontok: {len(items_nodes)}")

    items = []
    dropped_no_title = 0
    dropped_no_url = 0

    for it in items_nodes:
        title = txt(it, ["PRODUCTNAME","PRODUCT","TITLE","NAME"])
        desc  = txt(it, ["DESCRIPTION","DESC","LONG_DESCRIPTION","FULL_DESCRIPTION","ANNOTATION"])
        # URL sokféleképpen jöhet
        url   = txt(it, ["URL","PRODUCT_URL","LINK","SHOPURL","DEEPLINK"])
        img   = txt(it, ["IMGURL","IMGURL_ALTERNATIVE","IMAGE","IMAGE_LINK","IMG","MAIN_IMAGE"])

        price = txt(it, ["PRICE_VAT","PRICE","PRICE_NEW","SELLING_PRICE"])
        price_old = txt(it, ["PRICE_OLD","OLD_PRICE","ORIGINAL_PRICE","PRICE_BEFORE"])

        if not title:
            dropped_no_title += 1
            continue

        url = ensure_https(url)
        if not url:
            # végső fallback: üresen hagyjuk – a frontend ettől még kirakja (csak nem lesz katt)
            dropped_no_url += 1
            continue

        rec = {
            "title": title,
            "desc":  desc,
            "url":   url,
            "image": img,
            "price": clean_price(price),
            "old_price": clean_price(price_old),
        }
        items.append(rec)

    print(f"Kimenthető tételek: {len(items)}")
    if dropped_no_title or dropped_no_url:
        print(f"Elhagyva (nincs title): {dropped_no_title}, (nincs url): {dropped_no_url}")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    # Log kedvéért mutatunk egy mintát
    if items:
        sample = {k: items[0].get(k) for k in ("title","url","price","old_price","image")}
        print("Minta:", json.dumps(sample, ensure_ascii=False))

if __name__ == "__main__":
    main()
