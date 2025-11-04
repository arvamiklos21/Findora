# scripts/jateksziget_feed_to_json.py
# Letölti a Játéksziget (Dognet) XML-t és JSON-t készít belőle affiliate linkkel.

import json, re, sys, os
from urllib.parse import quote
import requests
import xml.etree.ElementTree as ET

FEED_URL = "https://dl.product-service.dognet.sk/fp/jateksziget.hu-arukereso.xml"
DOGNET_STD = "https://go.dognet.com/?dt=NGEc8ZwG&url="  # <- a TE dt kódod (ugyanaz, mint Tchibo)

OUT_PATH = os.path.join("docs", "jateksziget.json")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

def strip_ns(tag: str) -> str:
    if not tag:
        return ""
    return tag.split("}", 1)[-1].split(":", 1)[-1].upper()

def findtext_ci(elem: ET.Element, candidates):
    for c in candidates:
        for ch in elem:
            if strip_ns(ch.tag) == c:
                return (ch.text or "").strip()
    return ""

def wrap_affiliate(url: str) -> str:
    url = (url or "").strip()
    # ha több URL lenne a szövegben, az utolsót tartsuk
    urls = re.findall(r'https?://[^\s"]+', url)
    if urls:
        url = urls[-1]
    if not url:
        return ""
    # ha már Dognet-es, hagyjuk békén
    if "go.dognet.com" in url:
        return url
    return DOGNET_STD + quote(url, safe="")

def parse_price(s: str) -> str:
    if not s:
        return ""
    s = s.replace(" ", "").replace("HUF", "").replace("Ft", "").replace(",", ".")
    m = re.findall(r"[0-9]+(?:\.[0-9]+)?", s)
    if not m:
        return ""
    try:
        n = float(m[0])
        return f"{n:.2f}"
    except:
        return ""

def main():
    print(f"Letöltés: {FEED_URL}")
    r = requests.get(FEED_URL, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    items = []
    # Heureka/Árukereső-szerű feed: engedékeny elemnév-keresés
    def lname(x): return strip_ns(x.tag).upper()
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
            "url":   wrap_affiliate(url),
            "image": img,
            "price": parse_price(price)
        })

    print(f"OK, {len(items)} termék")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, separators=(",", ":"))

    print(f"→ Mentve: {OUT_PATH}")
    for row in items[:3]:
        p = (row.get("price") or "").replace(".", ",")
        print(f"- {row['title']} | {p} | {row['url'][:100]}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("HIBA:", e)
        sys.exit(1)
