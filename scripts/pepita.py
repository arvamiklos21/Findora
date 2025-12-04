# scripts/pepita.py
#
# PEPITA feed → Findora JSON oldalak (globál + ML-alapú kategória bontás + akciós blokk)
#
# Akciós blokk elérési útja: docs/feeds/pepita/akcio/...

import os
import sys
import re
import json
import math
import xml.etree.ElementTree as ET
import requests
import joblib

from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# --- alap pathok ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ML modell fájl – ezt használjuk kategorizálásra
MODEL_FILE = os.path.join(SCRIPT_DIR, "model_pepita.pkl")

# ===== KONFIG =====
OUT_DIR = "docs/feeds/pepita"

# Globális PEPITA feed (összes termék) – 300/lap
PAGE_SIZE_GLOBAL = 300

# Kategória nézet (pl. 20/lap a menüknél)
PAGE_SIZE_CAT = 20

# Akciós blokk mérete (pl. főoldali blokk)
PAGE_SIZE_AKCIO_BLOCK = 20

# Findora fő kategória SLUG-ok – a 25 menüdhöz igazítva
FINDORA_CATS = [
    "akciok",
    "elektronika",
    "haztartasi_gepek",
    "otthon",
    "kert",
    "jatekok",
    "divat",
    "szepseg",
    "egeszseg",
    "baba",
    "drogeria",
    "iroda_iskola",
    "sport",
    "latas",
    "allatok",
    "konyv",
    "utazas",
    "szamitastechnika",
    "mobil",
    "gaming",
    "smart_home",
    "lakberendezes",
    "konyha_fozes",
    "szerszam_barkacs",
    "auto_motor",
    "multi",
]


# ===== Segédfüggvények =====
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
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= maxlen:
        return t
    return t[: maxlen - 1].rstrip() + "…"


def load_feed_urls():
    """
    Több URL támogatása:
      - FEED_PEPITA_URL  : lehet 1 URL, vagy több sorba tördelve, vagy vesszővel elválasztva
      - FEED_PEPITA_URLS : ugyanaz, fallbackként
    """
    raw = os.environ.get("FEED_PEPITA_URL", "").strip()
    if not raw:
        raw = os.environ.get("FEED_PEPITA_URLS", "").strip()

    if not raw:
        raise RuntimeError("Hiányzik a FEED_PEPITA_URL vagy FEED_PEPITA_URLS beállítás!")

    urls = []
    for line in raw.replace(",", "\n").splitlines():
        u = line.strip()
        if u:
            urls.append(u)

    if not urls:
        raise RuntimeError("Nem találtam egyetlen PEPITA feed URL-t sem!")

    print(f"[INFO] PEPITA feed URL-ek száma: {len(urls)}")
    for u in urls:
        print(f"[INFO]  - {u}")

    return urls


def fetch_xml(url: str) -> str:
    print(f"[INFO] Letöltés: {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.text


def parse_pepita_xml(xml_text: str):
    """
    PEPITA-specifikus XML parser.

    Struktúra:
      <products>
        <product>
          <identifier>...</identifier>
          <name>...</name>
          <description>...</description>
          <product_url>...</product_url>
          <image_url>...</image_url>
          <price>...</price>
          <category>...</category>
          <manufacturer>...</manufacturer>
          ...
        </product>
        ...
      </products>
    """
    items = []
    root = ET.fromstring(xml_text)

    # FONTOS: itt <product>, NEM <item>!
    for prod in root.findall(".//product"):
        m = {}

        def gettext(tag_names):
            for tn in tag_names:
                el = prod.find(tn)
                if el is not None and el.text:
                    return el.text.strip()
            return ""

        m["id"] = gettext(["identifier", "id", "code"])
        m["title"] = gettext(["name", "title"])
        m["description"] = gettext(["description"])
        m["link"] = gettext(["product_url", "link", "url"])
        m["image_link"] = gettext(["image_link", "image_url"])
        m["price"] = gettext(["price"])
        m["sale_price"] = ""  # Pepitánál jelenleg nincs külön akciós ár mező
        m["product_type"] = gettext(["category"])
        m["brand"] = gettext(["manufacturer"])

        items.append(m)

    print(f"[INFO] XML-ből termékek száma (Pepita): {len(items)}")
    return items


def normalize_pepita_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    try:
        u = urlparse(raw_url)
        qs = dict(parse_qsl(u.query, keep_blank_values=True))
        new_qs = urlencode(qs, doseq=True)
        return urlunparse((u.scheme, u.netloc, u.path, u.params, new_qs, u.fragment))
    except Exception:
        return raw_url


def paginate_and_write(base_dir: str, items, page_size: int, meta_extra=None):
    """
    base_dir/meta.json
    base_dir/page-0001.json, page-0002.json, ...

    FONTOS:
    - Üres lista esetén is:
        - meta.json (page_count = 1)
        - page-0001.json ({"items": []})
      így a frontend SOHA nem kap 404-et a page-0001.json-re.
    """
    os.makedirs(base_dir, exist_ok=True)
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

    meta_path = os.path.join(base_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[INFO] meta.json kiírva: {meta_path} (items={total}, pages={page_count})")

    if total == 0:
        # Üres kategória/globál/akció: 1 oldal, üres items
        out_path = os.path.join(base_dir, "page-0001.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"items": []}, f, ensure_ascii=False)
        print(f"[INFO] {out_path} (0 db, üres lista)")
    else:
        for i in range(page_count):
            start = i * page_size
            end = start + page_size
            page_items = items[start:end]
            page_no = i + 1
            page_name = f"page-{page_no:04d}.json"
            out_path = os.path.join(base_dir, page_name)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"items": page_items}, f, ensure_ascii=False)
            print(f"[INFO] {out_path} ({len(page_items)} db)")


def main():
    # 0) ML-modell betöltése
    if not os.path.exists(MODEL_FILE):
        raise FileNotFoundError(
            f"[HIBA] Nem találom a Pepita ML modellt: {MODEL_FILE}. "
            f"Győződj meg róla, hogy a model_pepita.pkl a scripts mappában van."
        )

    print(f"[INFO] Modell betöltése: {MODEL_FILE}")
    model = joblib.load(MODEL_FILE)

    # 1) XML feed(ek) letöltése
    urls = load_feed_urls()

    all_items = []
    for url in urls:
        xml_text = fetch_xml(url)
        items = parse_pepita_xml(xml_text)
        all_items.extend(items)

    print(f"[INFO] Összesített PEPITA termék szám: {len(all_items)}")

    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    for m in all_items:
        pid = m.get("id") or ""
        title = m.get("title") or ""
        raw_desc = m.get("description") or ""
        url = normalize_pepita_url(m.get("link") or "")
        img = m.get("image_link") or ""

        price_raw = m.get("sale_price") or m.get("price")
        price = norm_price(price_raw)
        discount = None  # Pepitánál most nem számítunk külön kedvezmény %-ot

        cat_path = m.get("product_type") or ""
        if cat_path:
            # "Otthon & Kert > Dekorációk > ..." → csak az első rész kell ide
            cat_root = re.split(r"\s*[>\|]\s*", cat_path)[0].strip()
        else:
            cat_root = ""

        brand = m.get("brand") or ""
        sdesc = short_desc(raw_desc) or ""

        # ===== ML-alapú kategorizálás (ugyanaz a logika, mint a train_pepita_slim-ben) =====
        text_parts = [
            title,
            cat_path,
            brand,
            sdesc,
        ]
        text_for_model = " | ".join([p for p in text_parts if p])

        try:
            pred = model.predict([text_for_model])
            findora_main = str(pred[0])
        except Exception as e:
            print(f"[WARN] ML kategorizálás hiba (id={pid}): {e}")
            findora_main = "multi"

        if findora_main not in FINDORA_CATS:
            findora_main = "multi"

        row = {
            "id": pid,
            "title": title,
            "img": img,
            "desc": sdesc,
            "price": price,
            "discount": discount,
            "url": url,
            "partner": "pepita",
            "category_path": cat_path,
            "category_root": cat_root,
            "findora_main": findora_main,
            "cat": findora_main,
        }
        rows.append(row)

    print(f"[INFO] Normalizált sorok (Pepita): {len(rows)}")

    if not rows:
        print("[WARN] Nincs egyetlen normalizált PEPITA sor sem – üres page-0001.json + meta.json készül mindenhol.")

    # 1) Globális Pepita feed: docs/feeds/pepita/page-0001.json ...
    paginate_and_write(
        OUT_DIR,
        rows,
        PAGE_SIZE_GLOBAL,
        meta_extra={
            "partner": "pepita",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "scope": "global",
        },
    )

    # 2) Kategória feedek: docs/feeds/pepita/<findora_main>/page-0001.json (20/lap)
    buckets = {slug: [] for slug in FINDORA_CATS}
    for row in rows:
        slug = row.get("findora_main") or "multi"
        if slug not in buckets:
            slug = "multi"
        buckets[slug].append(row)

    for slug, items in buckets.items():
        # Üres listánál is meta + page-0001.json
        base_dir = os.path.join(OUT_DIR, slug)
        paginate_and_write(
            base_dir,
            items,
            PAGE_SIZE_CAT,
            meta_extra={
                "partner": "pepita",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "scope": f"category:{slug}",
            },
        )

    # 3) Akciós blokk: docs/feeds/pepita/akcio/page-0001.json ...
    # Itt azokat tesszük be, amiket az ML "akciok" kategóriára sorolt.
    akcios_items = [row for row in rows if row.get("cat") == "akciok"]

    akcio_base_dir = os.path.join(OUT_DIR, "akcio")
    paginate_and_write(
        akcio_base_dir,
        akcios_items,
        PAGE_SIZE_AKCIO_BLOCK,
        meta_extra={
            "partner": "pepita",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "scope": "akcio",
        },
    )

    print("[INFO] Kész: PEPITA feed JSON oldalak legenerálva (globál + kategória-bontás + akciós blokk).")


if __name__ == "__main__":
    main()
