# scripts/build_awin.py
# AWIN master feedlist -> partnerenként letölt, normalizál, 200/300-as oldalakra darabol
# Ment: docs/feeds/awin/<slug>/page-0001.json, meta.json + globális docs/feeds/awin/meta.json

import os, re, csv, io, json, zlib, gzip, math
import requests
from datetime import datetime

# ---- BEÁLLÍTÁSOK ----
FEED_LIST_URL = os.environ.get("AWIN_FEED_LIST_URL")
OUT_DIR   = "docs/feeds/awin"
PAGE_SIZE = int(os.environ.get("AWIN_PAGE_SIZE", "300"))
TIMEOUT   = 60

# ---- HELPEREK ----
def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^\w]+", "", s)
    return s.strip("_") or "partner"

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def write_json(path: str, data):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

def chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

def try_inflate_bytes(content: bytes) -> bytes:
    try:
        return gzip.decompress(content)
    except Exception:
        pass
    try:
        return zlib.decompress(content, 16+zlib.MAX_WBITS)
    except Exception:
        pass
    return content

def parse_feed_list(text: str):
    """Feedlist JSON vagy HTML feldolgozása."""
    try:
        j = json.loads(text)
        advs = []
        for it in j.get("advertisers") or j.get("feeds") or []:
            url = it.get("url") or it.get("downloadUrl") or it.get("feedUrl")
            if not url:
                continue
            advs.append({
                "name": it.get("name"),
                "url": url,
                "id": str(it.get("id")) if it.get("id") else None
            })
        if advs:
            return advs
    except Exception:
        pass

    urls = re.findall(r"https?://productdata\.awin\.com/datafeed/download/[^\s\"'<>]+", text)
    advs = []
    for u in urls:
        m = re.search(r"/advertiser/(\d+)/", u)
        adv_id = m.group(1) if m else None
        advs.append({"name": None, "url": u, "id": adv_id})
    return advs

def normalize_row(row: dict, partner_name: str):
    """Egységesített rekord a frontendhez."""
    low = { (k or "").strip().lower(): v for k, v in row.items() }

    title    = low.get("product_name") or low.get("name") or low.get("title") or ""
    price    = low.get("search_price") or low.get("price") or low.get("final_price") or low.get("sale_price") or ""
    currency = low.get("currency") or low.get("currency_code") or ""
    url      = low.get("aw_deep_link") or low.get("product_url") or low.get("url") or ""
    image    = low.get("merchant_image_url") or low.get("image_url") or low.get("aw_image_url") or ""
    category = low.get("merchant_category") or low.get("category") or ""
    brand    = low.get("brand") or ""
    instock  = low.get("instock") or low.get("availability") or ""

    def to_num(x):
        if x is None:
            return None
        s = str(x).replace(" ", "").replace(",", ".")
        m = re.search(r"([0-9]+(\.[0-9]+)?)", s)
        return float(m.group(1)) if m else None

    return {
        "title": title[:300],
        "price": to_num(price),
        "currency": currency,
        "url": url,
        "img": image,
        "category": category,
        "brand": brand,
        "in_stock": bool(re.search(r"^(1|true|yes|in ?stock|available)$", str(instock or "").lower()))
                 if instock else None,
        "partner": partner_name,
    }

def read_csv_bytes(b: bytes):
    """CSV bytes → dict list"""
    try:
        text = b.decode("utf-8", errors="replace")
    except Exception:
        text = b.decode("latin-2", errors="replace")
    return csv.DictReader(io.StringIO(text))

def guess_partner_name_from_url(url: str, fallback_id: str|None):
    m = re.search(r"/advertiser/(\d+)/", url)
    adv_id = m.group(1) if m else (fallback_id or "adv")
    return f"adv{adv_id}"

def save_partner(partner_slug: str, items: list):
    partner_dir = os.path.join(OUT_DIR, partner_slug)
    ensure_dir(partner_dir)

    total = len(items)
    pages = max(1, math.ceil(total / PAGE_SIZE))

    for idx, chunk_items in enumerate(chunk(items, PAGE_SIZE), start=1):
        write_json(os.path.join(partner_dir, f"page-{idx:04d}.json"), chunk_items)

    write_json(os.path.join(partner_dir, "meta.json"), {
        "partner": partner_slug,
        "count": total,
        "page_size": PAGE_SIZE,
        "pages": pages,
        "updated": now_iso()
    })
    return total, pages

# ---- FŐ FUTÁS ----
def main():
    ensure_dir(OUT_DIR)
    print("[AWIN] Feedlist letöltése…")

    r = requests.get(FEED_LIST_URL, timeout=TIMEOUT)
    r.raise_for_status()
    feedlist_text = r.text
    advertisers = parse_feed_list(feedlist_text)
    if not advertisers:
        raise SystemExit("❌ Nincs partner a feedlistában – ellenőrizd az AWIN_FEED_LIST_URL secretet.")

    summary = []
    for adv in advertisers:
        url = adv["url"]
        adv_name = (adv.get("name") or "").strip() or guess_partner_name_from_url(url, adv.get("id"))
        slug = slugify(adv_name)
        print(f"[AWIN] {adv_name} – letöltés: {url}")

        try:
            rr = requests.get(url, timeout=TIMEOUT)
            rr.raise_for_status()
            content = try_inflate_bytes(rr.content)

            items = []
            for row in read_csv_bytes(content):
                norm = normalize_row(row, partner_name=adv_name)
                if not norm["title"] and not norm["url"]:
                    continue
                items.append(norm)

            total, pages = save_partner(slug, items)
            summary.append({"id": slug, "name": adv_name, "count": total, "pages": pages})
            print(f"[OK] {adv_name}: {total} termék, {pages} oldal")

        except Exception as e:
            print(f"[HIBA] {adv_name}: {e}")
            continue

    write_json(os.path.join(OUT_DIR, "meta.json"), {
        "partners": sorted(summary, key=lambda x: x["name"].lower()),
        "updated": now_iso(),
        "page_size": PAGE_SIZE
    })
    print(f"[KÉSZ] Összes partner: {len(summary)} – meta.json frissítve.")

if __name__ == "__main__":
    main()
