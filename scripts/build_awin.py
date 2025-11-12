import os, json, math, gzip, csv, requests
from io import BytesIO
from datetime import datetime

# --- Beállítások ---
OUT_ROOT = "docs/feeds/awin"
PAGE_SIZE = int(os.getenv("AWIN_PAGE_SIZE", "300"))

# --- Letöltési forrás ---
FEED_LIST_URL = os.getenv("AWIN_FEED_LIST_URL")
if not FEED_LIST_URL:
    raise SystemExit("❌ Missing AWIN_FEED_LIST_URL secret!")

# --- Partner-szűrés: CSAK ezek kellenek most ---
TARGET_PARTNERS = {
    "AliExpress EU": "aliexpress",
    "Alibaba EU": "alibaba",
    "Lunzo HU": "lunzo"
}

# --- Segédfüggvények ---
def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# --- Lekérés feedlist ---
print(f"[AWIN] Feedlist letöltése: {FEED_LIST_URL}")
resp = requests.get(FEED_LIST_URL)
resp.raise_for_status()
feedlist = resp.json()

print(f"[AWIN] {len(feedlist)} feed található összesen.")

# --- Csak a cél partnereket dolgozzuk fel ---
for feed in feedlist:
    name = feed.get("merchant_name")
    fid = feed.get("fid")
    if name not in TARGET_PARTNERS:
        continue

    partner_id = TARGET_PARTNERS[name]
    print(f"\n[AWIN] Feldolgozás: {name} → {partner_id}")

    # Letöltési URL (CSV GZIP)
    url = feed["datafeed_url"]
    print(f"  Forrás: {url}")

    # Lekérés és kicsomagolás
    r = requests.get(url)
    r.raise_for_status()
    data = gzip.decompress(r.content)

    rows = list(csv.DictReader(data.decode("utf-8").splitlines()))
    total = len(rows)
    print(f"  Termékek: {total}")

    # Oldalak száma
    pages = math.ceil(total / PAGE_SIZE)

    # Célmappa
    out_dir = f"{OUT_ROOT}/{partner_id}"
    ensure_dir(out_dir)

    # Page-ek mentése
    for i in range(pages):
        start = i * PAGE_SIZE
        end = min(start + PAGE_SIZE, total)
        page_rows = rows[start:end]
        save_json(f"{out_dir}/page-{i+1:04}.json", page_rows)

    # Meta mentése
    meta = {
        "id": partner_id,
        "name": name,
        "count": total,
        "pages": pages,
        "updated": datetime.utcnow().isoformat() + "Z"
    }
    save_json(f"{out_dir}/meta.json", meta)
    print(f"  ✅ {pages} oldal mentve ide: {out_dir}")

print("\n🏁 Kész – az összes AWIN partner sikeresen feldolgozva!")
