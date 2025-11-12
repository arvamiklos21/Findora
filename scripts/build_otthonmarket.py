import os, re, json, math, xml.etree.ElementTree as ET, requests
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

FEED_URL  = os.environ.get("FEED_OTTHONMARKET_URL")
OUT_DIR   = "docs/feeds/otthonmarket"
PAGE_SIZE = 300  # forrás-oldal méret


# -------------------- ár normalizálás --------------------
def norm_price(v):
    if v is None: return None
    s = re.sub(r"[^\d.,-]", "", str(v)).replace(" ", "")
    if not s or s in ("-", ""): return None
    try:
        return int(round(float(s.replace(",", "."))))
    except:
        digits = re.sub(r"[^\d]", "", str(v))
        return int(digits) if digits else None


# -------------------- rövid leírás --------------------
def short_desc(t, maxlen=180):
    if not t: return None
    t = re.sub(r"<[^>]+>", " ", str(t))
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:maxlen-1] + "…") if len(t) > maxlen else t


# -------------------- XML namespace kezelése --------------------
def strip_ns(tag):
    return tag.split("}")[-1].split(":")[-1].lower()


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


def first(d, keys):
    for raw in keys:
        k = raw.lower()
        v = d.get(k)
        if isinstance(v, list) and v: return v[0]
        if isinstance(v, str) and v.strip(): return v.strip()
        if v not in (None, "", []): return v
    return None


TITLE_KEYS = ("productname","title","g:title","name","product_name")
LINK_KEYS  = ("url","link","g:link","product_url","product_link","deeplink")
IMG_KEYS   = ("imgurl","image_link","image","image_url","g:image_link","image1","main_image_url")
IMG_ALT_KEYS = ("imgurl_alternative","additional_image_link","additional_image_url","images","image2","image3")
DESC_KEYS  = ("description","g:description","long_description","short_description","desc","popis")

NEW_PRICE_KEYS = (
    "price_vat","price_with_vat","price_final","price_huf",
    "g:sale_price","sale_price","g:price","price","price_amount","current_price","amount"
)
OLD_PRICE_KEYS = (
    "old_price","price_before","was_price","list_price","regular_price","g:price","price"
)


def parse_items(xml_text):
    root = ET.fromstring(xml_text)
    candidates = []
    for path in (".//channel/item",".//item",".//products/product",".//product",".//SHOPITEM",".//shopitem",".//entry"):
        nodes = root.findall(path)
        if nodes:
            candidates = nodes
            break
    if not candidates:
        candidates = [n for n in root.iter() if strip_ns(n.tag) in ("item","product","shopitem","entry")]

    items = []
    for n in candidates:
        m = col
