# scripts/tchibo_feed_to_json.py
# Letölti a Tchibo Heureka (vagy hasonló) XML-t és JSON-t készít belőle affiliate linkekkel.

import json, re, sys, os
from urllib.parse import quote
import requests
import xml.etree.ElementTree as ET

# --- BEÁLLÍTÁSOK ---
FEED_URL = "https://transport.productsup.io/92670536fcbd28a5708a/channel/695671/HU_heureka.xml"

# Dognet standard deeplink (a te dt paramétereddel)
DOGNET_STD = "https://go.dognet.com/?dt=NGEc8ZwG&url="

OUT_PATH = os.path.join("docs", "tchibo.json")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

def strip_ns(tag: str) -> str:
    if not tag:
        return ""
    return tag.split("}", 1)[-1].split(":", 1)[-1].upper()

def findtext_ci(elem: ET.Element, candidates):
    """Namespace- és kis/nagybetű-független keresés a közvetlen gyerekek között."""
    want = {c.upper() for c in candidates}
    for ch in elem:
        if strip_ns(ch.tag) in want:
            return (ch.text or "").strip()
    return ""

def aff(url: str) -> str:
    url = (url or "").strip()
    urls = re.findall(r'https?://[^\s"]+', url)
    if urls:
        url = urls[-1]
    return (DOGNET_STD + quote(url, safe="")) if (url and DOGNET_STD) else url

def parse_price(s: str) -> str:
    if not s:
        return ""
    s = s.replace(" ", "").replace("HUF", "").replace("Ft", "")
    s = s.replace(",", ".")
    try:
        n = float(re.findall(r"[0-9]+(?:\.[0-9]+)?", s)[0])
        return f"{n:.2f}"
    except Exception:
        return ""

def main():
    print(f"Letöltés: {FEED_URL}")
    r = requests.get(FEED_URL, timeout=60)
    r.raise_for_status()

    root = ET.fromstring(r.content)

    items = []

    # Többféle lehetséges "termék" elem támogatása (ns-független)
    def lname(x):
        return strip_ns(x.tag).upper()
    CAND_ITEM = {"SHOPITEM", "ITEM", "PRODUCT", "OFFER", "ENTRY"}
    shopitems = [e for e in root.iter() if lname(e) in CAND_ITEM]

    for it in shopitems:
        title = (findtext_ci(it, [
            "PRODUCTNAME","PRODUCT","NAME","TITLE","ITEM_NAME"
        ]) or "").strip()
        url   = (findtext_ci(it, [
            "URL","ITEM_URL","PRODUCTURL","LINK"
        ]) or "").strip()
        img   = (findtext_ci(it, [
            "IMGURL","IMGURL_ALTERNATIVE","IMAGE","IMAGE_URL","IMG"
        ]) or "").strip()
        price = (findtext_ci(it, [
            "PRICE_VAT","PRICE","PRICE_WITH_VAT","ITEM_PRICE","PRICE_FINAL"
        ]) or "").strip()

        if not title or not url:
            continue

        items.append({
            "title": title,
            "url":   aff(url),
            "image": img,
            "price": parse_price(price)
        })

    print(f"OK, {len(items)} termék")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, separators=(",", ":"))

    print(f"→ Mentve: {OUT_PATH}")

    # rövid minta-log az első 3 tételből
    for row in items[:3]:
        p = (row.get("price") or "").replace(".", ",")
        print(f"- {row['title']} | {p} | {row['url'][:100]}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("HIBA:", e)
        sys.exit(1)
