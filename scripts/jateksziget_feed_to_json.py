import json, requests, xml.etree.ElementTree as ET
from urllib.parse import quote

FEED_URL = "https://dl.product-service.dognet.sk/fp/jateksziget.hu-arukereso.xml"
DOGNET_STD = "https://go.dognet.com/?dt=NGEc8ZwG&url="

def normalize_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip()
    if not u.startswith("http"):
        u = "https://" + u.lstrip("/")
    return u

def main():
    try:
        print("Letöltés:", FEED_URL)
        r = requests.get(FEED_URL, timeout=90)
        r.raise_for_status()
        xml = ET.fromstring(r.text)
    except Exception as e:
        print("❌ Hiba az XML letöltésében:", e)
        return

    products = []
    for item in xml.findall(".//product"):
        try:
            title = item.findtext("name") or ""
            price = item.findtext("price") or ""
            img = item.findtext("image_url") or ""
            url = item.findtext("product_url") or ""
            desc = item.findtext("description") or ""
            category = item.findtext("category") or ""

            if not title or not url:
                continue

            # Méretvariánsok kiszűrése (ha a névben van pl. 'XS', 'L', 'M', 'XL')
            if any(size in title.upper() for size in ["XS", "S ", "M ", "L ", "XL", "XXL", "EU", "UK", "US", " (SIZE"]):
                # csak egyszer tartjuk meg az adott terméket, ha már van hasonló név
                if any(p["title"].split()[0] in title for p in products):
                    continue

            products.append({
                "title": title.strip(),
                "price": price.strip(),
                "image": img.strip(),
                "url": DOGNET_STD + quote(normalize_url(url)),
                "desc": desc.strip(),
                "category": category.strip(),
            })
        except Exception as e:
            print("⚠️ Hiba elemnél:", e)
            continue

    print(f"✅ OK, {len(products)} termék feldolgozva")
    with open("docs/jateksziget.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print("→ Mentve: docs/jateksziget.json")

if __name__ == "__main__":
    main()
