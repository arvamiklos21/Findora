# scripts/build_alza.py
#
# ALZA feed(ek) → Findora JSON oldalak (GLOBAL ONLY)
#
# - Bemenet:
#   FEED_ALZA_URL (vagy ALZA_FEED_URL) secret
#     → 1 vagy több XML feed URL, whitespace / vessző / pontosvessző / | elválasztással
#
# - Kategorizálás:
#   CSAK ML modell (model_alza.pkl)  ✅  (category_guard finalize KIKAPCSOLVA)
#
# - Kimenet (CSAK globál, 1000/db oldal):
#   docs/feeds/alza/meta.json
#   docs/feeds/alza/page-0001.json, page-0002.json, ...
#
# - Futás elején:
#   docs/feeds/alza TELJES takarítás (régi json + régi mappák is)

import os
import re
import sys
import json
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import requests
import joblib

# ===== ALAP KONFIG =====

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

MODEL_FILE = os.path.join(SCRIPT_DIR, "model_alza.pkl")
OUT_DIR = Path("docs/feeds/alza")
PAGE_SIZE_GLOBAL = 1000

FEED_URL_RAW = os.environ.get("FEED_ALZA_URL") or os.environ.get("ALZA_FEED_URL")
if not FEED_URL_RAW:
    raise RuntimeError(
        "Hiányzó FEED_ALZA_URL (vagy ALZA_FEED_URL) secret. "
        "Állítsd be a GitHub Actions Secrets között."
    )

FINDORA_CATS = [
    "elektronika", "haztartasi_gepek", "szamitastechnika", "mobil", "gaming", "smart_home",
    "otthon", "lakberendezes", "konyha_fozes", "kert", "jatekok", "divat", "szepseg",
    "drogeria", "baba", "sport", "egeszseg", "latas", "allatok", "konyv", "utazas",
    "iroda_iskola", "szerszam_barkacs", "auto_motor", "multi",
]

# ===== SEGÉDFÜGGVÉNYEK =====

def wipe_out_dir(path: Path):
    # TELJES törlés: json + régi kategória/akció mappák is
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)

def split_feed_urls(raw: str):
    urls = [u.strip() for u in re.split(r"[\s,;|]+", raw) if u.strip()]
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
        return ""
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
IMG_KEYS = ("imgurl", "image_link", "image", "image_url", "g:image_link", "image1", "main_image_url")
IMG_ALT_KEYS = ("imgurl_alternative", "additional_image_link", "additional_image_url", "images", "image2", "image3")
DESC_KEYS = ("description", "g:description", "long_description", "short_description", "desc", "popis")
BRAND_KEYS = ("brand", "g:brand", "g:manufacturer", "manufacturer")
CATEGORY_KEYS = ("google_product_category_name", "google_product_category", "g:product_type", "product_type", "category")

NEW_PRICE_KEYS = (
    "g:sale_price", "sale_price", "price_vat", "price_with_vat", "price_final", "price_huf",
    "g:price", "price", "price_amount", "current_price", "amount",
)
OLD_PRICE_KEYS = ("old_price", "price_before", "was_price", "list_price", "regular_price", "old_price_vat", "g:price")

def parse_items_from_xml(xml_text):
    root = ET.fromstring(xml_text)
    candidates = []
    for path in (".//channel/item", ".//item", ".//products/product", ".//product", ".//SHOPITEM", ".//shopitem", ".//entry"):
        nodes = root.findall(path)
        if nodes:
            candidates = nodes
            break
    if not candidates:
        candidates = [n for n in root.iter() if strip_ns(n.tag) in ("item", "product", "shopitem", "entry")]

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

        raw_desc = first(m, DESC_KEYS) or ""
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

        discount = (round((1 - price_new / old) * 100) if old and price_new and old > price_new else None)

        items.append({
            "id": pid or link or title,
            "title": title,
            "img": img or "",
            "desc": desc,
            "raw_desc": raw_desc,
            "price": price_new,
            "old_price": old,
            "discount": discount,
            "url": link or "",
            "category_path": category_path,
            "brand": brand,
        })
    return items

# ===== dedup: méret összevonás, szín marad =====

SIZE_TOKENS = r"(?:XXS|XS|S|M|L|XL|XXL|3XL|4XL|5XL|\b\d{2}\b|\b\d{2}-\d{2}\b)"
COLOR_WORDS = (
    "fekete","fehér","feher","szürke","szurke","kék","kek","piros","zöld","zold","lila",
    "sárga","sarga","narancs","barna","bézs","bezs","rózsaszín","rozsaszin","bordó","bordeaux",
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
            if k.lower() in ("size","meret","merete","variant_size","size_id","meret_id"):
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
            if len(it.get("desc") or "") > len(cur.get("desc") or ""):
                cur["desc"] = it["desc"]
            if len(it.get("raw_desc") or "") > len(cur.get("raw_desc") or ""):
                cur["raw_desc"] = it["raw_desc"]
            if (it.get("old_price") or 0) > (cur.get("old_price") or 0):
                cur["old_price"] = it["old_price"]
    return list(buckets.values())

# ===== ML MODELL =====

def load_model():
    if not os.path.exists(MODEL_FILE):
        raise RuntimeError(
            f"Hiányzik az ML modell fájl: {MODEL_FILE}. "
            "Töltsd fel a model_alza.pkl-t a scripts mappába."
        )
    return joblib.load(MODEL_FILE)

def predict_category(model, title, desc, category_path, brand):
    text = " ".join([str(title or ""), str(desc or ""), str(category_path or ""), str(brand or "")]).strip()
    if not text:
        return "multi"
    try:
        pred = model.predict([text])[0]
        slug = str(pred).strip()
        if slug == "mobiltelefon":
            slug = "mobil"
        if slug in FINDORA_CATS:
            return slug
        return "multi"
    except Exception:
        return "multi"

# ===== JSON KIÍRÁS (GLOBAL) =====

def paginate_and_write_global(out_dir: Path, items, page_size: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(items)
    page_count = 1 if total == 0 else int(math.ceil(total / page_size))

    meta = {
        "partner": "alza",
        "scope": "global",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_items": total,
        "page_size": page_size,
        "page_count": page_count,
    }
    with (out_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    if total == 0:
        with (out_dir / "page-0001.json").open("w", encoding="utf-8") as f:
            json.dump({"items": []}, f, ensure_ascii=False)
        return

    items_sorted = sorted(
        items,
        key=lambda r: (
            r.get("findora_main") or "multi",
            (r.get("price") or 10**12),
            r.get("title") or "",
        ),
    )

    for page_no in range(1, page_count + 1):
        start = (page_no - 1) * page_size
        end = start + page_size
        page_items = items_sorted[start:end]
        with (out_dir / f"page-{page_no:04d}.json").open("w", encoding="utf-8") as f:
            json.dump({"items": page_items}, f, ensure_ascii=False)

# ===== MAIN =====

def main():
    feed_urls = split_feed_urls(FEED_URL_RAW)
    print(f"[INFO] Alza feed URL-ek száma: {len(feed_urls)}")

    # 0) TELJES takarítás az elején
    wipe_out_dir(OUT_DIR)

    all_items = []
    ok_count = 0

    for idx, url in enumerate(feed_urls, start=1):
        print(f"[INFO] Alza XML letöltés {idx}/{len(feed_urls)}: {url}")
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

    items_dedup = dedup_size_variants(all_items)
    print(f"[INFO] Alza: dedup után {len(items_dedup)} termék.")

    model = load_model()
    print("[INFO] Alza ML modell betöltve.")

    rows = []
    for it in items_dedup:
        title = it.get("title") or ""
        desc = it.get("desc") or ""
        category_path = it.get("category_path") or ""
        brand = it.get("brand") or ""

        predicted = predict_category(model, title, desc, category_path, brand)

        # ✅ ML-ONLY: nincs finalize guard
        findora_main = predicted

        rows.append({
            "id": it.get("id") or "",
            "title": title,
            "img": it.get("img") or "",
            "desc": desc,
            "raw_desc": it.get("raw_desc") or "",
            "price": it.get("price"),
            "old_price": it.get("old_price"),
            "discount": it.get("discount"),
            "url": it.get("url") or "",
            "partner": "alza",
            "category_path": category_path,
            "brand": brand,
            "findora_main": findora_main,
            "cat": findora_main,
        })

    print(f"[INFO] Alza: normalizált sorok: {len(rows)}")

    paginate_and_write_global(OUT_DIR, rows, PAGE_SIZE_GLOBAL)

    print(f"✅ Alza kész: {len(rows)} termék, page_size={PAGE_SIZE_GLOBAL} → {OUT_DIR}")

if __name__ == "__main__":
    main()
