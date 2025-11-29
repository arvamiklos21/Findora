# scripts/build_otthonmarket.py
#
# OtthonMarket feed → Findora JSON oldalak (globál + kategória + akciós blokk)
#
# Kategorizálás: category_assign_otthonmarket.assign_category
#   - partner: "otthonmarket"
#   - partner_default: "otthon" (ha nem talál semmit, visszarakja "otthon"-ba, NEM multi-ba)
#
# Kimenet:
#   docs/feeds/otthonmarket/meta.json, page-0001.json...              (globál)
#   docs/feeds/otthonmarket/<findora_cat>/meta.json, page-....json    (kategória)
#   docs/feeds/otthonmarket/akcio/meta.json, page-....json            (akciós blokk, discount >= 10%)

import os
import re
import json
import math
import xml.etree.ElementTree as ET
import requests

from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from pathlib import Path

# ===== kategória assignerek =====
# Közös 25 kategória lista
from category_assignbase import FINDORA_CATS
# Partner-specifikus logika
from category_assign_otthonmarket import assign_category as assign_otthonmarket_category

FEED_URL = os.environ.get("FEED_OTTHONMARKET_URL")
OUT_DIR = Path("docs/feeds/otthonmarket")

# Globál feed: 300/lap
PAGE_SIZE_GLOBAL = 300
# Kategória feedek: 20/lap
PAGE_SIZE_CAT = 20
# Akciós blokk: 20/lap
PAGE_SIZE_AKCIO_BLOCK = 20


# ---------- segédfüggvények (ugyanaz a logika, mint a laifenshop/karacsonydekor skriptekben) ----------

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
    "category",
    "param_category",
    "categorytext",
    "g:product_type",
    "product_type",
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

    # 1) klasszikus utak
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

    # 2) ha semmit nem találtunk: B-terv → bármilyen node, ahol a TAG-ben benne van 'item', 'product', 'offer', 'shop'
    if not candidates:
        for n in root.iter():
            t = strip_ns(n.tag)
            if any(x in t for x in ("item", "product", "offer", "shop")):
                candidates.append(n)

    # 3) ha így sincs semmi → üres listával vissza
    if not candidates:
        print("⚠ OtthonMarket: parse_items – nem találtam termék node-ot.")
        return []

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

        full_desc = first(m, DESC_KEYS)
        desc = short_desc(full_desc)

        # OtthonMarket kategória szöveg
        category_raw = first(m, CATEGORY_KEYS) or ""
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
                "raw_desc": full_desc or "",
                "price": price_new,
                "discount": discount,
                "url": link or "",
                "category_path": category_raw,  # közös név
                "brand": brand,
            }
        )

    print(f"ℹ OtthonMarket: parse_items → {len(items)} nyers termék")
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
        color = detect_color_token(it.get("title")) or detect_color_token(
            it.get("desc") or ""
        )
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

    FONTOS:
    - Üres lista esetén is létrejön:
        - meta.json
        - page-0001.json ({"items": []})
      így a frontend soha nem kap 404-et a page-0001.json-re.
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    total = len(items)

    # Üres lista esetén is legyen legalább 1 oldal
    if total == 0:
        page_count = 1
    else:
        page_count = int(math.ceil(total / page_size))

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

    if total == 0:
        out_path = base_dir / "page-0001.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump({"items": []}, f, ensure_ascii=False)
    else:
        for page_no in range(1, page_count + 1):
            start = (page_no - 1) * page_size
            end = start + page_size
            page_items = items[start:end]

            out_path = base_dir / f"page-{page_no:04d}.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump({"items": page_items}, f, ensure_ascii=False)


# ===== régi 'kat-*' slug → Findora slug =====

def map_otm_slug_to_findora(slug: str) -> str:
    """
    category_assign_otthonmarket.assign_category régi 'kat-*' ID-ket ad vissza.
    Itt lefordítjuk a Findora 25-ös slugokra.
    Ismeretlen / üres esetben: 'otthon'
    """
    if not slug:
        return "otthon"

    s = slug.strip().lower()

    mapping = {
        "kat-elektronika": "elektronika",
        "kat-gepek": "haztartasi_gepek",
        "kat-otthon": "otthon",
        "kat-jatekok": "jatekok",
        "kat-divat": "divat",
        "kat-szepseg": "szepseg",
        "kat-sport": "sport",
        "kat-konyv": "konyv",
        "kat-allatok": "allatok",
        "kat-latas": "latas",
        "kat-multi": "multi",
        "kat-kert": "kert",
        "kat-utazas": "utazas",
    }

    mapped = mapping.get(s, s)  # ha már eleve új slugot adna vissza, hagyjuk úgy

    if mapped not in FINDORA_CATS:
        # biztos fallback, NEM multi
        return "otthon"

    return mapped


# ---------- main ----------

def main():
    assert FEED_URL, "FEED_OTTHONMARKET_URL hiányzik (repo Secrets)."

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # régi JSON-ok törlése
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
    print(f"ℹ OtthonMarket: dedup után {len(items)} termék")

    # ===== NORMALIZÁLÁS + PARTNER-SPECIFIKUS KATEGORIZÁLÁS =====
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
        brand = it.get("brand") or ""  # itt most csak továbbvisszük, nem használjuk

        # Partner-specifikus assigner – RÉGI 'kat-*' ID-ket ad vissza
        raw_cat = assign_otthonmarket_category(
            category=category_path,
            name=title,
            description=desc,
        )

        findora_main = map_otm_slug_to_findora(raw_cat)

        row = {
            "id": pid,
            "title": title,
            "img": img,
            "desc": desc,
            "price": price,
            "discount": discount,
            "url": url,
            "partner": "otthonmarket",
            "category_path": category_path,
            "findora_main": findora_main,
            "cat": findora_main,
        }
        rows.append(row)

    total = len(rows)
    print(f"[INFO] OtthonMarket: normalizált sorok: {total}")

    # ===== HA NINCS EGYETLEN TERMÉK SEM =====
    if total == 0:
        # Globál üres meta + üres page-0001
        paginate_and_write(
            OUT_DIR,
            [],
            PAGE_SIZE_GLOBAL,
            meta_extra={
                "partner": "otthonmarket",
                "scope": "global",
            },
        )

        # Minden kategóriára üres meta + üres page-0001
        for slug in FINDORA_CATS:
            base_dir = OUT_DIR / slug
            paginate_and_write(
                base_dir,
                [],
                PAGE_SIZE_CAT,
                meta_extra={
                    "partner": "otthonmarket",
                    "scope": f"category:{slug}",
                },
            )

        # Akciós blokk üres meta + üres page-0001
        akcio_dir = OUT_DIR / "akcio"
        paginate_and_write(
            akcio_dir,
            [],
            PAGE_SIZE_AKCIO_BLOCK,
            meta_extra={
                "partner": "otthonmarket",
                "scope": "akcio",
            },
        )

        print("⚠️ OtthonMarket: nincs termék → csak üres meta-k + page-0001.json készült.")
        return

    # ===== GLOBÁL FEED =====
    paginate_and_write(
        OUT_DIR,
        rows,
        PAGE_SIZE_GLOBAL,
        meta_extra={
            "partner": "otthonmarket",
            "scope": "global",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )

    # ===== KATEGÓRIA FEED-EK =====
    buckets = {slug: [] for slug in FINDORA_CATS}
    for row in rows:
        slug = row.get("findora_main") or "otthon"
        if slug not in buckets:
            slug = "otthon"
            row["findora_main"] = "otthon"
            row["cat"] = "otthon"
        buckets[slug].append(row)

    for slug, items_cat in buckets.items():
        base_dir = OUT_DIR / slug
        paginate_and_write(
            base_dir,
            items_cat,
            PAGE_SIZE_CAT,
            meta_extra={
                "partner": "otthonmarket",
                "scope": f"category:{slug}",
                "generated_at": datetime.utcnow().isoformat() + "Z",
            },
        )

    # ===== AKCIÓS BLOKK (discount >= 10%) =====
    akcios_items = [
        row for row in rows
        if row.get("discount") is not None and row["discount"] >= 10
    ]

    akcio_dir = OUT_DIR / "akcio"
    paginate_and_write(
        akcio_dir,
        akcios_items,
        PAGE_SIZE_AKCIO_BLOCK,
        meta_extra={
            "partner": "otthonmarket",
            "scope": "akcio",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )

    print(
        f"✅ OtthonMarket kész: {total} termék, "
        f"{len(buckets)} kategória (mindegyiknek meta + legalább page-0001.json), "
        f"akciós blokk tételek: {len(akcios_items)} → {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
