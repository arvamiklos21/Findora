# scripts/build_alza.py
#
# ALZA → csak KATEGÓRIA + AKCIÓS BLOKK JSON
#
# Nem készül globális meta/page!
#

import os
import re
import json
import math
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import requests
import joblib

from category_assignbase import assign_category, FINDORA_CATS

# ===== Config =====

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FEED_URL = os.environ.get("FEED_ALZA_URL")

OUT_DIR = Path("docs/feeds/alza")

PAGE_SIZE_CAT = 20
PAGE_SIZE_AKCIO = 20

MODEL_FILE = os.path.join(SCRIPT_DIR, "model_alza.pkl")


# ===== Helpers =====

def norm_price(v):
    if not v:
        return None
    s = re.sub(r"[^\d.,-]", "", str(v))
    if not s:
        return None
    try:
        return int(float(s.replace(",", ".")))
    except:
        digits = re.sub(r"[^\d]", "", str(v))
        return int(digits) if digits else None


def short(t, maxlen=220):
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", str(t))
    t = re.sub(r"\s+", " ", t).strip()
    return (t[: maxlen - 1] + "…") if len(t) > maxlen else t


def strip_ns(tag):
    return tag.split("}")[-1].split(":")[-1].lower()


def collect(n):
    m = {}
    if n.text and n.text.strip():
        m[strip_ns(n.tag)] = n.text.strip()

    for a, v in (n.attrib or {}).items():
        m[strip_ns(a)] = v

    for c in n:
        k = strip_ns(c.tag)
        if c.text and c.text.strip():
            m[k] = c.text.strip()
        else:
            sub = collect(c)
            for sk, sv in sub.items():
                m.setdefault(sk, sv)

    return m


def first(d, keys):
    for k in keys:
        v = d.get(k.lower())
        if isinstance(v, list) and v:
            return v[0]
        if isinstance(v, str) and v.strip():
            return v.strip()
        if v not in (None, "", []):
            return v
    return None


TITLE_KEYS = ("title", "productname", "g:title")
LINK_KEYS = ("url", "link", "g:link")
IMG_KEYS = ("imgurl", "image_link", "image")
DESC_KEYS = ("description", "g:description", "long_description")
CATEGORY_KEYS = ("category", "product_type", "g:product_type")
BRAND_KEYS = ("brand",)

NEW_PRICE_KEYS = ("price_vat", "price_with_vat", "price", "g:price", "g:sale_price")
OLD_PRICE_KEYS = ("old_price", "price_old", "was_price", "regular_price")


def fetch_xml(url):
    for t in range(3):
        try:
            print(f"[INFO] Alza XML letöltés {t+1}/3")
            r = requests.get(url, headers={"User-Agent": "Mozilla"}, timeout=90)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print("[WARN]", e)
            time.sleep(4)
    raise RuntimeError("Alza XML nem tölthető le.")


def parse_items(xml_text):
    root = ET.fromstring(xml_text)

    nodes = root.findall(".//item")
    if not nodes:
        nodes = root.findall(".//product")
    if not nodes:
        nodes = [n for n in root.iter() if strip_ns(n.tag) in ("item", "product")]

    items = []
    for n in nodes:
        m = collect(n)
        m = {k.lower(): v for k, v in m.items()}

        pid = first(m, ("g:id", "id", "item_id"))
        title = first(m, TITLE_KEYS)
        url = first(m, LINK_KEYS)
        img = first(m, IMG_KEYS)
        desc = short(first(m, DESC_KEYS))
        cat_path = first(m, CATEGORY_KEYS) or ""
        brand = first(m, BRAND_KEYS) or ""

        price_new = None
        for k in NEW_PRICE_KEYS:
            price_new = norm_price(m.get(k))
            if price_new:
                break

        price_old = None
        for k in OLD_PRICE_KEYS:
            price_old = norm_price(m.get(k))
            if price_old:
                break

        discount = (
            round((1 - price_new / price_old) * 100)
            if price_old and price_new and price_old > price_new
            else None
        )

        items.append(
            {
                "id": pid or url or title,
                "title": title or "Ismeretlen termék",
                "img": img or "",
                "desc": desc,
                "price": price_new,
                "discount": discount,
                "url": url or "",
                "category_path": cat_path,
                "brand": brand,
            }
        )
    print(f"[INFO] Alza parse: {len(items)} termék")
    return items


# ========== Kategorizálás (ML + fallback) ==========

def load_model():
    if not os.path.exists(MODEL_FILE):
        print("[INFO] ML modell nincs – szabályalapú fallback.")
        return None
    try:
        model = joblib.load(MODEL_FILE)
        return model
    except:
        print("[WARN] ML modell hibás – fallback.")
        return None


def classify(model, title, desc, cat_path, brand):
    txt = " ".join([title or "", desc or "", cat_path or "", brand or ""]).strip()

    if model:
        try:
            c = model.predict([txt])[0]
            if c in FINDORA_CATS:
                return c
        except Exception as e:
            print("[WARN] ML:", e)

    return assign_category(
        title=title, desc=desc, category_path=cat_path, brand=brand,
        partner="alza", partner_default="multi"
    )


# ========== Írás ==========

def write_pages(base: Path, items, page_size, meta_extra=None):
    base.mkdir(parents=True, exist_ok=True)
    total = len(items)
    pages = math.ceil(total / page_size) if total else 0

    meta = {
        "total_items": total,
        "page_size": page_size,
        "page_count": pages,
    }
    if meta_extra:
        meta.update(meta_extra)

    with open(base/"meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    for p in range(1, pages + 1):
        s = (p - 1) * page_size
        e = s + page_size
        with open(base/f"page-{p:04d}.json", "w", encoding="utf-8") as f:
            json.dump({"items": items[s:e]}, f, ensure_ascii=False)


# ========== MAIN ==========

def main():
    if not FEED_URL:
        raise SystemExit("FEED_ALZA_URL nincs beállítva.")

    # régi JSON törlése
    if OUT_DIR.exists():
        for f in OUT_DIR.rglob("*.json"):
            f.unlink()

    # XML letöltés
    xml = fetch_xml(FEED_URL)
    raw = parse_items(xml)

    model = load_model()

    rows = []
    for it in raw:
        cat = classify(model, it["title"], it["desc"], it["category_path"], it["brand"])
        it["cat"] = cat
        it["findora_main"] = cat
        it["partner"] = "alza"
        rows.append(it)

    print(f"[INFO] Alza total normalized: {len(rows)}")

    # ====== KATEGÓRIA FEED ======
    for slug in FINDORA_CATS:
        subset = [r for r in rows if r["cat"] == slug]
        write_pages(
            OUT_DIR / slug,
            subset,
            PAGE_SIZE_CAT,
            meta_extra={"partner": "alza", "scope": f"category:{slug}"}
        )

    # ====== AKCIÓS BLOKK ======
    akcios = [r for r in rows if r.get("discount") and r["discount"] >= 10]

    write_pages(
        OUT_DIR / "akcios-block",
        akcios,
        PAGE_SIZE_AKCIO,
        meta_extra={"partner": "alza", "scope": "akcios-block"}
    )

    print("✔ ALZA kész: csak kategóriák + akciós blokk generálva.")


if __name__ == "__main__":
    main()
