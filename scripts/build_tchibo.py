import os, re, json, math, xml.etree.ElementTree as ET, requests
from datetime import datetime

# ====== beállítások ======
FEED_URL = os.environ.get("FEED_TCHIBO_URL")   # GitHub Secretből jön
OUT_DIR = "docs/feeds/tchibo"
PAGE_SIZE = 300

# ====== segédfüggvények ======
def norm_price(v):
    if not v: return None
    s = re.sub(r"[^\d.,]", "", str(v)).replace(" ", "")
    if not s: return None
    try: return int(float(s.replace(",", ".")))
    except: return None

def short_desc(t, maxlen=180):
    if not t: return None
    t = re.sub(r"\s+", " ", t.strip())
    return (t[:maxlen-1] + "…") if len(t) > maxlen else t

def strip_ns(tag): return tag.split("}")[-1].split(":")[-1]

def pick(d, *keys):
    for k in keys:
        if k in d and d[k]: return d[k]
    return None

# ====== XML feldolgozás ======
def parse_items(xml_text):
    root = ET.fromstring(xml_text)
    nodes = root.findall(".//item") or root.findall(".//product") or root.findall(".//entry")
    items = []
    for n in nodes:
        m = {}
        for c in list(n):
            key = strip_ns(c.tag)
            val = (c.text or "").strip()
            if key == "additional_image_link":
                m.setdefault(key, [])
                if val: m[key].append(val)
            else:
                m[key] = val

        link = pick(m, "link", "g:link", "url")
        price_new = None
        for k in ("g:sale_price","sale_price","g:price","price"):
            price_new = norm_price(m.get(k))
            if price_new: break

        old = norm_price(m.get("g:price") or m.get("price"))
        discount = round((1 - price_new/old)*100) if old and price_new and old>price_new else None
        img = m.get("image_link") or (m.get("additional_image_link")[0] if isinstance(m.get("additional_image_link"), list) and m.get("additional_image_link") else None) or m.get("g:image_link")
        items.append({
            "id": pick(m,"id","g:id") or link or "",
            "title": pick(m,"title","g:title") or "Ismeretlen termék",
            "img": img,
            "desc": short_desc(pick(m,"description","g:description")),
            "price": price_new,
            "discount": discount,
            "url": link
        })
    return items

# ====== fő folyamat ======
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/xml"}
    r = requests.get(FEED_URL, headers=headers, timeout=120)
    r.raise_for_status()
    items = parse_items(r.text)

    pages = max(1, math.ceil(len(items)/PAGE_SIZE))
    for i in range(pages):
        data = {"items": items[i*PAGE_SIZE:(i+1)*PAGE_SIZE]}
