# scripts/tchibo_feed_to_json.py
import json, re, requests, xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

FEED_URL = "https://transport.productsup.io/92670536fcbd28a5708a/channel/695671/HU_heureka.xml"
OUT_JSON = "docs/tchibo.json"
OUT_XML  = "docs/tchibo.xml"
UA = "FindoraBot/1.0 (+https://www.findora.hu) Python-requests"

def save_bytes(path, data: bytes):
    with open(path, "wb") as f:
        f.write(data)

def strip_ns(elem):
    for e in elem.iter():
        if isinstance(e.tag, str) and e.tag.startswith("{"):
            e.tag = e.tag.split("}", 1)[1]
    return elem

def txt1(node, names):
    for name in names:
        el = node.find(name)
        if el is not None:
            v = (el.text or "").strip()
            if v:
                return v
    return ""

def any_child(node, name_parts):
    parts = [p.lower() for p in name_parts]
    for el in list(node):
        tag = (el.tag or "").lower() if isinstance(el.tag, str) else ""
        if any(p in tag for p in parts):
            v = (el.text or "").strip()
            if v:
                return v
    return ""

def clean_price(s: str) -> str:
    if not s: return ""
    m = re.findall(r"[\d\.\,]+", s.strip())
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
        sp = sp._replace(fragment="")
        return urlunsplit(sp)
    except Exception:
        return ""

def main():
    # 1) Letöltés + log + raw mentés
    r = requests.get(FEED_URL, headers={"User-Agent": UA}, timeout=90)
    print("HTTP", r.status_code, "bytes=", len(r.content))
    try:
        print("HEAD(500):", r.content[:500].decode("utf-8", errors="replace"))
    except Exception:
        pass
    r.raise_for_status()
    save_bytes(OUT_XML, r.content)
    print(f"RAW XML mentve: {OUT_XML}")

    # 2) XML parse
    try:
        root = ET.fromstring(r.content)
    except ParseError as e:
        print("XML parse hiba:", e)
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump([], f)
        return
    root = strip_ns(root)

    # 3) Klasszikus csomópontok
    nodes = root.findall(".//SHOPITEM") or root.findall(".//item") or root.findall(".//PRODUCT")
    print("Klasszikus csomópontok:", len(nodes))

    # 4) Heurisztika – ha még mindig 0
    if not nodes:
        cand = []
        for n in root.iter():
            nm = any_child(n, ["productname","product","title","name"])
            ul = any_child(n, ["url","product_url","link","shopurl","deeplink","item_url"])
            if nm and ul:
                cand.append(n)
        nodes = cand
        print("Heurisztikus csomópontok:", len(nodes))

    items, drop_title, drop_url = [], 0, 0
    for it in nodes:
        title = txt1(it, ["PRODUCTNAME","PRODUCT","TITLE","NAME"]) or any_child(it, ["productname","product","title","name"])
        url   = txt1(it, ["URL","PRODUCT_URL","LINK","SHOPURL","DEEPLINK","ITEM_URL"]) or any_child(it, ["url","product_url","link","shopurl","deeplink","item_url"])
        desc  = txt1(it, ["DESCRIPTION","DESC","LONG_DESCRIPTION","FULL_DESCRIPTION","ANNOTATION"]) or any_child(it, ["description","desc"])
        img   = txt1(it, ["IMGURL","IMGURL_ALTERNATIVE","IMAGE","IMAGE_LINK","IMG","MAIN_IMAGE"]) or any_child(it, ["img","image"])
        price = txt1(it, ["PRICE_VAT","PRICE","PRICE_NEW","SELLING_PRICE","SALE_PRICE"]) or any_child(it, ["price"])
        price_old = txt1(it, ["PRICE_OLD","OLD_PRICE","ORIGINAL_PRICE","PRICE_BEFORE","REGULAR_PRICE"]) or any_child(it, ["old"])

        if not title:
            drop_title += 1
            continue
        url = ensure_https(url)
        if not url:
            drop_url += 1
            continue

        items.append({
            "title": title,
            "desc":  desc,
            "url":   url,
            "image": img,
            "price": clean_price(price),
            "old_price": clean_price(price_old),
        })

    print(f"Kimenthető: {len(items)}  (eldobva title nélkül: {drop_title}, url nélkül: {drop_url})")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    if items:
        print("Minta:", json.dumps({k: items[0].get(k) for k in ("title","url","price","old_price","image")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
