import os
import sys
import re
import json
import math
import xml.etree.ElementTree as ET
import requests

from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# --- hogy a scripts/ alatti category_assign_tchibo.py-t is lássa, amikor a repo gyökeréből fut ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from category_assign_tchibo import assign_category as assign_tchibo_category

FEED_URL = os.environ.get("FEED_TCHIBO_URL")
OUT_DIR = "docs/feeds/tchibo"
PAGE_SIZE = 300  # kategória-oldal méret

# Findora 25 fő kategória (slugok) – mindig lesz mappa + meta.json
FINDORA_CATS = [
    "elektronika",
    "haztartasi_gepek",
    "szamitastechnika",
    "mobiltelefon",
    "gaming",
    "smart_home",
    "otthon",
    "lakberendezes",
    "konyha_fozes",
    "kert",
    "jatekok",
    "divat",
    "szepseg",
    "drogeria",
    "baba",
    "sport",
    "egeszseg",
    "latas",
    "allatok",
    "konyv",
    "utazas",
    "iroda_iskola",
    "szerszam_barkacs",
    "auto_motor",
    "multi",
]


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
    """Namespace + prefix levágása: {ns}tag vagy g:tag → tag, majd lower()."""
    return tag.split("}")[-1].split(":")[-1].lower()


def collect_node(n):
    """
    XML node → lapos dict:
      - kulcs: namespace/prefix nélküli tag/attribútum neve (lowercase)
      - érték: szöveg vagy lista (képek stb.)
    """
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
    """
    Az első nem üres értéket adja vissza a megadott kulcsok közül.
    A collect_node már lowercase kulcsokat ad, ezért itt is lower-eljük a kulcsneveket.
    """
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


def ensure_str(v):
    """Bármi jön (lista, dict, szám), legyen belőle egyetlen szöveg."""
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    if isinstance(v, dict):
        return " ".join(str(x) for x in v.values())
    return str(v or "")


# FIGYELEM: a collect_node már namespace/prefix nélkül menti a tag-eket,
# ezért itt NINCS "g:title", "g:price" stb., csak "title", "price", stb.

TITLE_KEYS = ("productname", "title", "name", "product_name")
LINK_KEYS = ("url", "link", "product_url", "product_link", "deeplink")
IMG_KEYS = (
    "imgurl",
    "image_link",
    "image",
    "image_url",
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
DESC_KEYS = ("description", "long_description", "short_description", "desc", "popis")

NEW_PRICE_KEYS = (
    "price_vat",
    "price_with_vat",
    "price_final",
    "price_huf",
    "sale_price",
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
    "price",           # fallback: ha csak egy ármező van
    "param_old_price", # Tchibo régi ár: PARAM_OLD_PRICE → "param_old_price"
)


def parse_items(xml_text):
    root = ET.fromstring(xml_text)

    # 1) Megpróbáljuk a tipikus struktúrákat
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

    # 2) Ha semmi nem jött be, akkor minden node közül szűrünk
    if not candidates:
        candidates = [
            n
            for n in root.iter()
            if strip_ns(n.tag) in ("item", "product", "shopitem", "entry")
        ]

    items = []
    for n in candidates:
        m = collect_node(n)
        # kulcsok: lowercase
        m = {(k.lower() if isinstance(k, str) else k): v for k, v in m.items()}

        pid = first(m, ("id", "item_id", "sku", "product_id", "itemid"))
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

        # Kategória / categoryPath forrásmezők – Tchibo-specifikus mezőkkel
        cat_raw = first(
            m,
            (
                "param_category",   # PARAM_CATEGORY → "param_category"
                "categorytext",     # CATEGORYTEXT → "categorytext"
                "categorypath",
                "product_type",
                "category",
                "product_category",
            ),
        )
        cat_path = ensure_str(cat_raw).strip()

        # Új ár
        price_new = None
        for k in NEW_PRICE_KEYS:
            price_new = norm_price(m.get(k))
            if price_new:
                break

        # Régi ár (akció előtti)
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

        # ===== Tchibo → Findora fő kategória (category_assign_tchibo.assign_category) =====
        fields = {
            "product_type": cat_path or "",
            "category": cat_path or "",
            "categorytext": cat_path or "",
            "title": title or "",
            "name": title or "",
            "description": raw_desc or "",
            "long_description": raw_desc or "",
        }
        findora_main = assign_tchibo_category(fields) or "multi"
        if findora_main not in FINDORA_CATS:
            findora_main = "multi"

        # Gyökér kategória kivétele (category_root)
        if cat_path and ">" in cat_path:
            category_root = cat_path.split(">")[0].strip()
        else:
            category_root = (cat_path or "").strip()

        # Alap item struktúra + Findora mezők
        item = {
            "id": pid or link or title,
            "title": title,
            "img": img or "",
            "desc": desc,
            "price": price_new,
            "discount": discount,
            "url": link or "",
            "partner": "tchibo",
            "category_path": cat_path or "",
            "category_root": category_root,
            "findora_main": findora_main,
            # kompatibilitás a régi kóddal
            "cat": findora_main,
        }

        items.append(item)

    print(f"ℹ Tchibo: parse_items → {len(items)} nyers termék")
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
    return list(buckets.values())


def main():
    assert FEED_URL, "FEED_TCHIBO_URL hiányzik (repo Secrets)."
    os.makedirs(OUT_DIR, exist_ok=True)

    r = requests.get(
        FEED_URL,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/xml"},
        timeout=120,
    )
    r.raise_for_status()

    raw_items = parse_items(r.text)
    items = dedup_size_variants(raw_items)
    print(f"ℹ Tchibo: dedup után {len(items)} termék")

    # ===== KATEGÓRIA SZERINT SZÉTOSZTÁS =====
    cat_buckets = {cat: [] for cat in FINDORA_CATS}
    for it in items:
        cat = it.get("findora_main") or "multi"
        if cat not in FINDORA_CATS:
            cat = "multi"
        cat_buckets[cat].append(it)

    # Per-kategória oldal + meta
    categories_meta = {}
    for cat in FINDORA_CATS:
        items_cat = cat_buckets.get(cat, [])
        cat_dir = os.path.join(OUT_DIR, cat)
        os.makedirs(cat_dir, exist_ok=True)

        total_cat = len(items_cat)
        pages_cat = max(1, math.ceil(total_cat / PAGE_SIZE))

        # Oldalak írása – üres kategóriánál is 1 üres page-0001.json,
        # hogy a frontend biztosan ne dobjon 404-et.
        for i in range(pages_cat):
            start = i * PAGE_SIZE
            end = (i + 1) * PAGE_SIZE
            chunk = items_cat[start:end]
            data = {"items": chunk}

            page_path = os.path.join(cat_dir, f"page-{str(i + 1).zfill(4)}.json")
            with open(page_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

        meta_cat = {
            "partner": "tchibo",
            "category": cat,
            "pageSize": PAGE_SIZE,
            "total": total_cat,
            "pages": pages_cat,
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "source": "productsup",
        }
        with open(os.path.join(cat_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta_cat, f, ensure_ascii=False)

        categories_meta[cat] = {
            "total": total_cat,
            "pages": pages_cat,
        }

    # TOP-LEVEL meta összesítve (NINCS többé közös page-*.json)
    grand_total = len(items)
    top_meta = {
        "partner": "tchibo",
        "pageSize": PAGE_SIZE,
        "total": grand_total,
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "source": "productsup",
        "categories": categories_meta,
    }
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(top_meta, f, ensure_ascii=False)

    print(f"✅ Tchibo: {grand_total} termék kategóriákra bontva → {OUT_DIR}")
    for cat in FINDORA_CATS:
        info = categories_meta[cat]
        print(f"   - {cat:20s}: {info['total']} termék, {info['pages']} oldal")


if __name__ == "__main__":
    main()
