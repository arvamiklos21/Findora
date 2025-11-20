import xml.etree.ElementTree as ET
import os

# Itt adjuk meg a feed helyét
XML_PATH = "private_feeds/Affiliate_18855692_HU.xml.rss"

if not os.path.exists(XML_PATH):
    print("HIBA: Az XML nem található:", XML_PATH)
    exit()

tree = ET.parse(XML_PATH)
root = tree.getroot()

ns = {"g": "http://base.google.com/ns/1.0"}

unique_cats = set()

for item in root.findall(".//item"):
    pt = item.find("g:product_type", ns)
    if pt is None or not pt.text:
        continue

    raw = pt.text.strip()
    if not raw:
        continue

    # Szintek szétvágása
    parts = [p.strip() for p in raw.split("|") if p.strip()]

    # Csak az első két szint kell
    if len(parts) >= 2:
        key = f"{parts[0]}|{parts[1]}"
    elif len(parts) == 1:
        key = parts[0]  # fallback
    else:
        continue

    unique_cats.add(key)

print("\n=== Alza: egyedi első 2 szintű kategóriák ===\n")
for c in sorted(unique_cats):
    print(c)

print("\nÖsszes különböző kategória:", len(unique_cats))
