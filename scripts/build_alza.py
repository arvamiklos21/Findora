# scripts/build_alza.py
#
# ALZA feed → Findora JSON oldalak (csak kategória bontás, ML modellel)

import os
import sys
import re
import json
import math
import xml.etree.ElementTree as ET
import requests

from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import joblib  # <-- ML modell betöltéséhez

# --- hogy a scripts/ alatti dolgokat (ha kellenek) lássa ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ===== KONFIG =====
OUT_DIR = "docs/feeds/alza"

# Kategória nézet (pl. 20/lap a menüknél)
PAGE_SIZE_CAT = 20

# ML modell fájl – a scripts mappában
MODEL_FILE = os.path.join(SCRIPT_DIR, "model_alza.pkl")


# Findora fő kategória SLUG-ok – a 25 menüdhöz igazítva
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

# Modell címkék (szép nevek) → Findora slug
LABEL_TO_SLUG = {
    "Elektronika": "elektronika",
    "Háztartási gépek": "haztartasi_gepek",
    "Számítástechnika": "szamitastechnika",
    "Mobil & kiegészítők": "mobil",
    "Gaming": "gaming",
    "Smart Home": "smart_home",
    "Otthon": "otthon",
    "Lakberendezés": "lakberendezes",
    "Konyha & főzés": "konyha_fozes",
    "Kert": "kert",
    "Játékok": "jatekok",
    "Divat": "divat",
    "Szépség": "szepseg",
    "Drogéria": "drogeria",
    "Baba": "baba",
    "Sport": "sport",
    "Egészség": "egeszseg",
    "Látás": "latas",
    "Állatok": "allatok",
    "Könyv": "konyv",
    "Utazás": "utazas",
    "Iroda & iskola": "iroda_iskola",
    "Szerszám & barkács": "szerszam_barkacs",
    "Autó/Motor & autóápolás": "auto_motor",
    "Multi": "multi",
}


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


def build_text_for_model(cat_root, cat_path, title, desc):
    """
    Modell bemeneti szöveg: root + teljes kategóriaút + cím + leírás
    (ezt használtuk a D:\scan-es tréningnél is logikailag)
    """
    parts = []
    if cat_root:
        parts.append(str(cat_root))
    if cat_path:
        parts.append(str(cat_path))
    if title:
        parts.append(str(title))
    if desc:
        parts.append(str(desc))
    return " | ".join(parts)


def classify_with_model(model, cat_root, cat_path, title, desc):
    """
    ML modell meghívása, majd label → slug konverzió.
    Ha bármi gáz van, 'multi' a fallback.
    """
    text = build_text_for_model(cat_root, cat_path, title, desc)
    if not text.strip():
        return "multi"

    try:
        label = model.predict([text])[0]  # pl. "Sport", "Elektronika"
    except Exception as e:
        print(f"[WARN] model.predict hiba: {e}")
        return "multi"

    slug = LABEL_TO_SLUG.get(label, "multi")
    if slug not in FINDORA_CATS:
        slug = "multi"
    return slug


def load_feed_urls():
    """
    Több URL támogatása:
      - FEED_ALZA_URL  : lehet 1 URL, vagy több sorba tördelve, vagy vesszővel elválasztva
      - FEED_ALZA_URLS : ugyanaz, fallbackként

    A kettő közül bármelyik használható.
    """
    raw = os.environ.get("FEED_ALZA_URL", "").strip()
    if not raw:
        raw = os.environ.get("FEED_ALZA_URLS", "").strip()

    if not raw:
        raise RuntimeError("Hiányzik a FEED_ALZA_URL vagy FEED_ALZA_URLS beállítás!")

    urls = []
    for line in raw.replace(",", "\n").splitlines():
        u = line.strip()
        if u:
            urls.append(u)

    if not urls:
        raise RuntimeError("Nem találtam egyetlen ALZA feed URL-t sem!")

    return urls


def fetch_xml(url: str) -> str:
    print(f"[INFO] Letöltés: {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.text


def parse_alza_xml(xml_text: str):
    items = []
    root = ET.fromstring(xml_text)

    for item in root.findall(".//item"):
        m = {}

        def gettext(tag_names):
            for tn in tag_names:
                # prefixelt tag (g:id stb.)
                el = item.find(tn)
                if el is not None and el.text:
                    return el.text.strip()
                # namespace-független fallback (id, price stb.)
                bare = tn.split(":")[-1]
                el = item.find(f".//{{*}}{bare}")
                if el is not None and el.text:
                    return el.text.strip()
            return ""

        m["id"] = gettext(["g:id", "id"])
        m["title"] = gettext(["g:title", "title"])
        m["description"] = gettext(["g:description", "description"])
        m["link"] = gettext(["g:link", "link"])
        m["image_link"] = gettext(["g:image_link", "image_link", "g:image", "image"])
        m["price"] = gettext(["g:price", "price"])
        m["sale_price"] = gettext(["g:sale_price", "sale_price"])
        m["product_type"] = gettext(["g:product_type", "product_type", "category_path"])
        m["brand"] = gettext(["g:brand", "brand", "g:manufacturer", "manufacturer"])

        items.append(m)

    print(f"[INFO] XML-ből termékek száma: {len(items)}")
    return items


def normalize_alza_url(raw_url: str) -> str:
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
    Általános lapozó + fájlkiíró:
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
    # 0) Modell betöltése
    print(f"[INFO] Modell betöltése: {MODEL_FILE}")
    model = joblib.load(MODEL_FILE)

    # 1) XML feedek letöltése (több URL is lehet)
    urls = load_feed_urls()

    all_items = []
    for url in urls:
        xml_text = fetch_xml(url)
        items = parse_alza_xml(xml_text)
        all_items.extend(items)

    print(f"[INFO] Összesített ALZA termék szám: {len(all_items)}")

    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    for m in all_items:
        pid = m.get("id") or ""
        title = m.get("title") or ""
        raw_desc = m.get("description") or ""
        url = normalize_alza_url(m.get("link") or "")
        img = m.get("image_link") or ""

        price_raw = m.get("sale_price") or m.get("price")
        price = norm_price(price_raw)
        discount = None  # ide rakhatsz később %-os kedvezményt

        cat_path = m.get("product_type") or ""
        cat_root = cat_path.split("|", 1)[0].strip() if cat_path else ""

        # ===== ÚJ: ML alapú kategorizálás =====
        findora_main = classify_with_model(
            model,
            cat_root,
            cat_path,
            title,
            raw_desc or "",
        )

        row = {
            "id": pid,
            "title": title,
            "img": img,
            "desc": short_desc(raw_desc),
            "price": price,
            "discount": discount,
            "url": url,
            "partner": "alza",
            "category_path": cat_path,
            "category_root": cat_root,
            "findora_main": findora_main,
            "cat": findora_main,
        }
        rows.append(row)

    print(f"[INFO] Normalizált sorok (ML kategorizálással): {len(rows)}")

    # 2) Kategória szerinti feedek:
    #    docs/feeds/alza/<findora_main>/page-0001.json (20/lap)
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
                "partner": "alza",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "scope": f"category:{slug}",
            },
        )

    print("[INFO] Kész: ALZA feed JSON oldalak legenerálva (csak kategória-bontás).")


if __name__ == "__main__":
    main()
