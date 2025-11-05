# scripts/tchibo_feed_to_json.py
import json, xml.etree.ElementTree as ET, requests, re
from urllib.parse import urlparse

FEED_URL = "https://transport.productsup.io/92670536fcbd28a5708a/channel/695671/HU_heureka.xml"
OUT_PATH = "docs/tchibo.json"

def clean_price(s: str) -> str:
    if not s: return ""
    s = s.strip()
    # hagyjuk benne a számot és decimált, pontot vesszőt – frontenden formázzuk
    m = re.findall(r"[\d\.\,]+", s)
    return m[0] if m else ""

def ensure_tchibo_host(u: str) -> str:
    try:
        from urllib.parse import urlsplit, urlunsplit
        sp = urlsplit(u.strip())
        if not sp.scheme:  # ha hiányzik
            return "https://www.tchibo.hu/"
        host = "www.tchibo.hu"
        sp = sp._replace(scheme="https", netloc=host, fragment="")
        return urlunsplit(sp)
    except Exception:
        return "https://www.tchibo.hu/"

def main():
    r = requests.get(FEED_URL, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    # Heureka/Google-stílusú feedekben gyakori a <SHOPITEM> vagy <item>
    items = []
    for it in root.findall(".//SHOPITEM") + root.findall(".//item"):
        def txt(tag_names):
            for tag in tag_names:
                node = it.find(tag)
                if node is not None and (node.text or "").strip():
                    return node.text.strip()
            return ""

        title = txt(["PRODUCT", "PRODUCTNAME", "TITLE", "NAME"])
        desc  = txt(["DESCRIPTION", "DESC"])
        url   = txt(["URL", "LINK"])
        img   = txt(["IMGURL", "IMAGE", "IMAGE_LINK", "IMGURL_ALTERNATIVE"])

        price = txt(["PRICE_VAT", "PRICE", "PRICE_NEW", "SELLING_PRICE"])
        price_old = txt(["PRICE_OLD", "OLD_PRICE", "ORIGINAL_PRICE"])

        rec = {
            "title": title,
            "desc":  desc,
            "url":   ensure_tchibo_host(url),
            "image": img,
            "price": clean_price(price),
            "old_price": clean_price(price_old),
        }
        if rec["title"] and rec["url"]:
            items.append(rec)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
