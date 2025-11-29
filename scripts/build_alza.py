# scripts/build_alza.py
#
# ALZA feed(ek) → Findora JSON oldalak (csak KATEGÓRIA + AKCIÓS BLOKK)
#
# - Bemenet: FEED_ALZA_URL secret
#   → tartalmazhat 1 vagy több XML feed URL-t, szóközzel / sorvéggel / vesszővel elválasztva
# - Kategorizálás: ML modell (model_alza.pkl)
# - Kimenet:
#   docs/feeds/alza/<findora_cat>/meta.json, page-0001.json, ...
#   docs/feeds/alza/akcio/meta.json, page-0001.json, ...
#
# NINCS globális JSON (docs/feeds/alza/meta.json + page-0001.json).

import os
import re
import sys
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import requests
import joblib

# ===== ALAP KONFIG =====

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Alza ML modell
MODEL_FILE = os.path.join(SCRIPT_DIR, "model_alza.pkl")

# Kimeneti mappa
OUT_DIR = Path("docs/feeds/alza")

# Kategória feed: lapméret
PAGE_SIZE_CAT = 20

# Akciós blokk: lapméret
PAGE_SIZE_AKCIO = 20

# FEED URL(ek) – több URL is lehet, elválasztva whitespace / vessző / pontosvessző / |
FEED_URL_RAW = os.environ.get("FEED_ALZA_URL") or os.environ.get("ALZA_FEED_URL")

if not FEED_URL_RAW:
    raise RuntimeError(
        "Hiányzó FEED_ALZA_URL (vagy ALZA_FEED_URL) secret. "
        "Állítsd be a GitHub Actions Secrets között."
    )

# ===== FINDORA FŐ KATEGÓRIÁK (SLUG-ok) – 25 fix kategória =====
FINDORA_CATS = [
    "elektronika",
    "haztartasi_gepek",
    "szamitastechnika",
    "mobil",
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


# ===== SEGÉDFÜGGVÉNYEK =====

def split_feed_urls(raw: str):
    """
    FEED_ALZA_URL → lista, több URL is lehet
    Elválasztók: whitespace, vessző, pontosvessző, pipe.
    """
    urls = [u.strip() for u in re.split(r"[\s,;|]+", raw) if u.strip()]
    # alapszintű validálás
    urls = [u for u in urls if u.lower().startswith("http")]
    if not urls:
        raise RuntimeError(
            "FEED_ALZA_URL nem tartalmaz érvényes URL-t. "
            "Adj meg 1 vagy több XML feed URL-t (soronként vagy szóközzel elválasztva)."
        )
    return urls


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


def short_desc(t, maxlen=220):
    if not t:
        return None
    t = re.sub(r"<[^>]+>", " ", str(t))
    t = re.sub(r"\s+", " ", t).strip()
    return (t[: maxlen - 1] + "…") if len(t) > maxlen else t


def strip_ns(tag):
    return tag.split("}")[-1].split(":")[-1].lower()


def collect_node(n):
    """
    XML → "lapos" dict.
    - Több image mezőt listába szed.
    - Namespace-eket levágjuk.
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
    "google_product_category_name",
    "google_product_category",
    "g:product_type",
    "product_type",
    "category",
)

NEW_PRICE_KEYS = (
    "g:sale_price",
    "sale_price",
    "price_vat",
    "price_with_vat",
    "price_final",
    "price_huf",
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
    "old_price_vat",
    "g:price",  # fallback, ha csak g:price van + külön akciós mező nincs
)


def parse_items_from_xml(xml_text):
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
            if k.lower() in (
                "size",
                "meret",
                "merete",
                "variant_size",
                "size_id",
                "meret_id",
            ):
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
            # jobb kép
            if not cur.get("img") and it.get("img"):
                cur["img"] = it["img"]
            # alacsonyabb ár (jobb usernek)
            if (it.get("price") or 0) and (
                not cur.get("price") or it["price"] < cur["price"]
            ):
                cur["price"] = it["price"]
            # nagyobb kedvezmény
            if (it.get("discount") or 0) > (cur.get("discount") or 0):
                cur["discount"] = it["discount"]
            # hosszabb leírás
            if len(it.get("desc") or "") > len(cur.get("desc") or ""):
                cur["desc"] = it["desc"]
    return list(buckets.values())


def paginate_and_write(base_dir: Path, items, page_size: int, meta_extra=None):
    """
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


# ===== ML MODELL =====

def load_model():
    if not os.path.exists(MODEL_FILE):
        raise RuntimeError(
            f"Hiányzik az ML modell fájl: {MODEL_FILE}. "
            "Töltsd fel a model_alza.pkl-t a scripts mappába."
        )
    return joblib.load(MODEL_FILE)


def predict_category(model, title, desc, category_path, brand):
    text = " ".join(
        [
            str(title or ""),
            str(desc or ""),
            str(category_path or ""),
            str(brand or ""),
        ]
    ).strip()
    if not text:
        return "multi"
    try:
        pred = model.predict([text])[0]
        slug = str(pred).strip()

        # régi label kompat: ha a modell "mobiltelefon"-t ad vissza, mappelés "mobil"-ra
        if slug == "mobiltelefon":
            slug = "mobil"

        if not slug:
            return "multi"
        if slug not in FINDORA_CATS:
            # ha ismeretlen label – biztonsági fallback
            return "multi"
        return slug
    except Exception:
        return "multi"


# ===== MAIN =====

def main():
    # 1) Több feed URL feldarabolása
    feed_urls = split_feed_urls(FEED_URL_RAW)
    print(f"[INFO] Alza feed URL-ek száma: {len(feed_urls)}")

    all_items = []
    ok_count = 0

    for idx, url in enumerate(feed_urls, start=1):
        print(f"[INFO] Alza XML letöltés {idx}/{len(feed_urls)}")
        try:
            r = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/xml"},
                timeout=180,
            )
            r.raise_for_status()
        except Exception as e:
            print(f"[WARN] Alza feed letöltési hiba ({idx}): {e}")
            continue

        try:
            items = parse_items_from_xml(r.text)
            print(f"[INFO] Alza feed {idx}: {len(items)} nyers termék")
            all_items.extend(items)
            ok_count += 1
        except Exception as e:
            print(f"[WARN] Alza feed parse hiba ({idx}): {e}")

    if ok_count == 0:
        raise RuntimeError("Egyik Alza XML feed sem töltődött le/parsolódott sikeresen.")

    print(f"[INFO] Alza: összesen {len(all_items)} nyers termék a {ok_count} sikeres feedből.")

    # 2) dedup méretvariánsokra
    items_dedup = dedup_size_variants(all_items)
    print(f"[INFO] Alza: dedup után {len(items_dedup)} termék.")

    # 3) ML modell betöltése
    model = load_model()
    print("[INFO] Alza ML modell betöltve.")

    # 4) Normalizált sorok + kategóriák
    rows = []
    for it in items_dedup:
        pid = it["id"]
        title = it["title"]
        desc = it.get("desc") or ""
        url = it.get("url") or ""
        img = it.get("img") or ""
        price = it.get("price")
        discount = it.get("discount")
        category_path = it.get("category_path") or ""
        brand = it.get("brand") or ""

        findora_main = predict_category(
            model=model,
            title=title,
            desc=desc,
            category_path=category_path,
            brand=brand,
        )

        row = {
            "id": pid,
            "title": title,
            "img": img,
            "desc": desc,
            "price": price,
            "discount": discount,
            "url": url,
            "partner": "alza",
            "category_path": category_path,
            "findora_main": findora_main,
            "cat": findora_main,
        }
        rows.append(row)

    total = len(rows)
    print(f"[INFO] Alza: normalizált sorok: {total}")

    # régi JSON-ok törlése TELJES alza mappában (akkor is, ha total == 0)
    if OUT_DIR.exists():
        for old in OUT_DIR.rglob("*.json"):
            try:
                old.unlink()
            except OSError:
                pass

    if total == 0:
        print("⚠️ Alza: nincs termék – üres kategória meta-k + üres akciós meta készül.")
        # Minden kategóriára üres meta + üres page-0001
        for slug in FINDORA_CATS:
            base_dir = OUT_DIR / slug
            paginate_and_write(
                base_dir,
                [],
                PAGE_SIZE_CAT,
                meta_extra={
                    "partner": "alza",
                    "scope": f"category:{slug}",
                },
            )

        # Akciós bucket üresen
        akcio_dir = OUT_DIR / "akcio"
        paginate_and_write(
            akcio_dir,
            [],
            PAGE_SIZE_AKCIO,
            meta_extra={
                "partner": "alza",
                "scope": "akcio",
            },
        )
        return

    # 5) KATEGÓRIA FEED-EK (CSAK kategóriák, NINCS globál)
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
                "partner": "alza",
                "scope": f"category:{slug}",
                "generated_at": datetime.utcnow().isoformat() + "Z",
            },
        )

    # 6) AKCIÓS BLOKK (discount >= 10%)
    akcios_items = [
        row for row in rows if row.get("discount") is not None and row["discount"] >= 10
    ]

    akcio_dir = OUT_DIR / "akcio"
    paginate_and_write(
        akcio_dir,
        akcios_items,
        PAGE_SIZE_AKCIO,
        meta_extra={
            "partner": "alza",
            "scope": "akcio",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )

    print(
        f"✅ Alza kész: {total} termék, "
        f"{len(buckets)} kategória (mindegyiknek meta + legalább page-0001.json), "
        f"akciós blokk tételek: {len(akcios_items)} → {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
