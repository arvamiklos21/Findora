# scripts/build_decathlon.py
#
# Decathlon feed → Findora JSON oldalak (globál + kategória + akciós blokk)
#
# Kategorizálás: category_assignbase.assign_category
#   - partner: "decathlon"
#   - partner_default: "sport" (ha nem talál semmit, visszarakja "sport"-ba, NEM multi-ba)
#
# Kimenet:
#   docs/feeds/decathlon/meta.json, page-0001.json...              (globál)
#   docs/feeds/decathlon/<findora_cat>/meta.json, page-....json    (kategória)
#   docs/feeds/decathlon/akcios-block/meta.json, page-....json     (akciós blokk, discount >= 10%)

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

FEED_URL = os.environ.get("FEED_DECATHLON_URL")
OUT_DIR = Path("docs/feeds/decathlon")

# Globál feed: nagyobb lap
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
            n
            for n in root.iter()
            if strip_ns(n.tag) in ("item", "product", "shopitem", "entry")
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

        # kategóriázáshoz
        product_type = first(m, ("product_type", "g:product_type"))
        google_cat = first(m, ("google_product_category", "g:google_product_category"))
        brand = first(m, BRAND_KEYS)

        # category_path: ha mindkettő van, fűzzük össze
        if product_type and google_cat and product_type != google_cat:
            category_path = f"{product_type} | {google_cat}"
        else:
            category_path = product_type or google_cat or ""

        # Ár + akció
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
                "brand": brand or "",
            }
        )

    print(f"ℹ Decathlon: parse_items → {len(items)} nyers termék")
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
            # kép
            if not cur.get("img") and it.get("img"):
                cur["img"] = it["img"]
            # alacsonyabb ár
            if (it.get("price") or 0) and (not cur.get("price") or it["price"] < cur["price"]):
                cur["price"] = it["price"]
            # nagyobb kedvezmény
            if (it.get("discount") or 0) > (cur.get("discount") or 0):
                cur["discount"] = it["discount"]
            # ha az újban van hosszabb leírás, cseréljük
            if len(it.get("desc") or "") > len(cur.get("desc") or ""):
                cur["desc"] = it["desc"]
            # category_path / brand első érték maradhat (nem piszkáljuk)
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
    assert FEED_URL, "FEED_DECATHLON_URL hiányzik (repo Secrets)."

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
    print(f"ℹ Decathlon: dedup után {len(items)} termék")

    # ===== NORMALIZÁLÁS + KÖZÖS KATEGORIZÁLÁS =====
    rows = []
    for it in items:
        pid = it["id"]
        title = it["title"]
        desc = it.get("desc") or ""
        url = it.get("url") or ""
        img = it.get("img") or ""
        price = it.get("price")
        discount = it.get("discount")
        category_path = it.get("category_path") or ""
        # Decathlon feedben brand nem mindig tiszta, de ha lenne:
        brand = it.get("brand") or ""

        findora_main = assign_category(
            title=title,
            desc=desc,
            category_path=category_path,
            brand=brand,
            partner="decathlon",
            partner_default="sport",
        )

        row = {
            "id": pid,
            "title": title,
            "img": img,
            "desc": desc,
            "price": price,
            "discount": discount,
            "url": url,
            "partner": "decathlon",
            "category_path": category_path,
            "findora_main": findora_main,
            "cat": findora_main,
        }
        rows.append(row)

    total = len(rows)
    print(f"[INFO] Decathlon: normalizált sorok: {total}")

    # ===== HA NINCS EGYETLEN TERMÉK SEM =====
    if total == 0:
        # Globál üres meta
        paginate_and_write(
            OUT_DIR,
            [],
            PAGE_SIZE_GLOBAL,
            meta_extra={
                "partner": "decathlon",
                "scope": "global",
            },
        )

        # Minden kategóriára üres meta
        for slug in FINDORA_CATS:
            base_dir = OUT_DIR / slug
            paginate_and_write(
                base_dir,
                [],
                PAGE_SIZE_CAT,
                meta_extra={
                    "partner": "decathlon",
                    "scope": f"category:{slug}",
                },
            )

        # Akciós blokk üres meta
        akcio_dir = OUT_DIR / "akcios-block"
        paginate_and_write(
            akcio_dir,
            [],
            PAGE_SIZE_AKCIO_BLOCK,
            meta_extra={
                "partner": "decathlon",
                "scope": "akcios-block",
            },
        )

        print("⚠️ Decathlon: nincs termék → csak üres meta-k készültek.")
        return

    # ===== GLOBÁL FEED =====
    paginate_and_write(
        OUT_DIR,
        rows,
        PAGE_SIZE_GLOBAL,
        meta_extra={
            "partner": "decathlon",
            "scope": "global",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )

    # ===== KATEGÓRIA FEED-EK =====
    buckets = {slug: [] for slug in FINDORA_CATS}
    for row in rows:
        slug = row.get("findora_main") or "multi"
        if slug not in buckets:
            slug = "multi"
        buckets[slug].append(row)

    for slug, items_cat in buckets.items():
        base_dir = OUT_DIR / slug
        paginate_and_write(
            base_dir,
            items_cat,
            PAGE_SIZE_CAT,
            meta_extra={
                "partner": "decathlon",
                "scope": f"category:{slug}",
                "generated_at": datetime.utcnow().isoformat() + "Z",
            },
        )

    # ===== AKCIÓS BLOKK (discount >= 10%) =====
    akcios_items = [
        row for row in rows
        if row.get("discount") is not None and row["discount"] >= 10
    ]

    akcio_dir = OUT_DIR / "akcios-block"
    paginate_and_write(
        akcio_dir,
        akcios_items,
        PAGE_SIZE_AKCIO_BLOCK,
        meta_extra={
            "partner": "decathlon",
            "scope": "akcios-block",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )

    print(
        f"✅ Decathlon kész: {total} termék, "
        f"{len(buckets)} kategória (mindegyiknek meta), "
        f"akciós blokk tételek: {len(akcios_items)} → {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
