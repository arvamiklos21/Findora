import os, re, json, math, xml.etree.ElementTree as ET, requests
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

FEED_URL  = os.environ.get("FEED_OTTHONMARKET_URL")
OUT_DIR   = "docs/feeds/otthonmarket"
PAGE_SIZE = 300

# (ugyanaz a segédfüggvény-csomag, mint a build_laifenshop.py-ban – másold át 1/1)

# --- segédfüggvények és parser innen ugyanaz, mint fent ---
# ... (másold át a teljes blokkot) ...

def main():
    assert FEED_URL, "FEED_OTTHONMARKET_URL hiányzik (repo Secrets)."
    os.makedirs(OUT_DIR, exist_ok=True)
    r = requests.get(FEED_URL, headers={"User-Agent":"Mozilla/5.0","Accept":"application/xml"}, timeout=120)
    r.raise_for_status()
    items = dedup_size_variants(parse_items(r.text))
    pages = max(1, math.ceil(len(items)/PAGE_SIZE))
    for i in range(pages):
        data = {"items": items[i*PAGE_SIZE:(i+1)*PAGE_SIZE]}
        with open(os.path.join(OUT_DIR, f"page-{str(i+1).zfill(4)}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    meta = {
        "partner":"otthonmarket",
        "pageSize":PAGE_SIZE,
        "total":len(items),
        "pages":pages,
        "lastUpdated":datetime.utcnow().isoformat()+"Z",
        "source":"feed"
    }
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(f"✅ {len(items)} termék, {pages} oldal → {OUT_DIR}")

if __name__ == "__main__":
    main()
