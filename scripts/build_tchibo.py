import os, re, json, math, xml.etree.ElementTree as ET, requests
from datetime import datetime

FEED_URL  = os.environ.get("FEED_TCHIBO_URL")
OUT_DIR   = "docs/feeds/tchibo"
PAGE_SIZE = 300

def norm_price(v):
    if v is None: return None
    s = re.sub(r"[^\d.,-]", "", str(v)).replace(" ", "")
    if not s or s in ("-", ""): return None
    try: return int(round(float(s.replace(",", "."))))
    except: return None

def short_desc(t, maxlen=180):
    if not t: return None
    t = re.sub(r"\s+", " ", str(t).strip())
    return (t[:maxlen-1] + "…") if len(t) > maxlen else t

def strip_ns(tag):  # '{ns}price' vagy 'g:price' -> 'price'
    return tag.split("}")[-1].split(":")[-1]

def first(d, keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip(): return v.strip()
        if v not in (None, "", []): return v
    return None

def collect_node(n):
    m = {}
    txt = (n.text or "").strip()
    if txt: m[strip_ns(n.tag)] = txt
    for ak, av in n.attrib.items():
        m[strip_ns(ak)] = av
    for c in list(n):
        k = strip_ns(c.tag)
        v = (c.text or "").strip()
        if k in ("additional_image_link", "additional_image_url", "images"):
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

def parse_items(xml_text):
    root = ET.fromstring(xml_text)
    candidates = []
    for path in (".//channel/item", ".//item", ".//products/product", ".//product", ".//entry"):
        nodes = root.findall(path)
        if nodes:
            candidates = nodes
            break
    if not candidates:
        candidates = [n for n in root.iter() if strip_ns(n.tag) in ("item","product","entry")]

    items = []
    for n in candidates:
        m = collect_node(n)
        pid   = first(m, ("id","g:id","item_id","sku","product_id"))
        title = first(m, ("title","g:title","name","product_name")) or "Ismeretlen termék"
        link  = first(m, ("link","g:link","url","product_url","product_link"))
        img   = first(m, ("image_link","image","image_url","g:image_link")) \
                or (m.get("additional_image_link",[None])[0] if isinstance(m.get("additional_image_link"),list) else None)
        desc  = short_desc(first(m, ("description","g:description","long_description","short_description")))

        price_new = None
        for k in ("g:sale_price","sale_price","g:price","price","price_amount","current_price"):
            price_new = norm_price(m.get(k))
            if price_new: break

        old = None
        for k in ("g:price","price","old_price","list_price","regular_price"):
            old = norm_price(m.get(k))
            if old: break

        discount = round((1 - price_new/old) * 100) if old and price_new and old > price_new else None

        items.append({
            "id": pid or link or title,
            "title": title,
            "img": img or "",
            "desc": desc,
            "price": price_new,
            "discount": discount,
            "url": link or ""
        })
    return items

def main():
    assert FEED_URL, "FEED_TCHIBO_URL hiányzik (repo Secrets)."
    os.makedirs(OUT_DIR, exist_ok=True)
    r = requests.get(FEED_URL, headers={"User-Agent":"Mozilla/5.0","Accept":"application/xml"}, timeout=120)
    r.raise_for_status()
    items = parse_items(r.text)
    if not items:
        items = [{"id":"DEBUG-NO-ITEMS","title":"Nem találtam terméket az XML-ben","img":"","desc":"Parser finomítás kell.","price":None,"discount":None,"url":""}]

    pages = max(1, math.ceil(len(items)/PAGE_SIZE))
    for i in range(pages):
        data = {"items": items[i*PAGE_SIZE:(i+1)*PAGE_SIZE]}
        with open(os.path.join(OUT_DIR, f"page-{str(i+1).zfill(4)}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    meta = {"partner":"tchibo","pageSize":PAGE_SIZE,"total":len(items),"pages":pages,"lastUpdated":datetime.utcnow().isoformat()+"Z","source":"productsup"}
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(f"✅ {len(items)} termék, {pages} oldal → {OUT_DIR}")

if __name__ == "__main__":
    main()
