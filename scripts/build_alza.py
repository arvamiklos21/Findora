import os
import sys
import re
import json
import math
import xml.etree.ElementTree as ET
import requests

from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# --- hogy a scripts/ alatti category_assign.py-t is lássa ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from category_assign import assign_category


# ===== Feed URL-ek beolvasása (több XML támogatása) =====
def load_feed_urls():
    """
    FEED_ALZA_URLS: több soros vagy vesszővel elválasztott lista
    FEED_ALZA_URL: 1 darab URL (fallback)
    """
    raw = os.environ.get("FEED_ALZA_URLS", "").strip()
    if not raw:
        raw = os.environ.get("FEED_ALZA_URL", "").strip()

    if not raw:
        raise RuntimeError("Hiányzik a FEED_ALZA_URLS vagy FEED_ALZA_URL beállítás!")

    # Soronként vagy vesszővel elválasztva
    parts = []
    for line in raw.replace(",", "\n").splitlines():
        u = line.strip()
        if u:
            parts.append(u)

    if not parts:
        raise RuntimeError("FEED_ALZA_URL(S) üres – nincs egyetlen XML URL sem.")

    return parts


OUT_DIR = "docs/feeds/alza"
PAGE_SIZE = 300


# ===== Ár normalizálás =====
def norm_price(v):
    if v is None:
        return None
    s = re.sub(r"[^\d.,-]", "", str(v)).replace(" ", "")
    if not s or s in ("", "-"):
        return None
    try:
        return int(round(float(s.replace(",", "."))))
    except Exception:
        digits = re.sub(r"[^\d]", "", str(v))
        return int(digits) if digits else None


# ===== Rövidített leírás =====
def short_desc(t, maxlen=180):
    if not t:
        return None
    t = re.sub(r"<[^>]+>", " ", str(t))
    t = re.sub(r"\s+", " ", t).strip()
    return (t[: maxlen - 1] + "…") if len(t) > maxlen else t


# ===== Namespace eltávolítás =====
def strip_ns(tag):
    return tag.split("}")[-1].split(":")[-1].lower()


# ===== XML → dict konverzió =====
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
            # több kép – listába gyűjtjük
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


# ===== Első nem-üres mező =====
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


# Mező kulcs-listák
TITLE_KEYS = ("productname", "title", "g:title", "name")
LINK_KEYS = ("url", "link", "g:link", "product_url")
IMG_KEYS = ("imgurl", "image_link", "image", "image_url", "g:image_link", "image1")
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
)

OLD_PRICE_KEYS = (
    "old_price",
    "list_price",
    "was_price",
    "regular_price",
    "price_before",
)


def ensure_str(v):
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    if isinstance(v, dict):
        return " ".join(str(x) for x in v.values())
    return str(v or "")


# ===== XML feldolgozó =====
def parse_items(xml_text):
    root = ET.fromstring(xml_text)

    # 1) Szokásos path-ek
    candidates = []
    for path in (
        ".//SHOPITEM",
        ".//shopitem",
        ".//channel/item",
        ".//products/product",
        ".//product",
        ".//item",
    ):
        nodes = root.findall(path)
        if nodes:
            candidates = nodes
            break

    # 2) Ha semmi nem volt, fallback – bármely item/product/shopitem
    if not candidates:
        candidates = [
            n for n in root.iter() if strip_ns(n.tag) in ("item", "product", "shopitem")
        ]

    items = []
    for n in candidates:
        m = collect_node(n)
        m = {k.lower(): v for k, v in m.items()}

        pid = first(m, ("g:id", "id", "item_id", "sku"))

        title = first(m, TITLE_KEYS) or "Ismeretlen termék"
        link = first(m, LINK_KEYS)

        img = first(m, IMG_KEYS)
        if not img:
            alt = first(m, IMG_ALT_KEYS)
            if isinstance(alt, list) and alt:
                img = alt[0]
            elif isinstance(alt, str):
                img = alt

        raw_desc = ensure_str(first(m, DESC_KEYS))
        desc = short_desc(raw_desc)

        cat_path = first(
            m,
            (
                "categorytext",
                "product_type",
                "g:product_type",
                "category",
                "product_category",
            ),
        )

        # árak
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

        # Kategória → Findora
        # assign_category(product_type, title, description)
        findora_main = assign_category(cat_path or "", title or "", raw_desc or "")

        # category_root (első szegmens, ha '|' vagy '>' van)
        category_root = (cat_path or "").strip()
        for sep in (">", "|"):
            if sep in category_root:
                category_root = category_root.split(sep)[0].strip()
                break

        item = {
            "id": pid or link or title,
            "title": title,
            "img": img or "",
            "desc": desc,
            "price": price_new,
            "discount": discount,
            "url": link or "",
            "partner": "alza",
            "category_path": cat_path or "",
            "category_root": category_root,
            "findora_main": findora_main,
            "cat": findora_main,
        }

        items.append(item)

    return items


# ===== dedup méret/szín =====
SIZE_TOKENS = r"(?:XXS|XS|S|M|L|XL|XXL|\b\d{2}\b|\b\d{2}-\d{2}\b)"
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
    try:
        if not u:
            return u
        p = urlparse(u)
        q = dict(parse_qsl(p.query, keep_blank_values=True))
        for k in list(q.keys()):
            if k.lower() in ("size", "meret", "merete", "variant_size", "size_id"):
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
        base_url = strip_size_from_url(it.get("url"))
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
    return list(buckets.values())


# ===== main =====
def main():
    feed_urls = load_feed_urls()
    os.makedirs(OUT_DIR, exist_ok=True)

    all_items = []

    for url in feed_urls:
        print(f"Letöltés: {url}")
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=180)
        r.raise_for_status()

        items = parse_items(r.text)
        print(f"  → {len(items)} termék ebből a feedből")
        all_items.extend(items)

    print("Összes nyers termék (összes feed):", len(all_items))

    all_items = dedup_size_variants(all_items)
    print("Dedup után termékek:", len(all_items))

    # DEBUG: kategória stat (Alza category_path → darabszám)
    cat_counts = {}
    for it in all_items:
        cp = (it.get("category_path") or "").strip()
        if not cp:
            cp = "(nincs category_path)"
        cat_counts[cp] = cat_counts.get(cp, 0) + 1

    debug_path = os.path.join(OUT_DIR, "categories.json")
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(cat_counts, f, ensure_ascii=False, indent=2)

    print(f"DEBUG kategória stat mentve ide: {debug_path}")

    # Oldalak készítése
    pages = max(1, math.ceil(len(all_items) / PAGE_SIZE))
    for i in range(pages):
        data = {"items": all_items[i * PAGE_SIZE : (i + 1) * PAGE_SIZE]}
        with open(
            os.path.join(OUT_DIR, f"page-{str(i + 1).zfill(4)}.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(data, f, ensure_ascii=False)

    meta = {
        "partner": "alza",
        "pageSize": PAGE_SIZE,
        "total": len(all_items),
        "pages": pages,
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
    }

    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    print(f"✅ {len(all_items)} termék → {pages} oldal → {OUT_DIR}")


if __name__ == "__main__":
    main()
