#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, json, re
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests

FEED_URL = "https://dl.product-service.dognet.sk/fp/jateksziget.hu-arukereso.xml"
OUT_PATH = os.path.join("docs", "jateksziget.json")

# --- XML segédek ---

def strip_ns(tag: str) -> str:
    """Eltávolítja az XML namespace-et a tag-ból."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def findtext_ci(elem, names):
    """Case-insensitive child text keresés több lehetséges tag-névre."""
    want = {n.lower() for n in names}
    for ch in elem.iter():
        if strip_ns(ch.tag).lower() in want:
            t = (ch.text or "").strip()
            if t:
                return t
    return None

# --- Normalizálás / kulcsképzés ---

SIZE_WORDS = r"(?:xxxs|xxs|xs|s|m|l|xl|xxl|xxxl)"
REG_SIZE_PAREN = re.compile(r"\(\s*(?:méret|size)[^)]+\)", re.IGNORECASE)
REG_SIZE_COLON = re.compile(r"méret\s*[:\-]?\s*\S+", re.IGNORECASE)
REG_SIZE_STANDALONE = re.compile(rf"\b{SIZE_WORDS}\b", re.IGNORECASE)
REG_SIZE_SYSTEM = re.compile(r"\b(?:EU|UK|US)\s?\d+\b", re.IGNORECASE)
REG_WS = re.compile(r"\s{2,}")

def stem_title_no_size(s: str) -> str:
    """Címtörzs a méretminták SZŰRÉSÉVEL (színt nem bántjuk)."""
    if not s:
        return ""
    t = s.lower()
    t = REG_SIZE_PAREN.sub("", t)
    t = REG_SIZE_COLON.sub("", t)
    t = REG_SIZE_SYSTEM.sub("", t)
    t = REG_SIZE_STANDALONE.sub("", t)
    t = REG_WS.sub(" ", t)
    return t.strip()

def norm_url_for_key(u: str) -> str:
    """Kulcshoz: csak origin+path, query/hash nélkül (ha URL)."""
    if not u:
        return ""
    try:
        p = urlparse(u)
        return (f"{p.scheme}://{p.netloc}{p.path}").rstrip("/")
    except Exception:
        return (u.split("?")[0]).rstrip("/")

def parse_price_num(p) -> float:
    """Ár parse számra (Ft), ha nem sikerül, akkor NaN."""
    if p is None:
        return float("nan")
    s = str(p)
    # csak szám, pont, vessző
    s = re.sub(r"[^\d.,]", "", s)
    # európai formátum támogatás: vessző -> pont (tizedes)
    s = s.replace(",", ".")
    try:
        n = float(s)
        return n
    except Exception:
        return float("nan")

# --- Letöltés és feldolgozás ---

def fetch_xml(url: str) -> bytes:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content

def extract_items(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)

    def lname(x): return strip_ns(x.tag).upper()
    CAND_ITEM = {"SHOPITEM", "ITEM", "PRODUCT", "OFFER", "ENTRY"}

    items = []
    for it in (e for e in root.iter() if lname(e) in CAND_ITEM):
        title = (findtext_ci(it, ["PRODUCTNAME","PRODUCT","NAME","TITLE","ITEM_NAME"]) or "").strip()
        url   = (findtext_ci(it, ["URL","ITEM_URL","PRODUCTURL","LINK"]) or "").strip()
        img   = (findtext_ci(it, ["IMGURL","IMGURL_ALTERNATIVE","IMAGE","IMAGE_URL","IMG"]) or "").strip()
        price = (findtext_ci(it, ["PRICE_VAT","PRICE","PRICE_WITH_VAT","ITEM_PRICE","PRICE_FINAL"]) or "").strip()

        if not (title or url or img):
            continue

        items.append({
            "title": title,
            "url": url,
            "image": img,
            "price": price
        })

    return items

def dedupe_keep_color_drop_size(items):
    """
    Duplikáció kiszűrése: ugyanaz a termék (méret nélkül) csak egyszer maradjon.
    - Kulcs: norm_url_path + '|' + stem_title_no_size(title)
    - Ha több rekord ütközik: megtartjuk az OLCSÓBBAT és ha van jobb (nem üres) kép/URL, azzal frissítünk.
    - Színkülönbséget nem távolítjuk el: mivel a 'stem_title_no_size' csak a méretmintákat vágja,
      a „piros/kék/… ” a címben megmarad → eltérő kulcsot ad (ha az URL/path is más).
    """
    seen = {}
    for x in items:
        base = norm_url_for_key(x.get("url", "")) or ""
        stem = stem_title_no_size(x.get("title", ""))
        key = f"{base}|{stem}" if (base or stem) else x.get("title","").strip()

        price_num = parse_price_num(x.get("price"))
        rec = {
            "title": x.get("title",""),
            "url": x.get("url",""),
            "image": x.get("image",""),
            "price": x.get("price",""),
            "_price_num": price_num
        }

        if key in seen:
            prev = seen[key]
            # olcsóbb nyer; ha ár azonos/NaN, akkor az első marad
            if (price_num == price_num) and (prev["_price_num"] != prev["_price_num"] or price_num < prev["_price_num"]):
                # frissítjük olcsóbbra
                if rec["title"]: prev["title"] = rec["title"]
                if rec["url"]:   prev["url"]   = rec["url"]
                if rec["image"]: prev["image"] = rec["image"]
                prev["price"] = rec["price"]
                prev["_price_num"] = rec["_price_num"]
            else:
                # ha az előzőn nincs kép/URL és ezen van, pótoljuk
                if not prev.get("image") and rec.get("image"):
                    prev["image"] = rec["image"]
                if not prev.get("url") and rec.get("url"):
                    prev["url"] = rec["url"]
        else:
            seen[key] = rec

    # Vissza a "tiszta" mezők (belső _price_num nélkül)
    out = []
    for v in seen.values():
        out.append({
            "title": v["title"],
            "url": v["url"],
            "image": v["image"],
            "price": v["price"]
        })
    return out

def main():
    print(f"Letöltés: {FEED_URL}")
    xml_bytes = fetch_xml(FEED_URL)
    print("XML ok, feldolgozás…")

    raw_items = extract_items(xml_bytes)
    print(f"Nyers elemek: {len(raw_items)}")

    clean_items = dedupe_keep_color_drop_size(raw_items)
    print(f"Duplikátumok kiszűrve (méret eldobva, szín marad): {len(clean_items)}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(clean_items, f, ensure_ascii=False, indent=2)

    print(f"→ Mentve: {OUT_PATH}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("HIBA:", e, file=sys.stderr)
        sys.exit(1)
