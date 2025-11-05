# scripts/tchibo_feed_to_json.py
import json, re, requests, xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
from collections import Counter
from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qsl

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
            if v: return v
    return ""

def any_child(node, name_parts):
    parts = [p.lower() for p in name_parts]
    for el in list(node):
        tag = (el.tag or "").lower() if isinstance(el.tag, str) else ""
        if any(p in tag for p in parts):
            v = (el.text or "").strip()
            if v: return v
    return ""

def clean_price(s: str) -> str:
    if not s: return ""
    m = re.findall(r"[\d\.\,]+", s.strip())
    return m[0] if m else ""

def tidy_title(raw: str) -> str:
    if not raw: return ""
    t = raw
    # ha "123/valami" formátum, csak a név rész
    if "/" in t:
        t = t.split("/", 1)[1]
    # kötőjelekből szavak
    t = t.replace("-", " ").strip()
    if not t: t = raw.strip()
    # első betű nagy
    return t[:1].upper() + t[1:]

def cleanup_url(u: str) -> str:
    """Tchibo URL normalizálás: https, host, felesleges ']]' és track paramok törlése."""
    if not u: return ""
    raw = u.strip()
    raw = re.sub(r"\]\]+$", "", raw)  # záró CDATA maradék
    try:
        sp = urlsplit(raw)
        # relatív -> teljes
        if not sp.scheme and not sp.netloc and raw.startswith("/"):
            sp = urlsplit("https://www.tchibo.hu" + raw)
        if not sp.scheme:
            sp = sp._replace(scheme="https")
        host = sp.netloc or "www.tchibo.hu"
        # ha nem tchibo host, akkor is átirányítjuk a hivatalosra
        if "tchibo.hu" not in host:
            host = "www.tchibo.hu"
        # query tisztítás: csak article_id-t tartjuk meg, ha van
        q = dict(parse_qsl(sp.query, keep_blank_values=True))
        keep = {}
        if "article_id" in q and q["article_id"]:
            keep["article_id"] = q["article_id"].strip().rstrip("]")
        sp = sp._replace(netloc=host, fragment="", query=urlencode(keep))
        return urlunsplit(sp)
    except Exception:
        return "https://www.tchibo.hu/"

def extract_image_fallback(xml_text: str) -> str:
    # próbáljunk tchibo medias képet kifogni a nyers feedből
    m = re.search(r"https?://[^\"'\s]+/medias/[^\"'\s]+\.(?:jpg|jpeg|png|webp)", xml_text, re.I)
    return m.group(0) if m else ""

def parse_xml_to_items(xml_bytes):
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ParseError:
        return items
    root = strip_ns(root)

    # diagnosztika (logban látod)
    _tags = Counter()
    for e in root.iter():
        if isinstance(e.tag, str): _tags[e.tag] += 1
    print("Top tagek:", ", ".join(t for t,_ in _tags.most_common(20)))

    # ismert csomópontok
    nodes = (
        root.findall(".//SHOPITEM")
        or root.findall(".//shopitem")
        or root.findall(".//item")
        or root.findall(".//PRODUCT")
    )
    print("Talált klasszikus csomópontok:", len(nodes))

    for it in nodes:
        title = (
            txt1(it, ["PRODUCTNAME","PRODUCT","TITLE","NAME"])
            or any_child(it, ["productname","product","title","name"])
        )
        url   = (
            txt1(it, ["URL","PRODUCT_URL","LINK","SHOPURL","DEEPLINK","ITEM_URL"])
            or any_child(it, ["url","product_url","link","shopurl","deeplink","item_url"])
        )
        desc  = (
            txt1(it, ["DESCRIPTION","DESC","LONG_DESCRIPTION","FULL_DESCRIPTION","ANNOTATION"])
            or any_child(it, ["description","desc"])
        )
        # képek több mezőből
        img = (
            txt1(it, ["IMGURL","IMGURL_ALTERNATIVE","IMAGE","IMAGE_LINK","IMG","MAIN_IMAGE","IMAGE_URL","IMGURL_1"])
            or any_child(it, ["imgurl","image","image_link","main_image","image_url"])
        )
        price = (
            txt1(it, ["PRICE_VAT","PRICE","PRICE_NEW","SELLING_PRICE","SALE_PRICE"])
            or any_child(it, ["price_vat","price","sale_price"])
        )
        price_old = (
            txt1(it, ["PRICE_OLD","OLD_PRICE","ORIGINAL_PRICE","PRICE_BEFORE","REGULAR_PRICE"])
            or any_child(it, ["price_old","old_price","original_price","price_before","regular_price"])
        )

        # cím/URL kötelező
        url = cleanup_url(url)
        if not (title and url): 
            # próbálj címet url-ből
            if url and not title:
                title = tidy_title(url.split("/products/",1)[-1])
            if not (title and url):
                continue

        items.append({
            "title": tidy_title(title),
            "desc":  desc,
            "url":   url,
            "image": img,
            "price": clean_price(price),
            "old_price": clean_price(price_old),
        })

    return items

def regex_fallback_to_items(text_bytes):
    """Utolsó mentsvár: linkek a nyers feedből (ár/kép nélkül)."""
    txt = text_bytes.decode("utf-8", errors="replace")
    urls = set(re.findall(r"https?://(?:www\.)?tchibo\.hu/[^\s\"'<>()]*?products/[^\s\"'<>()]+", txt))
    urls |= set("https://www.tchibo.hu" + u for u in re.findall(r"(?<![a-zA-Z:])(/products/[^\s\"'<>()]+)", txt))
    items = []
    for u in list(urls)[:80]:
        cu = cleanup_url(u)
        title_guess = tidy_title(cu.split("/products/",1)[-1])
        items.append({"title": title_guess, "desc":"", "url": cu, "image":"", "price":"", "old_price":""})
    # egy képet próbálunk kimenteni a feedből, hogy legalább 1 legyen
    img = extract_image_fallback(txt)
    if img and items:
        items[0]["image"] = img
    return items

def main():
    headers = {
        "User-Agent": UA,
        "Accept": "application/xml,text/xml,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
    }
    r = requests.get(FEED_URL, headers=headers, timeout=90, allow_redirects=True)
    print("HTTP", r.status_code, "bytes=", len(r.content))
    save_bytes(OUT_XML, r.content)

    items = parse_xml_to_items(r.content)
    if not items:
        print("XML 0 tétel → REGEX fallback…")
        items = regex_fallback_to_items(r.content)

    if not items:
        print("NINCS KIMENTHETŐ TÉTEL – nem írjuk felül a meglévő JSON-t.")
        return

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Mentve: {OUT_JSON}  (összes tétel: {len(items)})")
    print("Minta:", json.dumps({k: items[0].get(k) for k in ("title","url")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
