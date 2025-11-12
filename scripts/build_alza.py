import os, re, json, math, xml.etree.ElementTree as ET, requests, tempfile
from datetime import datetime

FEED_URL  = os.environ.get("FEED_ALZA_URL")
OUT_DIR   = "docs/feeds/alza"
PAGE_SIZE = 300  # JSON-lap méret

# --- utilok (light) ---
def norm_price(v):
    if v is None: return None
    s = re.sub(r"[^\d.,-]", "", str(v)).replace(" ", "")
    if not s or s in ("-", ""): return None
    try:
        return int(round(float(s.replace(",", "."))))
    except:
        digits = re.sub(r"[^\d]", "", str(v))
        return int(digits) if digits else None

def short_desc(t, maxlen=180):
    if not t: return None
    t = re.sub(r"<[^>]+>", " ", str(t))
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:maxlen-1] + "…") if len(t) > maxlen else t

def strip_ns(tag):
    return tag.split("}")[-1].split(":")[-1].lower()

TITLE_KEYS = ("productname","title","g:title","name","product_name")
LINK_KEYS  = ("url","link","g:link","product_url","product_link","deeplink")
IMG_KEYS   = ("imgurl","image_link","image","image_url","g:image_link","image1","main_image_url")
IMG_ALT_KEYS = ("imgurl_alternative","additional_image_link","additional_image_url","images","image2","image3")
DESC_KEYS  = ("description","g:description","long_description","short_description","desc","popis")
NEW_PRICE_KEYS = ("price_vat","price_with_vat","price_final","price_huf","g:sale_price","sale_price","g:price","price","price_amount","current_price","amount")
OLD_PRICE_KEYS = ("old_price","price_before","was_price","list_price","regular_price","g:price","price")

def first(d, keys):
    for raw in keys:
        k = raw.lower()
        v = d.get(k)
        if isinstance(v, list) and v: return v[0]
        if isinstance(v, str) and v.strip(): return v.strip()
        if v not in (None, "", []): return v
    return None

def collect_node(n):
    m = {}
    txt = (n.text or "").strip()
    k0 = strip_ns(n.tag)
    if txt: m.setdefault(k0, txt)
    for ak, av in (n.attrib or {}).items():
        m.setdefault(strip_ns(ak), av)
    for c in list(n):
        k = strip_ns(c.tag)
        v = (c.text or "").strip()
        if k in ("imgurl_alternative","additional_image_link","additional_image_url","images","image2","image3"):
            m.setdefault(k, [])
            if v: m[k].append(v)
        else:
            if v:
                m[k] = v
            else:
                sub = collect_node(c)
                for sk, sv in sub.items():
                    m.setdefault(sk, sv)
    return m

def to_item_dict(m):
    pid   = first(m, ("g:id","id","item_id","sku","product_id","itemid"))
    title = first(m, TITLE_KEYS) or "Ismeretlen termék"
    link  = first(m, LINK_KEYS)

    img = first(m, IMG_KEYS)
    if not img:
        alt = first(m, IMG_ALT_KEYS)
        if isinstance(alt, list) and alt: img = alt[0]
        elif isinstance(alt, str): img = alt

    desc  = short_desc(first(m, DESC_KEYS))

    price_new = None
    for k in NEW_PRICE_KEYS:
        price_new = norm_price(m.get(k))
        if price_new: break

    old = None
    for k in OLD_PRICE_KEYS:
        old = norm_price(m.get(k))
        if old: break

    discount = round((1 - price_new/old)*100) if old and price_new and old > price_new else None

    return {
        "id": pid or link or title,
        "title": title,
        "img": img or "",
        "desc": desc,
        "price": price_new,
        "discount": discount,
        "url": link or "",
        "partner": "Alza"
    }

def iter_items_xml(file_path):
    # Keresünk tipikus item node-okat (RSS/atom/SHOPITEM)
    wanted = {"item","product","shopitem","entry"}
    ctx = ET.iterparse(file_path, events=("end",))
    for ev, el in ctx:
        tag = strip_ns(el.tag)
        if tag in wanted:
            yield el
            el.clear()

def main():
    assert FEED_URL, "FEED_ALZA_URL hiányzik (repo Secrets)."
    os.makedirs(OUT_DIR, exist_ok=True)

    # Nagy fájl → töltsük le egy ideiglenes fájlba stream-elve.
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
        with requests.get(FEED_URL, headers={"User-Agent":"Mozilla/5.0","Accept":"application/xml"}, timeout=600, stream=True) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    tmp.write(chunk)

    page_idx = 0
    buffer = []
    total = 0

    for node in iter_items_xml(tmp_path):
        m = collect_node(node)
        m = { (k.lower() if isinstance(k,str) else k): v for k,v in m.items() }
        item = to_item_dict(m)
        buffer.append(item)
        total += 1

        if len(buffer) >= PAGE_SIZE:
            page_idx += 1
            out = {"items": buffer}
            with open(os.path.join(OUT_DIR, f"page-{str(page_idx).zfill(4)}.json"), "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False)
            buffer = []

    if buffer:
        page_idx += 1
        out = {"items": buffer}
        with open(os.path.join(OUT_DIR, f"page-{str(page_idx).zfill(4)}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)

    meta = {
        "partner":"alza",
        "pageSize":PAGE_SIZE,
        "total": total,
        "pages": page_idx,
        "lastUpdated": datetime.utcnow().isoformat()+"Z",
        "source":"feed"
    }
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    print(f"✅ {total} termék, {page_idx} oldal → {OUT_DIR}")

if __name__ == "__main__":
    main()
