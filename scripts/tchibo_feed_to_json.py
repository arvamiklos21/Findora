# scripts/tchibo_feed_to_json.py
import json, re, requests, xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

FEED_URL = "https://transport.productsup.io/92670536fcbd28a5708a/channel/695671/HU_heureka.xml"
OUT_JSON = "docs/tchibo.json"
UA = "FindoraBot/1.0 (+https://www.findora.hu) Python-requests"

def norm_https(u: str) -> str:
    if not u: return ""
    try:
        from urllib.parse import urlsplit, urlunsplit
        s = u.strip().replace("]]", "")  # feed maradék lecsapása
        sp = urlsplit(s)
        if not sp.scheme:
            sp = sp._replace(scheme="https")
        if not sp.netloc and s.startswith("/"):
            sp = sp._replace(netloc="www.tchibo.hu")
        sp = sp._replace(fragment="")
        return urlunsplit(sp)
    except Exception:
        return ""

def first_url_from_text(txt: str) -> str:
    if not txt: return ""
    m = re.search(r"https?://[^\s,]+", txt)
    return m.group(0) if m else ""

def clean_price(p: str) -> str:
    if not p: return ""
    # elfogadja a "6 995,00" / "6995,00" formátumokat is
    x = re.findall(r"[\d\.,\s]+", p)
    if not x: return ""
    v = x[0].replace(" ", "")
    return v

def lower_tag(t):
    if not isinstance(t, str): return ""
    if t.startswith("{"):  # namespace lecsupaszítás
        t = t.split("}", 1)[1]
    return t.lower()

def product_to_record(node) -> dict:
    """
    Egy <product> csomópontból minden közvetlen gyerek TAG->TEXT mapet építünk,
    és több lehetséges kulcsból válogatunk (PRODUCTNAME/PRODUCT/TITLE, stb.)
    """
    fields = {}
    for ch in list(node):
        tag = lower_tag(ch.tag)
        val = (ch.text or "").strip()
        if val:
            fields[tag] = val

    # Kép: IMGURL, IMGURL_ALTERNATIVE1/2..., PARAM_MAIN_IMAGE, vagy ISBN-ben URL
    image = (
        fields.get("imgurl")
        or fields.get("param_main_image")
        or fields.get("image_link")
        or fields.get("main_image")
        or first_url_from_text(fields.get("isbn", ""))
        or ""
    )
    image = norm_https(image)

    # Ár: PRICE_VAT, különben PARAM_PRICE
    price = clean_price(fields.get("price_vat") or fields.get("param_price") or "")
    old_price = clean_price(fields.get("price_old") or fields.get("original_price") or "")

    # Leírás
    desc = fields.get("description") or fields.get("param_description_short") or ""

    # URL + article_id megtartása, sallangok levágása
    raw_url = fields.get("url") or fields.get("product_url") or fields.get("link") or ""
    raw_url = raw_url.replace("]]", "").strip()
    url = norm_https(raw_url)
    if url:
        try:
            from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
            sp = urlsplit(url)
            q = parse_qs(sp.query)
            new_q = {}
            if "article_id" in q and q["article_id"]:
                aid = q["article_id"][0].replace("]", "")
                new_q["article_id"] = aid
            sp = sp._replace(netloc="www.tchibo.hu", query=urlencode(new_q, doseq=True), fragment="")
            url = urlunsplit(sp)
        except Exception:
            pass

    # Cím
    title = (
        fields.get("productname")
        or fields.get("product")
        or fields.get("title")
        or fields.get("name")
        or ""
    )

    # Ha még mindig nincs cím, próbáljuk a URL-ből
    if not title and "/products/" in url:
        slug = url.split("/products/", 1)[-1]
        slug = re.split(r"[?&#]", slug)[0]
        title = re.sub(r"[-_]+", " ", slug).strip().capitalize()

    if not title or not url:
        return {}

    return {
        "title": title,
        "desc": desc,
        "url": url,
        "image": image,
        "price": price,
        "old_price": old_price,
    }

def parse_feed(xml_bytes: bytes):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ParseError:
        return items

    # products/product struktúra
    products = root.findall(".//product") or root.findall(".//PRODUCT") or []
    for p in products:
        rec = product_to_record(p)
        if rec:
            items.append(rec)
    return items

def main():
    headers = {
        "User-Agent": UA,
        "Accept": "application/xml,text/xml;q=1,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
    }
    r = requests.get(FEED_URL, headers=headers, timeout=90)
    r.raise_for_status()

    items = parse_feed(r.content)

    # Ha valamiért nem sikerül kinyerni, NE írjuk felül 0-val
    if not items:
        print("WARN: 0 tétel – a meglévő JSON érintetlen marad.")
        return

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"OK: {OUT_JSON} mentve, {len(items)} tétel.")

if __name__ == "__main__":
    main()
