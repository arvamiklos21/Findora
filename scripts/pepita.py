# scripts/pepita.py
#
# PEPITA feed → Findora JSON oldalak (globál + kategória bontás)

import os
import sys
import re
import json
import math
import xml.etree.ElementTree as ET
import requests

from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# --- hogy a scripts/ alatti category_assign_pepita.py-t is lássa ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from category_assign_pepita import assign_category  # def assign_category(fields: dict) -> pl. "otthon"


# ===== KONFIG =====
OUT_DIR = "docs/feeds/pepita"

# Globális PEPITA feed (összes termék) – 300/lap
PAGE_SIZE_GLOBAL = 300

# Kategória nézet (pl. 20/lap a menüknél)
PAGE_SIZE_CAT = 20

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
        m["sale_price"] = ""  # Pepitánál nincs külön akciós ár mező
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
    """
    os.makedirs(base_dir, exist_ok=True)
    total = len(items)
    page_count = int(math.ceil(total / page_size)) if total else 0

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
        discount = None

        cat_path = m.get("product_type") or ""
        if cat_path:
            # "Otthon & Kert > Dekorációk > ..." → csak az első rész kell ide
            cat_root = re.split(r"\s*[>\|]\s*", cat_path)[0].strip()
        else:
            cat_root = ""

        # ===== Pepita-specifikus kategorizálás =====
        fields_for_cat = {
            "title": title,
            "description": raw_desc,
            "categorypath": cat_path,
            "category": cat_root,
            "product_type": m.get("product_type") or "",
            "brand": m.get("brand") or "",
            "categorytext": cat_path,
        }

        try:
            # KÖZVETLENÜL azt használjuk, amit a kategorizáló ad vissza (pl. "otthon", "szepseg", "sport"...)
            findora_main = assign_category(fields_for_cat)
        except Exception as e:
            print(f"[WARN] assign_category (Pepita) hiba (id={pid}): {e}")
            findora_main = "multi"

        if findora_main not in FINDORA_CATS:
            findora_main = "multi"

        row = {
            "id": pid,
            "title": title,
            "img": img,
            "desc": short_desc(raw_desc),
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
        print("[WARN] Nincs egyetlen normalizált PEPITA sor sem – nem lesznek JSON oldalak.")
        return

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
        if not items:
            continue
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

    print("[INFO] Kész: PEPITA feed JSON oldalak legenerálva (globál + kategória-bontás).")


if __name__ == "__main__":
    main()
