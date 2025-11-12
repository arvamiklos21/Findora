import os, json, math, gzip, csv, requests
from datetime import datetime

# --- Beállítások ---
OUT_ROOT = "docs/feeds/awin"
PAGE_SIZE = int(os.getenv("AWIN_PAGE_SIZE", "300"))

# --- Feedlist betöltése helyi CSV-ből ---
print("[AWIN] Feedlist betöltése helyi CSV-ből (scripts/datafeeds.csv)")
feedlist = []
with open("scripts/datafeeds.csv", newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Az AWIN CSV oszlopnevei: Merchant Name, Feed ID, Datafeed URL
        if row.get("Merchant Name") in ["AliExpress EU", "Alibaba EU", "Lunzo HU"]:
            feedlist.append({
                "merchant_name": row["Merchant Name"],
                "fid": row["Feed ID"],
                "datafeed_url": row["Datafeed URL"]
            })

print(f"[AWIN] {len(feedlist)} partner kiválasztva feldolgozásra.")

# --- Hasznos függvények ---
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# --- Minden partner feldolgozása ---
for feed in feedlist:
    name = feed["merchant_name"]
    fid = feed["fid"]
    url = feed["datafeed_url"]

    partner_id = name.lower().split()[0]  # pl. "aliexpress", "alibaba", "lunzo"
    out_dir = f"{OUT_ROOT}/{partner_id}"
    ensure_dir(out_dir)

    print(f"\n[AWIN] Letöltés: {name} ({partner_id})")
    print(f"  URL: {url}")

    # Letöltés és kicsomagolás
    r = requests.get(url)
    r.raise_for_status()
    content = gzip.decompress(r.content)

    rows = list(csv.DictReader(content.decode("utf-8").splitlines()))
    total = len(rows)
    pages = math.ceil(total / PAGE_SIZE)
    print(f"  Termékek: {total}, oldalak: {pages}")

    # Oldalak mentése
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

    print(f"  ✅ {name}: {pages} oldal mentve ide → {out_dir}")

print("\n🏁 Kész – az AWIN feedek sikeresen feldolgozva!")
