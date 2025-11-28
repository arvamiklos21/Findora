#!/usr/bin/env python
# build_cj_txt.py
#
# CJ datatransfer TXT -> Findora JSON oldalak
#
# Használat:
#   python scripts/build_cj_txt.py <input_txt> <partner_slug>
#
# Példa:
#   python scripts/build_cj_txt.py cj-eoptika/eOptika_HU-eOptikaHU_google_all-shopping.txt cj-eoptika
#
# Kimenet:
#   docs/feeds/<partner_slug>/meta.json
#   docs/feeds/<partner_slug>/page-0001.json, page-0002.json, ...

import os
import sys
import csv
import json
import math
from datetime import datetime

OUT_BASE = os.path.join("docs", "feeds")
PAGE_SIZE = 500  # tetszés szerint: 200 / 500 / 1000

def pick_first(dct, keys, default=""):
    """
    Első nem üres mező a megadott kulcsok listájából.
    """
    for k in keys:
        v = dct.get(k)
        if v is not None and str(v).strip() != "":
            return v
    return default

def price_to_int(price_str):
    """
    CJ feedben ár mező: "1234.56" vagy "1234,56".
    Ebből int HUF-ot csinálunk (kerekítés).
    Ha nem értelmezhető, None.
    """
    if not price_str:
        return None
    s = str(price_str).strip().replace(",", ".")
    try:
        val = float(s)
        return int(round(val))
    except ValueError:
        return None

def load_cj_txt(path, partner_slug):
    """
    CJ TXT beolvasása (tab-szeparált), DictReaderrel.
    Visszatér: Findora item listával.
    """
    items = []

    # Tipikus CJ encoding utf-8, ha nem, majd módosítunk később
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            # ID – CJ sku / merchant sku
            pid = pick_first(row, ["cj-sku", "sku", "sku-id", "sku_id", "id", "product-id"])

            # Név
            title = pick_first(row, ["name", "product-name", "product_name", "item-name"])

            # Leírás + keywords
            desc = pick_first(row, ["description", "long-description", "long_description", "product-description"])
            keywords = pick_first(row, ["keywords", "keyword"], "")
            if keywords:
                desc = (desc or "") + " " + keywords

            # Kép
            img = pick_first(row, ["image-url", "image_url", "image-link", "image-link-url"])

            # Termék URL
            url = pick_first(row, ["buy-url", "buy_url", "sku-url", "link", "url", "product-url"])

            # Ár / akciós ár
            sale_price_raw = pick_first(row, ["sale-price", "sale_price", "discount-price", "discount_price"])
            list_price_raw = pick_first(row, ["price", "list-price", "list_price"])

            price = price_to_int(sale_price_raw)
            if price is None:
                price = price_to_int(list_price_raw)

            # Kedvezmény most None – később lehet számolni
            discount = None

            # Merchant kategória
            category_path = pick_first(
                row,
                ["advertiser-category", "merchant-category", "category", "categories", "category-name"]
            )

            # Kötelezők: id, title, url
            if not pid or not title or not url:
                continue

            item = {
                "id": str(pid).strip(),
                "title": str(title).strip(),
                "img": str(img).strip() if img else None,
                "desc": str(desc).strip() if desc else "",
                "price": price,
                "discount": discount,
                "url": str(url).strip(),
                "partner": partner_slug,
                "category_path": str(category_path).strip() if category_path else None,
                # "findora_main": majd külön category_assign fogja kitölteni
            }
            items.append(item)

    return items

def write_pages(items, partner_slug):
    """
    items listából meta.json + page-0001.json, page-0002.json... generálása.
    """
    out_dir = os.path.join(OUT_BASE, partner_slug)
    os.makedirs(out_dir, exist_ok=True)

    total = len(items)
    if total == 0:
        print(f"[INFO] {partner_slug}: 0 termék – nem írok ki oldalakat.")
        # meta.json azért legyen meg, üresként is
        meta = {
            "partner": partner_slug,
            "total": 0,
            "pageSize": PAGE_SIZE,
            "pageCount": 0,
            "currency": "HUF",
            "updatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        meta_path = os.path.join(out_dir, "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return

    page_count = int(math.ceil(total / float(PAGE_SIZE)))

    meta = {
        "partner": partner_slug,
        "total": total,
        "pageSize": PAGE_SIZE,
        "pageCount": page_count,
        "currency": "HUF",  # CJ HU feed -> HUF, ha más lenne, majd finomítjuk
        "updatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    meta_path = os.path.join(out_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    for i in range(page_count):
        start = i * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = items[start:end]

        page_name = f"page-{i+1:04d}.json"
        page_path = os.path.join(out_dir, page_name)

        data = {
            "partner": partner_slug,
            "page": i + 1,
            "pageSize": PAGE_SIZE,
            "total": total,
            "items": page_items,
        }

        with open(page_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] {partner_slug}: {total} termék, {page_count} oldal -> {out_dir}")

def main():
    if len(sys.argv) != 3:
        print("Használat: python scripts/build_cj_txt.py <input_txt> <partner_slug>")
        print("Példa:   python scripts/build_cj_txt.py cj-eoptika/valami.txt cj-eoptika")
        sys.exit(1)

    input_txt = sys.argv[1]
    partner_slug = sys.argv[2]

    if not os.path.isfile(input_txt):
        print(f"HIBA: Nem találom a TXT fájlt: {input_txt}")
        sys.exit(1)

    items = load_cj_txt(input_txt, partner_slug)
    write_pages(items, partner_slug)

if __name__ == "__main__":
    main()
