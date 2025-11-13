import os, json, math, xml.etree.ElementTree as ET, requests
from datetime import datetime

FEED_URL  = os.environ.get("FEED_LAIFENSHOP_URL")
OUT_DIR   = "docs/feeds/laifenshop"
PAGE_SIZE = 300  # maximum termék / JSON oldal


# --------- utilok ----------

def force_https(u: str) -> str:
    """http -> https, // -> https://  (mixed content ellen)"""
    if not u:
        return ""
    u = u.strip()
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http://"):
        return "https://" + u[len("http://") :]
    return u


def clean_text(x: str) -> str:
    if not x:
        return ""
    return " ".join(str(x).split()).strip()


def to_num(v):
    """Szám konverzió – Laifennél sima egész ár jön (44999 stb.)"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "")
    if not s:
        return None
    # csak számok – ha bármi más, hagyjuk None-ra
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None


def ensure_out_dir():
    os.makedirs(OUT_DIR, exist_ok=True)


# --------- XML betöltés és normalizálás ----------

def fetch_xml(url: str) -> ET.Element:
    if not url:
        raise RuntimeError("FEED_LAIFENSHOP_URL nincs beállítva env-ben.")
    print(f"Letöltés: {url}")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    print(f"HTTP {r.status_code}, {len(r.content)} byte")
    return ET.fromstring(r.content)


def text_or_none(node: ET.Element, tag: str):
    el = node.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    return None


def parse_products(root: ET.Element):
    """
    Forrás struktúra:

    <Products>
      <Product>
        <Identifier>55479255859578</Identifier>
        <Manufacturer>Laifen</Manufacturer>
        <Name>Laifen Wave</Name>
        <ProductUrl>https://www.laifenshop.hu/products/...</ProductUrl>
        <Price>44999</Price>
        <Description>...</Description>
        ...
        <ImageUrl>...</ImageUrl>
        <ImageUrl2>...</ImageUrl2>
        ...
      </Product>
      ...
    </Products>
    """
    products = root.findall(".//Product")
    items = []

    print(f"Talált Product elemek: {len(products)}")

    for p in products:
        identifier = clean_text(text_or_none(p, "Identifier") or "") or None
        name       = clean_text(text_or_none(p, "Name") or "")
        desc       = clean_text(text_or_none(p, "Description") or "")
        url        = clean_text(text_or_none(p, "ProductUrl") or "")
        price_raw  = text_or_none(p, "Price") or text_or_none(p, "NetPrice")
        price      = to_num(price_raw)

        # Kép kiválasztása: ImageUrl, majd ImageUrl2..19
        img = ""
        img_candidates = []

        first_img = text_or_none(p, "ImageUrl")
        if first_img:
            img_candidates.append(first_img)

        for i in range(2, 20):
            ti = text_or_none(p, f"ImageUrl{i}")
            if ti:
                img_candidates.append(ti)

        if img_candidates:
            img = force_https(img_candidates[0])

        item = {
            "id": identifier or name or "",
            "title": name,
            "img": img,
            "desc": desc,
            "price": price,
            "discount": None,
            "url": url,
        }

        # Minimális szűrés: ha egyáltalán nincs neve, akkor dobjuk
        if not item["title"]:
            continue

        items.append(item)

    print(f"Normalizált termékek száma: {len(items)}")
    return items


# --------- JSON oldalak írása ----------

def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def write_pages(items):
    ensure_out_dir()
    total = len(items)
    pages = max(1, math.ceil(total / PAGE_SIZE))

    # meta.json
    meta = {
        "partner": "laifenshop",
        "pageSize": PAGE_SIZE,
        "total": total,
        "pages": pages,
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "source": "feed",
    }

    meta_path = os.path.join(OUT_DIR, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"meta.json kiírva: {meta_path}")

    # page-0001.json, page-0002.json, ...
    page_num = 1
    for chunk in chunked(items, PAGE_SIZE):
        out = {"items": chunk}
        fn = f"page-{page_num:04d}.json"
        out_path = os.path.join(OUT_DIR, fn)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
        print(f"Oldal #{page_num} → {out_path} ({len(chunk)} termék)")
        page_num += 1


def main():
    root = fetch_xml(FEED_URL)
    items = parse_products(root)
    write_pages(items)


if __name__ == "__main__":
    main()
