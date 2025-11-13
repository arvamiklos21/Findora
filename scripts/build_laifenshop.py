import os
import re
import math
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

FEED_URL = os.environ.get("FEED_LAIFENSHOP_URL")
OUT_DIR = Path("docs/feeds/laifenshop")
PAGE_SIZE = 300  # bőven elég, most csak ~pár tucat termék van


def force_https(u: str) -> str:
    """http -> https, // -> https://  (mixed content ellen)"""
    if not u:
        return ""
    u = u.strip()
    if u.startswith("//"):
        u = "https:" + u
    if u.startswith("http://"):
        u = "https://" + u[len("http://") :]
    return u


def clean_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def parse_price(raw: str):
    """
    Google feed stílusú ár: pl.
      '34999 HUF' vagy 'HUF 34999' vagy '34999'
    Visszatérés: (value: float | None, currency: str | None)
    """
    if not raw:
        return None, None
    s = raw.strip()
    # egyszerű: keressünk benne egy számot (pontot/veszőt engedve)
    m = re.search(r"(\d[\d\s.,]*)", s)
    if not m:
        return None, None
    num_txt = m.group(1).replace(" ", "").replace(",", ".")
    try:
        val = float(num_txt)
    except ValueError:
        return None, None

    # pénznem – ha benne van HUF/EUR stb.
    cur = None
    for code in ["HUF", "Ft", "EUR", "€", "USD", "$"]:
        if code in s:
            cur = "HUF" if code in ("HUF", "Ft") else (
                "EUR" if code in ("EUR", "€") else (
                    "USD" if code in ("USD", "$") else None
                )
            )
            break

    return val, cur


def get_child_text_any(item, names):
    """
    item alatti bármelyik child közül visszaadja az elsőt,
    amelynek localname-je szerepel a names listában.
    (kezeli a névtereket, pl. {http://base.google.com/ns/1.0}title)
    """
    for child in item:
        tag = child.tag
        # localname: ha van namespace, vágjuk le
        if "}" in tag:
            local = tag.split("}", 1)[1]
        else:
            local = tag
        if local in names:
            return (child.text or "").strip()
    return ""


def parse_items_from_xml(xml_text: str):
    root = ET.fromstring(xml_text)

    # próbáljuk meg úgy, mintha RSS lenne: <rss><channel><item>...
    items = root.findall(".//item")
    if not items:
        # ha nem talál, lehet, hogy <products><product> a struktúra
        items = root.findall(".//product")

    parsed = []
    for it in items:
        # localname-ek alapján szedjük ki
        pid = get_child_text_any(it, ["g:id", "id"])
        if not pid:
            pid = get_child_text_any(it, ["id"])  # fallback

        title = get_child_text_any(it, ["g:title", "title"])
        desc = get_child_text_any(it, ["g:description", "description"])

        link = get_child_text_any(it, ["g:link", "link"])
        img = get_child_text_any(it, ["g:image_link", "image_link"])

        price_raw = get_child_text_any(it, ["g:price", "price"])
        sale_raw = get_child_text_any(it, ["g:sale_price", "sale_price"])

        price_val, cur1 = parse_price(sale_raw or price_raw)
        orig_val, cur2 = parse_price(price_raw)

        currency = cur1 or cur2 or "HUF"

        discount = None
        if orig_val and price_val and orig_val > price_val:
            discount = int(round((orig_val - price_val) / orig_val * 100))

        parsed.append(
            {
                "id": pid or None,
                "title": clean_text(title) or None,
                "img": force_https(img),
                "desc": clean_text(desc),
                "price": price_val,
                "original_price": orig_val if orig_val and orig_val != price_val else None,
                "currency": currency,
                "discount": discount,
                "url": force_https(link),
            }
        )

    return parsed


def main():
    if not FEED_URL:
        raise SystemExit("FEED_LAIFENSHOP_URL nincs beállítva (env).")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Letöltés: {FEED_URL}")
    resp = requests.get(FEED_URL, timeout=60)
    resp.raise_for_status()

    items = parse_items_from_xml(resp.text)
    # szűrés: kell, hogy legyen title ÉS url, különben nem tudunk gombot/képet linkelni
    cleaned = [it for it in items if it.get("title") and it.get("url")]

    total = len(cleaned)
    pages = max(1, math.ceil(total / PAGE_SIZE))

    meta = {
        "ok": True,
        "partner": "laifenshop",
        "total": total,
        "pages": pages,
        "pageSize": PAGE_SIZE,
    }

    (OUT_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    for p in range(1, pages + 1):
        start = (p - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        chunk = cleaned[start:end]
        page_obj = {
            "ok": True,
            "partner": "laifenshop",
            "page": p,
            "total": total,
            "items": chunk,
        }
        out_path = OUT_DIR / f"page-{p:04d}.json"
        out_path.write_text(json.dumps(page_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Írva: {out_path} ({len(chunk)} termék)")

    print(f"✅ Laifenshop kész: {total} termék, {pages} oldal.")


if __name__ == "__main__":
    main()
