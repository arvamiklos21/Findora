# scripts/build_otthonmarket.py
#
# OtthonMarket → GLOBAL ONLY feed (1000/json), NINCS kategória mappa, NINCS akció mappa.

import os
import re
import json
import math
import xml.etree.ElementTree as ET
import requests

from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from pathlib import Path

from category_assignbase import FINDORA_CATS
from category_assign_otthonmarket import assign_category as assign_otthonmarket_category

FEED_URL = os.environ.get("FEED_OTTHONMARKET_URL")
OUT_DIR = Path("docs/feeds/otthonmarket")
PAGE_SIZE_GLOBAL = 1000

def norm_price(v):
    if v is None:
        return None
    s = re.sub(r"[^\d.,-]", "", str(v)).replace(" ", "")
    if not s or s in ("-", ""):
        return None
    try:
        return int(round(float(s.replace(",", "."))))
    except Exception:
        digits = re.sub(r"[^\d]", "", str(v))
        return int(digits) if digits else None

def short_desc(t, maxlen=180):
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", str(t))
    t = re.sub(r"\s+", " ", t).strip()
    return (t[: maxlen - 1] + "…") if len(t) > maxlen else t

def strip_ns(tag):
    return tag.split("}")[-1].split(":")[-1].lower()

def collect_node(n):
    m = {}
    txt = (n.text or "").strip()
    k0 = strip_ns(n.tag)
    if txt:
        m.setdefault(k0, txt)
    for ak, av in (n.attrib or {}).items():
        m.setdefault(strip_ns(ak), av)
    for c in list(n):
        k = strip_ns(c.tag)
        v = (c.text or "").strip()
        if k in (
            "imgurl_alternative",
            "additional_image_link",
            "additional_image_url",
            "images",
            "image2",
            "image3",
        ):
            m.setdefault(k, [])
            if v:
                m[k].append(v)
        else:
            if v:
                m[k] = v
            else:
                sub = collect_node(c)
                for sk, sv in sub.items():
                    m.setdefault(sk, sv)
    return m

def first(d, keys):
    for raw in keys:
        k = raw.lower()
        v = d.get(k)
        if isinstance(v, list) and v:
            return v[0]
        if isinstance(v, str) and v.strip():
            return v.strip()
        if v not in (None, "", []):
            return v
    return None

TITLE_KEYS = ("productname", "title", "g:title", "name", "product_name")
LINK_KEYS  = ("url", "link", "g:link", "product_url", "product_link", "deeplink")
IMG_KEYS   = ("imgurl", "image_link", "image", "image_url", "g:image_link", "image1", "main_image_url")
IMG_ALT_KEYS = ("imgurl_alternative", "additional_image_link", "additional_image_url", "images", "image2", "image3")
DESC_KEYS  = ("description", "g:description", "long_description", "short_description", "desc", "popis")
BRAND_KEYS = ("brand", "g:brand", "g:manufacturer", "manufacturer")
CATEGORY_KEYS = ("category","param_category","categorytext","g:product_type","product_type")

NEW_PRICE_KEYS = (
    "price_vat","price_with_vat","price_final","price_huf",
    "g:sale_price","sale_price","g:price","price","price_amount","current_price","amount",
)
OLD_PRICE_KEYS = (
    "old_price","price_before","was_price","list_price","regular_price","g:price","price",
)

def parse_items(xml_text):
    root = ET.fromstring(xml_text)
    # find candidates
    candidates = []
    for path in (
        ".//channel/item",".//item",".//products/product",".//product",
        ".//SHOPITEM",".//shopitem",".//entry"
    ):
        nodes = root.findall(path)
        if nodes:
            candidates = nodes
            break

    if not candidates:
        candidates = [n for n in root.iter() if strip_ns(n.tag) in ("item","product","shopitem","entry")]

    items = []
    for n in candidates:
        m = collect_node(n)
        m = {(k.lower() if isinstance(k,str) else k): v for k,v in m.items()}

        pid   = first(m, ("g:id","id","item_id","sku","product_id","itemid"))
        title = first(m, TITLE_KEYS) or ""
        url   = first(m, LINK_KEYS)
        img   = first(m, IMG_KEYS)
        if not img:
            alt = first(m, IMG_ALT_KEYS)
            if isinstance(alt, list) and alt:
                img = alt[0]
            elif isinstance(alt, str):
                img = alt
        desc  = short_desc(first(m, DESC_KEYS))
        raw_cat_text = first(m, CATEGORY_KEYS) or ""
        brand = first(m, BRAND_KEYS) or ""

        price_new = None
        for k in NEW_PRICE_KEYS:
            price_new = norm_price(m.get(k))
            if price_new is not None:
                break

        old = None
        for k in OLD_PRICE_KEYS:
            old = norm_price(m.get(k))
            if old is not None:
                break

        discount = None
        if old and price_new and old > price_new:
            discount = round((1 - price_new / old) * 100)

        items.append({
            "id": pid or url or title,
            "title": title,
            "img": img or "",
            "desc": desc,
            "raw_cat": raw_cat_text,
            "brand": brand,
            "price": price_new,
            "discount": discount,
            "url": url or "",
        })

    return items

def dedup_size_variants(items):
    buckets = {}
    for it in items:
        # same dedup logic as others
        key = it.get("url") or it.get("id")
        cur = buckets.get(key)
        if not cur:
            buckets[key] = it
        else:
            if (it.get("price") or 0) and (not cur.get("price") or it["price"] < cur["price"]):
                cur["price"] = it["price"]
            if (it.get("discount") or 0) > (cur.get("discount") or 0):
                cur["discount"] = it["discount"]
    return list(buckets.values())

def paginate_and_write(base_dir:Path, items, page_size:int, meta_extra=None):
    base_dir.mkdir(parents=True, exist_ok=True)
    total = len(items)
    page_count = 1 if total==0 else int(math.ceil(total/page_size))

    meta = {"total_items":total, "page_size":page_size, "page_count":page_count}
    if meta_extra:
        meta.update(meta_extra)

    with (base_dir/"meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    if total==0:
        with (base_dir/"page-0001.json").open("w",encoding="utf-8") as f:
            json.dump({"items":[]},f,ensure_ascii=False)
        return

    items_sorted = sorted(items,key=lambda x:(x.get("id") or "",x.get("title") or ""))
    for i in range(page_count):
        start=i*page_size
        page_items = items_sorted[start:start+page_size]
        with (base_dir/f"page-{i+1:04d}.json").open("w",encoding="utf-8") as f:
            json.dump({"items":page_items},f,ensure_ascii=False)

def main():
    if not FEED_URL:
        raise RuntimeError("FEED_OTTHONMARKET_URL not set")

    OUT_DIR.mkdir(parents=True,exist_ok=True)
    # wipe old
    for old in OUT_DIR.rglob("*.json"):
        try: old.unlink()
        except: pass

    r = requests.get(FEED_URL,headers={"Accept":"application/xml"},timeout=150)
    r.raise_for_status()

    raw_items = parse_items(r.text)
    items = dedup_size_variants(raw_items)

    rows=[]
    for it in items:
        # assign partner category (only used for findora_main field)
        raw_cat = assign_otthonmarket_category(
            category=it.get("raw_cat",""),
            name=it.get("title",""),
            description=it.get("desc",""),
        )
        # ensure findora slug, fallback "otthon"
        findora_main = raw_cat if raw_cat in FINDORA_CATS else "otthon"

        rows.append({
            "id":it.get("id"),
            "title":it.get("title"),
            "img":it.get("img"),
            "desc":it.get("desc"),
            "price":it.get("price"),
            "discount":it.get("discount"),
            "url":it.get("url"),
            "partner":"otthonmarket",
            "brand":it.get("brand") or "",
            "findora_main":findora_main,
            "cat":findora_main,
        })

    paginate_and_write(
        OUT_DIR,
        rows,
        PAGE_SIZE_GLOBAL,
        meta_extra={"partner":"otthonmarket","scope":"global","generated_at":datetime.utcnow().isoformat()+"Z"}
    )

if __name__ == "__main__":
    main()
