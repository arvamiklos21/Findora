# scripts/build_cj_eoptika.py
#
# CJ eOptika feed → Findora paginált JSON (CSAK GLOBÁL, 1000/db oldal)
#
# BEMENET:
#   - CJ ZIP HTTP-ről:
#       CJ_FEED_URL    – DataTransfer ZIP URL (amiben benne van az eOptika XML is)
#       CJ_HTTP_USER   – HTTP felhasználó
#       CJ_HTTP_PASS   – HTTP jelszó
#
# Kategorizálás:
#   - NEM használunk category_assign-t
#   - MINDEN eOptika termék fixen: "latas"
#
# KIMENET:
#   docs/feeds/cj-eoptika/meta.json
#   docs/feeds/cj-eoptika/page-0001.json, page-0002.json, ...
#
# Futás (GitHub Actions):
#   CJ_FEED_URL, CJ_HTTP_USER, CJ_HTTP_PASS secretsből/envből

import os
import re
import io
import json
import math
import zipfile
from pathlib import Path
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import requests

# ===== KONFIG =====
OUT_DIR = Path("docs/feeds/cj-eoptika")
PAGE_SIZE = 1000

CJ_FEED_URL = os.environ.get("CJ_FEED_URL")
CJ_HTTP_USER = os.environ.get("CJ_HTTP_USER")
CJ_HTTP_PASS = os.environ.get("CJ_HTTP_PASS")

PARTNER_ID = "cj-eoptika"
FIXED_CATEGORY = "latas"


# ====================== SEGÉDFÜGGVÉNYEK ======================

def rm_tree_contents(path: Path):
    """Törli a célmappában lévő összes fájlt és almappát (a mappát meghagyja)."""
    if not path.exists():
        return
    for p in sorted(path.rglob("*"), reverse=True):
        try:
            if p.is_file() or p.is_symlink():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
        except OSError:
            # GitHub runneren néha előfordulhat lock/perm anomália; hagyjuk, de próbáljuk folytatni
            pass


def short_desc(text: str, maxlen: int = 280) -> str:
    """HTML/whitespace takarítás + rövidítés."""
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", str(text))
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= maxlen:
        return t
    cut = t[: maxlen + 10]
    m = re.search(r"\s+\S*$", cut)
    if m:
        cut = cut[: m.start()].rstrip()
    return cut + "…"


def parse_price(raw_value, row_currency=None):
    """
    Kezeli:
      - "1234.56 HUF"
      - "1234,56 HUF"
      - "1234.56" + külön currency mező
    Vissza: (float_or_none, currency_str)
    """
    if not raw_value:
        return None, (row_currency or "HUF")

    raw_value = str(raw_value).strip()
    parts = raw_value.split()

    if len(parts) >= 2:
        amount = parts[0].replace(",", ".")
        currency = parts[1].strip()
    else:
        amount = raw_value.replace(",", ".")
        currency = (row_currency or "HUF")

    try:
        return float(amount), currency
    except Exception:
        return None, currency


def price_to_huf_int(value_float, currency: str):
    """
    Findora jelenlegi logikája HUF-ra optimalizált.
    Ha nem HUF, akkor is megpróbáljuk int-re tenni (de a legjobb, ha a feed HUF).
    """
    if value_float is None:
        return None
    try:
        return int(round(float(value_float)))
    except Exception:
        return None


def compute_discount(price_huf: int | None, old_price_huf: int | None):
    if old_price_huf and price_huf and old_price_huf > price_huf:
        try:
            return int(round((1 - price_huf / float(old_price_huf)) * 100))
        except Exception:
            return None
    return None


def paginate_and_write(out_dir: Path, items: list, page_size: int):
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(items)
    page_count = 1 if total == 0 else int(math.ceil(total / float(page_size)))

    # stabil sorrend: title + id (hogy ne ugráljon diffben)
    items_sorted = sorted(items, key=lambda x: (str(x.get("title", "")), str(x.get("id", ""))))

    # oldalak
    if total == 0:
        with (out_dir / "page-0001.json").open("w", encoding="utf-8") as f:
            json.dump({"items": []}, f, ensure_ascii=False)
        print(f"[INFO] {PARTNER_ID}: page-0001.json (0 db, üres)")
    else:
        for i in range(page_count):
            start = i * page_size
            end = start + page_size
            chunk = items_sorted[start:end]
            fn = out_dir / f"page-{i+1:04d}.json"
            with fn.open("w", encoding="utf-8") as f:
                json.dump({"items": chunk}, f, ensure_ascii=False)
            print(f"[INFO] {PARTNER_ID}: {fn.name} → {len(chunk)} db")

    # meta
    meta = {
        "partner": PARTNER_ID,
        "source": "cj-zip",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_items": total,
        "page_size": page_size,
        "page_count": page_count,
    }
    with (out_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[INFO] {PARTNER_ID}: meta.json kész")


def fetch_cj_zip(url: str, user: str = None, password: str = None) -> bytes:
    if not url:
        raise RuntimeError("CJ_FEED_URL nincs beállítva")

    auth = (user, password) if (user and password) else None
    print(f"[INFO] CJ ZIP letöltése: {url}")
    resp = requests.get(url, auth=auth, timeout=180)
    resp.raise_for_status()
    print("[INFO] CJ ZIP méret:", len(resp.content), "byte")
    return resp.content


def parse_eoptika_from_zip(zip_bytes: bytes):
    """
    ZIP → eOptika XML(ek) → nyers lista.
    Csak fájlok: név tartalmazza "eOptikaHU_google_all" és .xml.
    """
    items = []

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        target_files = [
            n for n in names
            if "eOptikaHU_google_all" in n and n.lower().endswith(".xml")
        ]

        if not target_files:
            print("[WARN] Nincs eOptika XML a ZIP-ben (nem találtam 'eOptikaHU_google_all' nevű fájlt).")
            return items

        for name in target_files:
            print("[INFO] eOptika XML feldolgozása:", name)
            with zf.open(name) as f:
                tree = ET.parse(f)
                root = tree.getroot()

                # A CJ feed szerkezete: <feed><entry>...</entry></feed>
                for entry in root.findall(".//entry"):
                    def get_text(tag_name: str) -> str:
                        el = entry.find(tag_name)
                        return (el.text or "").strip() if el is not None and el.text else ""

                    pid = get_text("id") or ""
                    title = get_text("title") or ""
                    description = get_text("description") or ""
                    url = get_text("link") or ""
                    image = get_text("image_link") or ""

                    if not title or not url:
                        continue

                    row_currency = get_text("currency") or "HUF"
                    raw_sale = get_text("sale_price")
                    raw_price = get_text("price")

                    sale_val, c1 = parse_price(raw_sale, row_currency)
                    price_val, c2 = parse_price(raw_price, row_currency)

                    currency = c1 or c2 or row_currency or "HUF"
                    final_val = sale_val if sale_val is not None else price_val
                    orig_val = price_val if (sale_val is not None and price_val is not None and sale_val < price_val) else None

                    price_huf = price_to_huf_int(final_val, currency)
                    old_price_huf = price_to_huf_int(orig_val, currency)

                    discount = compute_discount(price_huf, old_price_huf)

                    brand = get_text("brand") or ""
                    category_path = (
                        get_text("google_product_category_name")
                        or get_text("google_product_category")
                        or get_text("product_type")
                        or ""
                    )

                    items.append(
                        {
                            "id": pid.strip() or url,  # fallback, de legyen stabil
                            "title": title.strip(),
                            "img": image.strip(),
                            "desc": short_desc(description),
                            "price": price_huf,
                            "old_price": old_price_huf,
                            "discount": discount,
                            "url": url.strip(),
                            "partner": PARTNER_ID,
                            "brand": brand.strip(),
                            "category_path": category_path.strip(),
                            "findora_main": FIXED_CATEGORY,
                            "cat": FIXED_CATEGORY,
                        }
                    )

    return items


# ====================== MAIN ======================

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Takarítás: mindent töröl a partner mappájában (régi kategória/akció struktúrákat is)
    rm_tree_contents(OUT_DIR)

    # 2) Feed beolvasás
    if not CJ_FEED_URL:
        print("[WARN] CJ_FEED_URL nincs beállítva – üres feedet generálok.")
        paginate_and_write(OUT_DIR, [], PAGE_SIZE)
        return

    try:
        zip_bytes = fetch_cj_zip(CJ_FEED_URL, CJ_HTTP_USER, CJ_HTTP_PASS)
        rows = parse_eoptika_from_zip(zip_bytes)
    except Exception as e:
        print(f"[WARN] Hiba a CJ ZIP feldolgozásakor: {e}")
        rows = []

    # 3) Dedupe (id + url)
    seen = set()
    ded = []
    for it in rows:
        key = (str(it.get("id", "")).strip(), str(it.get("url", "")).strip())
        if key in seen:
            continue
        seen.add(key)
        ded.append(it)

    print(f"[INFO] {PARTNER_ID}: nyers={len(rows)} dedup={len(ded)}")

    # 4) Kiírás globál 1000/page
    paginate_and_write(OUT_DIR, ded, PAGE_SIZE)
    print(f"✅ KÉSZ: {PARTNER_ID} → {OUT_DIR} ({len(ded)} termék)")


if __name__ == "__main__":
    main()
