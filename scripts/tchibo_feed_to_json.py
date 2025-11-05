# scripts/tchibo_feed_to_json.py
import json, re, requests, xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
from collections import Counter

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
    """Relatív és protokoll-relatív Tchibo linkek normalizálása teljes https-re."""
    if not u: return ""
    try:
        from urllib.parse import urlsplit, urlunsplit
        raw = u.strip()
        sp = urlsplit(raw)
        # /products/... -> https://www.tchibo.hu/products/...
        if not sp.scheme and not sp.netloc and raw.startswith("/"):
            return "https://www.tchibo.hu" + raw
        # //www.tchibo.hu/... -> https://www.tchibo.hu/...
        if not sp.scheme and raw.startswith("//"):
            return "https:" + raw
        # nincs séma -> https
        if not sp.scheme:
            sp = sp._replace(scheme="https")
        if not sp.netloc:
            return ""
        sp = sp._replace(fragment="")
        return urlunsplit(sp)
    except Exception:
        return ""

def parse_xml_to_items(xml_bytes):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ParseError:
        return items
    root = strip_ns(root)

    # Diagnosztika
    tags = Counter()
    for e in root.iter():
        if isinstance(e.tag, str):
            tags[e.tag] += 1
    print("Top tagek:", ", ".join(t for t,_ in tags.most_common(20)))

    # Klasszikus + alternatív gyűjtés
    nodes = root.findall(".//SHOPITEM") or root.findall(".//item") or root.findall(".//PRODUCT")
    print("Klasszikus csomópontok:", len(nodes))
    if not nodes:
        cand = []
        for n in root.iter():
            nm = any_child(n, ["productname","product","title","name"])
            ul = any_child(n, ["url","product_url","link","shopurl","deeplink","item_url"])
            if nm and ul:
                cand.append(n)
        nodes = cand
        print("Heurisztikus csomópontok:", len(nodes))

    drop_title = drop_url = 0
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
    print(f"XML-ből kimenthető: {len(items)}  (eldobva title nélkül: {drop_title}, url nélkül: {drop_url})")
    return items

def regex_fallback_to_items(text_bytes):
    """Ha nem XML/üres a feed, REGEX-szel kinyerünk Tchibo termék URL-eket, és azokból építünk rekordot."""
    txt = text_bytes.decode("utf-8", errors="replace")
    # keresünk products linkeket
    urls = set(re.findall(r"https?://(?:www\.)?tchibo\.hu/[^\s\"'<>()]*?products/[^\s\"'<>()]+", txt))
    # plusz protokollrelatív/relatív linkek
    urls |= set("https://www.tchibo.hu" + u for u in re.findall(r"(?<!https:)(?<!http:)//(?:www\.)?tchibo\.hu/[^\s\"'<>()]*?products/[^\s\"'<>()]+", txt))
    urls |= set("https://www.tchibo.hu" + u for u in re.findall(r"(?<![a-zA-Z:])(/products/[^\s\"'<>()]+)", txt))

    items = []
    for u in list(urls)[:60]:  # ne szaladjon el
        # cím a slugból
        slug = u.split("/products/", 1)[-1]
        slug = re.split(r"[?&#]", slug)[0]
        slug_words = re.split(r"[-_]", slug)
        title_guess = " ".join(w for w in slug_words if w and len(w) > 1)
        title_guess = title_guess.strip().capitalize() or "Tchibo termék"
        items.append({
            "title": title_guess,
            "desc":  "",
            "url":   ensure_https(u),
            "image": "",
            "price": "",
            "old_price": "",
        })
    print(f"Regex fallback-találatok: {len(items)}")
    return items

def main():
    # Letöltés több fejléccel + mentés
    headers = {
        "User-Agent": UA,
        "Accept": "application/xml,text/xml,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
    }
    r = requests.get(FEED_URL, headers=headers, timeout=90, allow_redirects=True)
    print("HTTP", r.status_code, "bytes=", len(r.content))
    try:
        print("HEAD(500):", r.content[:500].decode("utf-8", errors="replace"))
    except Exception:
        pass
    r.raise_for_status()
    save_bytes(OUT_XML, r.content)
    print(f"RAW mentve: {OUT_XML}")

    # 1) XML parse
    items = parse_xml_to_items(r.content)

    # 2) Ha nincs semmi, regex fallback
    if not items:
        print("XML kinyerés 0—indul a REGEX fallback…")
        items = regex_fallback_to_items(r.content)

    # 3) Végső: ha még mindig 0, NE írjuk felül a meglévő JSON-t (fail-safe)
    if len(items) == 0:
        print("NINCS KIMENTHETŐ TÉTEL – a docs/tchibo.json változatlan marad (fail-safe).")
        return

    # Írás
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Mentve: {OUT_JSON}  (összes tétel: {len(items)})")
    print("Minta:", json.dumps({k: items[0].get(k) for k in ("title","url")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
