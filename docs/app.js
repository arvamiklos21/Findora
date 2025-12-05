# scripts/build_alza.py
#
# ALZA feed(ek) → Findora JSON oldalak (GLOBAL + MEILISEARCH)
#
# - Bemenet:
#   FEED_ALZA_URL (vagy ALZA_FEED_URL) secret
#     → tartalmazhat 1 vagy több XML feed URL-t, szóközzel / sorvéggel / vesszővel elválasztva
#
# - Kategorizálás:
#   ML modell (model_alza.pkl) + category_guard.finalize_category_for_alza
#
# - Kimenet:
#   1) JSON oldalak (NINCS kategória mappa, NINCS akcio mappa):
#      docs/feeds/alza/meta.json
#      docs/feeds/alza/page-0001.json  (max 1000 termék)
#      docs/feeds/alza/page-0002.json  ...
#
#   2) Meilisearch index feltöltés:
#      - index: products_all  (vagy MEILI_INDEX_PRODUCTS env)
#      - minden dokumentum:
#          id          = "alza-<eredeti_id>"
#          title       = ...
#          description = desc
#          img         = img
#          url         = url
#          price       = price
#          old_price   = old_price
#          discount    = discount
#          partner     = "alza"
#          partner_name= "Alza"
#          category    = findora_main   (pl. "elektronika", "sport"...)
#          brand       = brand
#          category_path = category_path
#
# NINCS több:
#   docs/feeds/alza/<cat>/...
#   docs/feeds/alza/akcio/...

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

# hogy a scripts/ mappában lévő modulokat (pl. category_guard.py) is lássa,
# amikor a repo gyökeréből futtatjuk: python scripts/build_alza.py
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Guard réteg az ML modell fölé
from category_guard import finalize_category_for_alza

# Alza ML modell
MODEL_FILE = os.path.join(SCRIPT_DIR, "model_alza.pkl")

# Kimeneti mappa – GLOBÁLIS alza feed
OUT_DIR = Path("docs/feeds/alza")

# Globális feed lapméret
PAGE_SIZE_GLOBAL = 1000

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

# ===== MEILISEARCH KONFIG =====

MEILI_HOST = os.environ.get("MEILI_HOST", "http://127.0.0.1:7700")
MEILI_API_KEY = os.environ.get("MEILI_API_KEY") or os.environ.get("MEILI_MASTER_KEY")
MEILI_INDEX_PRODUCTS = os.environ.get("MEILI_INDEX_PRODUCTS", "products_all")


# ===== SEGÉDFÜGGVÉNYEK =====

def split_feed_urls(raw: str):
    """
    FEED_ALZA_URL → lista, több URL is lehet
    Elválasztók: whitespace, vessző, pontosvessző, pipe.
    """
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
                "old_price": old,
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
            # alacsonyabb ár
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
            # hosszabb raw_desc
            if len(it.get("raw_desc") or "") > len(cur.get("raw_desc") or ""):
                cur["raw_desc"] = it["raw_desc"]
            # old_price – nagyobb árat tartjuk meg (hogy a kedvezmény értelmes maradjon)
            if (it.get("old_price") or 0) > (cur.get("old_price") or 0):
                cur["old_price"] = it["old_price"]
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

        if slug == "mobiltelefon":
            slug = "mobil"

        if not slug:
            return "multi"
        if slug not in FINDORA_CATS:
            return "multi"
        return slug
    except Exception:
        return "multi"


# ===== MEILISEARCH FELTÖLTÉS =====

def chunked(iterable, size):
    buf = []
    for it in iterable:
        buf.append(it)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def push_to_meili(rows):
    """
    Alza sorok → Meilisearch (products_all index)
    """
    if not MEILI_API_KEY:
        print("[WARN] MEILISEARCH API KEY hiányzik (MEILI_API_KEY). Meili feltöltés kihagyva.")
        return

    url = f"{MEILI_HOST.rstrip('/')}/indexes/{MEILI_INDEX_PRODUCTS}/documents"

    session = requests.Session()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MEILI_API_KEY}",
    }

    count = 0
    for batch in chunked(rows, 1000):
        docs = []
        for row in batch:
            doc_id = f"alza-{row['id']}"
            doc = {
                "id": doc_id,
                "title": row["title"],
                "description": row.get("desc") or "",
                "img": row.get("img") or "",
                "url": row.get("url") or "",
                "price": row.get("price"),
                "old_price": row.get("old_price"),
                "discount": row.get("discount"),
                "partner": "alza",
                "partner_name": "Alza",
                "category": row.get("findora_main") or "multi",
                "brand": row.get("brand") or "",
                "category_path": row.get("category_path") or "",
                # extra mezők, ha később kellenek:
                "raw_desc": row.get("raw_desc") or "",
            }
            docs.append(doc)

        try:
            resp = session.post(url, headers=headers, data=json.dumps(docs))
            if resp.status_code >= 400:
                print(
                    f"[WARN] Meili batch hiba (status={resp.status_code}): {resp.text[:500]}"
                )
            else:
                # opcionálisan taskUid-et logolhatjuk
                try:
                    data = resp.json()
                    task_uid = data.get("taskUid")
                    print(f"[INFO] Meili batch OK, taskUid={task_uid}, docs={len(docs)}")
                except Exception:
                    print(f"[INFO] Meili batch OK, docs={len(docs)}")
        except Exception as e:
            print(f"[WARN] Meili batch request hiba: {e}")

        count += len(docs)

    print(f"[INFO] Meilibe küldött Alza dokumentumok: {count}")


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

    # 4) Normalizált sorok + kategóriák (ML + guard)
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
        old_price = it.get("old_price")
        raw_desc = it.get("raw_desc") or ""

        predicted = predict_category(
            model=model,
            title=title,
            desc=desc,
            category_path=category_path,
            brand=brand,
        )

        findora_main = finalize_category_for_alza(
            predicted=predicted,
            title=title,
            desc=desc,
            category_path=category_path,
        )

        row = {
            "id": pid,
            "title": title,
            "img": img,
            "desc": desc,
            "raw_desc": raw_desc,
            "price": price,
            "old_price": old_price,
            "discount": discount,
            "url": url,
            "partner": "alza",
            "category_path": category_path,
            "brand": brand,
            "findora_main": findora_main,
            "cat": findora_main,
        }
        rows.append(row)

    total = len(rows)
    print(f"[INFO] Alza: normalizált sorok: {total}")

    # 5) Régi JSON-ok törlése TELJES alza mappában (akkor is, ha total == 0)
    if OUT_DIR.exists():
        for old in OUT_DIR.rglob("*.json"):
            try:
                old.unlink()
            except OSError:
                pass

    # 6) GLOBÁLIS JSON feed (NINCS kategória mappa, NINCS akcio mappa)
    if total == 0:
        print("⚠️ Alza: nincs termék – üres global meta + üres page-0001 készül.")
        paginate_and_write(
            OUT_DIR,
            [],
            PAGE_SIZE_GLOBAL,
            meta_extra={
                "partner": "alza",
                "scope": "global",
            },
        )
        # Meili-re nincs mit feltolni
        return

    # Rendezés opcionálisan ár/név szerint (nem kötelező, de stabil)
    rows_sorted = sorted(
        rows,
        key=lambda r: (
            r.get("findora_main") or "multi",
            (r.get("price") or 10**12),
            r.get("title") or "",
        ),
    )

    paginate_and_write(
        OUT_DIR,
        rows_sorted,
        PAGE_SIZE_GLOBAL,
        meta_extra={
            "partner": "alza",
            "scope": "global",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )

    print(
        f"✅ Alza global feed kész: {total} termék, "
        f"page_size={PAGE_SIZE_GLOBAL}, "
        f"JSON → {OUT_DIR}"
    )

    # 7) Meilisearch feltöltés
    push_to_meili(rows_sorted)


if __name__ == "__main__":
    main()
