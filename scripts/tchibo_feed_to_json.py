# scripts/tchibo_feed_to_json.py
import json, re, requests, xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

FEED_URL = "https://transport.productsup.io/92670536fcbd28a5708a/channel/695671/HU_heureka.xml"

# IDE írunk, mert nálad a /tchibo.json működik a weben
OUT_JSON = "tchibo.json"

UA = "FindoraBot/1.0 (+https://www.findora.hu) Python-requests"


def text(node):
    return (node.text or "").strip() if node is not None else ""


def find_txt_ci(parent, *tags):
    """Case-insensitive child keresés a megadott tag-nevekre."""
    if parent is None:
        return ""
    # próbáljuk direktben
    for t in tags:
        el = parent.find(t)
        if el is not None and text(el):
            return text(el)
    # case-insensitive kör: végigmegyünk a gyerekeken és hasonlítunk
    want = [t.lower() for t in tags]
    for el in list(parent):
        tag = (el.tag or "")
        tag_clean = tag.split("}", 1)[-1].lower()
        if tag_clean in want and text(el):
            return text(el)
    return ""


def clean_url(u: str) -> str:
    if not u:
        return ""
    s = u.strip()
    # feed végéről a dupla ']]' és egyéb whitespace eltávolítása
    s = re.sub(r"\]+$", "", s)
    try:
        from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
        sp = urlsplit(s)
        # relatív útból teljes URL
        if not sp.scheme and not sp.netloc:
            s = "https://www.tchibo.hu" + (s if s.startswith("/") else ("/" + s))
            sp = urlsplit(s)
        # csak https + host tisztítás
        scheme = "https"
        netloc = "www.tchibo.hu"
        # csak article_id param maradjon (ha van)
        qs = parse_qs(sp.query, keep_blank_values=False)
        keep = {}
        if "article_id" in qs and qs["article_id"]:
            aid = re.sub(r"\]+$", "", qs["article_id"][0])
            keep["article_id"] = aid
        return urlunsplit((scheme, netloc, sp.path, urlencode(keep), ""))
    except Exception:
        return "https://www.tchibo.hu/"


def clean_price_str(s: str) -> str:
    """Az eredeti árstring (pl. '6 995,00') első számtömbjét visszaadjuk, hogy a frontend szépen formázza."""
    if not s:
        return ""
    m = re.findall(r"[\d\.\,\s]+", s)
    return (m[0].strip() if m else "").replace("\xa0", " ").strip()


def product_to_record(p):
    # tipikus ProductsUp mezők
    title = (
        find_txt_ci(p, "PRODUCTNAME", "ProductName", "productname")
        or find_txt_ci(p, "PRODUCT", "Product", "product")
    )
    url = find_txt_ci(p, "URL", "Url", "url", "DEEPLINK", "deeplink")
    desc = (
        find_txt_ci(p, "DESCRIPTION", "Description", "description", "PARAM_DESCRIPTION_SHORT")
        or ""
    )
    img = (
        find_txt_ci(p, "IMGURL", "ImgUrl", "imgurl", "IMAGE_LINK", "image_link")
        or find_txt_ci(p, "IMGURL_ALTERNATIVE1", "IMGURL_ALTERNATIVE", "image", "MAIN_IMAGE")
        or ""
    )
    price = (
        find_txt_ci(p, "PRICE_VAT", "Price_VAT", "price_vat", "PRICE", "price", "PARAM_PRICE")
        or ""
    )
    price_old = (
        find_txt_ci(p, "PRICE_OLD", "old_price", "ORIGINAL_PRICE", "PRICE_BEFORE")
        or ""
    )

    if not title or not url:
        return None

    return {
        "title": title.strip(),
        "desc": desc.strip(),
        "url": clean_url(url),
        "image": img.strip(),
        "price": clean_price_str(price),
        "old_price": clean_price_str(price_old),
    }


def parse_feed(xml_bytes: bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ParseError:
        return []

    # ProductsUp: <products><product>...
    products = root.findall(".//product") or root.findall(".//PRODUCT") or []
    out = []
    for p in products:
        rec = product_to_record(p)
        if rec:
            out.append(rec)
    return out


def main():
    headers = {
        "User-Agent": UA,
        "Accept": "application/xml,text/xml,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
    }
    r = requests.get(FEED_URL, headers=headers, timeout=90)
    print("HTTP", r.status_code, "bytes=", len(r.content))
    r.raise_for_status()

    items = parse_feed(r.content)

    # Ha valamiért nulla (nem kéne), ne írjunk üreset – de nálad most kifejezetten kell a friss JSON:
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Mentve: {OUT_JSON}  (tételek: {len(items)})")
    if items:
        print("Minta:", json.dumps({k: items[0].get(k) for k in ("title", "url", "price", "image")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
