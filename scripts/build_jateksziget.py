# scripts/build_jateksziget.py
#
# Játéksziget feed → Findora JSON oldalak (globál + kategória + akciós blokk)
#
# Kategorizálás: category_assignbase.assign_category
#   - partner: "jateksziget"
#   - partner_default: "jatekok" (ha nem talál semmit, visszarakja "jatekok"-ba, NEM multi-ba)
#
# Kimenet:
#   docs/feeds/jateksziget/meta.json, page-0001.json...              (globál)
#   docs/feeds/jateksziget/<findora_cat>/meta.json, page-....json    (kategória)
#   docs/feeds/jateksziget/akcios-block/meta.json, page-....json     (akciós blokk, discount >= 10%)

import os
import re
import json
import math
import xml.etree.ElementTree as ET
import requests

from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from pathlib import Path

from category_assignbase import assign_category, FINDORA_CATS

FEED_URL = os.environ.get("FEED_JATEKSZIGET_URL")
OUT_DIR = Path("docs/feeds/jateksziget")

# Globál feed: 300/lap (forrás-oldal méret)
PAGE_SIZE_GLOBAL = 300

# Kategória feedek: 20/lap
PAGE_SIZE_CAT = 20

# Akciós blokk: 20/lap
PAGE_SIZE_AKCIO_BLOCK = 20


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
        return None
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
LINK_KEYS = ("url", "link", "g:link", "product_url", "product_link", "deeplink")
IMG_KEYS = (
    "imgurl",
    "image_link",
    "image",
    "image_url",
    "g:image_link",
    "image1",
    "main_image_url",
)
IMG_ALT_KEYS = (
    "imgurl_alternative",
    "additional_image_link",
    "additional_image_url",
    "images",
    "image2",
    "image3",
)
DESC_KEYS = (
    "description",
    "g:description",
    "long_description",
    "short_description",
    "desc",
    "popis",
)
BRAND_KEYS = ("brand", "g:brand", "g:manufacturer", "manufacturer")
CATEGORY_KEYS = (
    "product_type",
    "g:product_type",
    "google_product_category",
    "g:google_product_category",
    "category",
    "kategoria",
)


NEW_PRICE_KEYS = (
    "price_vat",
    "price_with_vat",
    "price_final",
    "price_huf",
    "g:sale_price",
    "sale_price",
    "g:price",
    "price",
    "price_amount",
    "current_price",
    "amount",
)
OLD_PRICE_KEYS = (
    "old_price",
    "price_before",
    "was_price",
    "list_price",
    "regular_price",
    "g:price",
    "price",
)


def parse_items(xml_text):
    root = ET.fromstring(xml_text)
    candidates = []
    for path in (
        ".//channel/item",
        ".//item",
        ".//products/product",
        ".//product",
        ".//SHOPITEM",
        ".//shopitem",
        ".//entry",
    ):
        nodes = root.findall(path)
        if nodes:
            candidates = nodes
            break
    if not candidates:
        candidates = [
            n for n in root.iter() if strip_ns(n.tag) in ("item", "product", "shopitem", "entry")
        ]

    items = []
    for n in candidates:
        m = collect_node(n)
        m = {(k.lower() if isinstance(k, str) else k): v for k, v in m.items()}

        pid = first(m, ("g:id", "id", "item_id", "sku", "product_id", "itemid"))
        title = first(m, TITLE_KEYS) or "Ismeretlen termék"
        link = first(m, LINK_KEYS)

        img = first(m, IMG_KEYS)
        if not img:
            alt = first(m, IMG_ALT_KEYS)
            if isinstance(alt, list) and alt:
                img = alt[0]
            elif isinstance(alt, str):
                img = alt

        raw_desc = first(m, DESC_KEYS)
        desc = short_desc(raw_desc)

        # kategória + brand
        category_path = first(m, CATEGORY_KEYS) or ""
        brand = first(m, BRAND_KEYS) or ""

        price_new = None
        for k in NEW_PRICE_KEYS:
            price_new = norm_price(m.get(k))
            if price_new:
                break

        old = None
        for k in OLD_PRICE_KEYS:
            old = norm_price(m.get(k))
            if old:
                break

        discount = (
            round((1 - price_new / old) * 100)
            if old and price_new and old > price_new
            else None
        )

        items.append(
            {
                "id": pid or link or title,
                "title": title,
                "img": img or "",
                "desc": desc,
                "raw_desc": raw_desc or "",
                "price": price_new,
                "discount": discount,
                "url": link or "",
                "category_path": category_path,
                "brand": brand,
            }
        )
    print(f"ℹ Játéksziget: parse_items → {len(items)} nyers termék")
    return items


# ===== dedup: méret összevonás, szín marad =====
SIZE_TOKENS = r"(?:XXS|XS|S|M|L|XL|XXL|3XL|4XL|5XL|\b\d{2}\b|\b\d{2}-\d{2}\b)"
COLOR_WORDS = (
    "fekete",
    "fehér",
    "feher",
    "szürke",
    "szurke",
    "kék",
    "kek",
    "piros",
    "zöld",
    "zold",
    "lila",
    "sárga",
    "sarga",
    "narancs",
    "barna",
    "bézs",
    "bezs",
    "rózsaszín",
    "rozsaszin",
    "bordó",
    "bordeaux",
)


def normalize_title_for_size(t):
    if not t:
        return ""
    t0 = re.sub(r"\s+", " ", t.strip(), flags=re.I)
    t1 = re.sub(rf"\b{SIZE_TOKENS}\b", "", t0, flags=re.I)
    t1 = re.sub(r"\s{2,}", " ", t1).strip()
    return t1.lower()


def detect_color_token(t):
    if not t:
        return ""
    tl = t.lower()
    for w in COLOR_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", tl, flags=re.I):
            return w
    return ""


def strip_size_from_url(u):
    if not u:
        return u
    try:
        p = urlparse(u)
        q = dict(parse_qsl(p.query, keep_blank_values=True))
        for k in list(q.keys()):
            if k.lower() in ("size", "meret", "merete", "variant_size", "size_id", "meret_id"):
                q.pop(k, None)
        new_q = urlencode(q, doseq=True)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, p.fragment))
    except Exception:
        return u


def dedup_size_variants(items):
    buckets = {}
    for it in items:
        tnorm = normalize_title_for_size(it.get("title"))
        color = detect_color_token(it.get("title")) or detect_color_token(it.get("desc") or "")
        base_url = strip_size_from_url(it.get("url") or "")
        key = (tnorm, color or "", base_url or "")
        cur = buckets.get(key)
        if not cur:
            buckets[key] = it
        else:
            if not cur.get("img") and it.get("img"):
                cur["img"] = it["img"]
            if (it.get("price") or 0) and (not cur.get("price") or it["price"] < cur["price"]):
                cur["price"] = it["price"]
            if (it.get("discount") or 0) > (cur.get("discount") or 0):
                cur["discount"] = it["discount"]
            if len(it.get("desc") or "") > len(cur.get("desc") or ""):
                cur["desc"] = it["desc"]
    return list(buckets.values())


def paginate_and_write(base_dir: Path, items, page_size: int, meta_extra=None):
    """
    Általános lapozó + fájlkiíró:
      base_dir/meta.json
      base_dir/page-0001.json, page-0002.json, ...
    Üres lista esetén is ír meta.json-t (page_count=0), hogy a frontend ne kapjon 404-et.
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    total = len(items)
    page_count = int(math.ceil(total / page_size)) if total else 0

    meta = {
        "total_items": total,
        "page_size": page_size,
        "page_count": page_count,
    }
    if meta_extra:
        meta.update(meta_extra)

    meta_path = base_dir / "meta.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    for page_no in range(1, page_count + 1):
        start = (page_no - 1) * page_size
        end = start + page_size
        page_items = items[start:end]

        out_path = base_dir / f"page-{page_no:04d}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump({"items": page_items}, f, ensure_ascii=False)


def main():
    assert FEED_URL, "FEED_JATEKSZIGET_URL hiányzik (repo Secrets)."

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # régi JSON-ok törlése (globál + kategória + akcios-block)
    for old in OUT_DIR.rglob("*.json"):
        try:
            old.unlink()
        except OSError:
            pass

    r = requests.get(
        FEED_URL,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/xml"},
        timeout=120,
    )
    r.raise_for_status()

    raw_items = parse_items(r.text)
    items = dedup_size_variants(raw_items)
    print(f"ℹ Játéksziget: dedup után {len(items)} termék")

    # ===== NORMALIZÁLÁS + KÖZÖS KATEGORIZÁLÁS =====
    rows = []
    for it in items:
        pid = it["id"]
        title = it["title"]
        desc = it.get("desc") or ""
        url = it.get("url") or ""
        img = it.get("img") or ""
        price = it.get("price")
