# scripts/build_alza.py
#
# ALZA feed → Findora JSON oldalak

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


# ====== KONFIG ======
OUT_DIR = "docs/feeds/alza"
PAGE_SIZE = 300  # kb. ennyi termék / JSON oldal


# ====== Segéd: ár normalizálása ======
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


# ====== Rövid leírás ======
def short_desc(t, maxlen=220):
    if not t:
        return None
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= maxlen:
        return t
    return t[: maxlen - 1].rstrip() + "…"


# ===== Feed URL-ek beolvasása (több XML támogatása) =====
def load_feed_urls():
    raw = os.environ.get("FEED_ALZA_URLS", "").strip()
    if not raw:
        raw = os.environ.get("FEED_ALZA_URL", "").strip()

    if not raw:
        raise RuntimeError("Hiányzik a FEED_ALZA_URLS vagy FEED_ALZA_URL beállítás!")

    urls = []
    for line in raw.replace(",", "\n").splitlines():
        u = line.strip()
        if u:
            urls.append(u)
    if not urls:
        raise RuntimeError("Nem találtam egyetlen ALZA feed URL-t sem!")
    return urls


# ===== XML letöltése =====
def fetch_xml(url: str) -> str:
    print(f"[INFO] Letöltés: {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.text


# ===== XML → item lista =====
def parse_alza_xml(xml_text: str):
    items = []
    root = ET.fromstring(xml_text)

    for item in root.findall(".//item"):
        m = {}

        def gettext(tag_names):
            for tn in tag_names:
                el = item.find(tn)
                if el is not None and el.text:
                    return el.text.strip()
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


# ===== Deeplink normalizálás =====
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


# ===== Fő build =====
def main():
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
        discount = None

        cat_path = m.get("product_type") or ""
        cat_root = cat_path.split("|", 1)[0].strip() if cat_path else ""

        fields_for_cat = {
            "title": title or "",
            "description": raw_desc or "",
            "category": cat_path or "",
            "product_type": cat_path or "",
            "categorytext": cat_path or "",
            "brand": m.get("brand") or "",
        }
        findora_main = assign_category(fields_for_cat) or "kat-multi"

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

    print(f"[INFO] Normalizált sorok: {len(rows)}")

    total = len(rows)
    page_count = int(math.ceil(total / PAGE_SIZE)) if total else 0

    meta = {
        "partner": "alza",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_items": total,
        "page_size": PAGE_SIZE,
        "page_count": page_count,
    }

    meta_path = os.path.join(OUT_DIR, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[INFO] meta.json kiírva: {meta_path}")

    for i in range(page_count):
        start = i * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = rows[start:end]
        page_no = i + 1
        page_name = f"page-{page_no:04d}.json"
        out_path = os.path.join(OUT_DIR, page_name)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"items": page_items}, f, ensure_ascii=False)
        print(f"[INFO] {out_path} ({len(page_items)} db)")

    print("[INFO] Kész: ALZA feed JSON oldalak legenerálva.")


if __name__ == "__main__":
    main()
