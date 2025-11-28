# category_assign_tchibo.py
#
# Tchibo – CATEGORYTEXT alapú, tisztán szabályos kategória-hozzárendelés
# input:  D:\tchibo\tchibo_clean.csv
#         (oszlopok: title, desc, category_text, category_root)
# output: D:\tchibo\tchibo_with_categories.csv
#         (ugyanez + findora_main)
#
# NINCS model.pkl, nincs ML – csak Google taxo → Findora 25 fő kategória szabály.

import os
import csv
from collections import Counter

INPUT_CSV = r"D:\tchibo\tchibo_clean.csv"
OUTPUT_CSV = r"D:\tchibo\tchibo_with_categories.csv"

# --- Root → Findora fő kategória (ha nincs speciális finomhang) ---

ROOT_MAP = {
    "Animals & Pet Supplies": "allatok",
    "Apparel & Accessories": "divat",
    "Arts & Entertainment": "jatekok",
    "Baby & Toddler": "baba",
    "Business & Industrial": "otthon",
    "Cameras & Optics": "elektronika",
    "Electronics": "elektronika",
    "Food, Beverages & Tobacco": "konyha_fozes",
    "Furniture": "otthon",
    "Hardware": "szerszam_barkacs",
    "Health & Beauty": "egeszseg",
    "Home & Garden": "otthon",  # itt külön kezeljük majd részletesen
    "Luggage & Bags": "divat",
    "Office Supplies": "iroda_iskola",
    "Sporting Goods": "sport",
    "Vehicles & Parts": "auto_motor",
}


# ===== SPEC. LOGIKÁK =====

def map_home_and_garden(category_text: str) -> str:
    """
    Home & Garden részletes felbontása Findora fő kategóriákra.
    """
    cat = (category_text or "").strip()

    # KONYHA & FŐZÉS
    if "Home & Garden > Kitchen & Dining" in cat:
        return "konyha_fozes"

    # KERT
    if "Home & Garden > Lawn & Garden" in cat:
        return "kert"

    # HÁZTARTÁSI GÉPEK
    if "Home & Garden > Household Appliances" in cat:
        return "haztartasi_gepek"

    # DROGÉRIA – takarítás, mosás
    if "Home & Garden > Household Supplies > Household Cleaning Supplies" in cat:
        return "drogeria"
    if "Home & Garden > Household Supplies > Laundry Supplies" in cat:
        return "drogeria"

    # OTTHON – textil, dekor, világítás, tárolás, fürdőszoba
    if "Home & Garden > Decor" in cat:
        return "otthon"
    if "Home & Garden > Lighting" in cat:
        return "otthon"
    if "Home & Garden > Linens & Bedding" in cat:
        return "otthon"
    if "Home & Garden > Bathroom Accessories" in cat:
        return "otthon"
    if "Home & Garden > Household Supplies > Storage & Organization" in cat:
        return "otthon"

    # Fallback
    return "otthon"


def map_health_and_beauty(category_text: str) -> str:
    """
    Health & Beauty finomhang: szepseg / drogeria / egeszseg / latas.
    """
    cat = (category_text or "").strip()

    # Egészség
    if "First Aid" in cat or "Hot & Cold Therapies" in cat or "Medical Tape & Bandages" in cat:
        return "egeszseg"
    if "Massage & Relaxation" in cat:
        return "egeszseg"

    # Szépség
    if "Cosmetics" in cat or "Bath & Body" in cat or "Skin Care" in cat:
        return "szepseg"

    # Drogéria
    if "Adult Hygienic Wipes" in cat:
        return "drogeria"

    # Látás
    if "Vision Care > Eyeglasses" in cat:
        return "latas"

    # Fallback: alap root-map
    return "egeszseg"


def map_electronics_like(category_text: str, root: str) -> str:
    """
    Electronics / Cameras & Optics finomhang (pl. mobiltelefon).
    """
    cat = (category_text or "").strip()

    # Mobil & kiegészítők
    if "Mobile Phone" in cat:
        return "mobiltelefon"

    # később: webcam -> szamitastechnika stb.
    return "elektronika"


def map_tchibo_to_findora(category_text: str, category_root: str) -> str:
    """
    Tchibo CATEGORYTEXT + category_root → Findora fő kategória (slug).
    Csak szabályalapú.
    """
    root = (category_root or "").strip()
    cat = (category_text or "").strip()

    # Home & Garden részletesen
    if root == "Home & Garden":
        return map_home_and_garden(cat)

    # Health & Beauty finomhang
    if root == "Health & Beauty":
        return map_health_and_beauty(cat)

    # Electronics / Cameras & Optics
    if root in ("Electronics", "Cameras & Optics"):
        return map_electronics_like(cat, root)

    # Animals & Pet Supplies – direkt allatok
    if root == "Animals & Pet Supplies":
        return "allatok"

    # Sporting Goods – direkt sport
    if root == "Sporting Goods":
        return "sport"

    # Baby & Toddler – direkt baba
    if root == "Baby & Toddler":
        return "baba"

    # Alap root-map fallback
    return ROOT_MAP.get(root, "multi")


# ===== FŐ PROGRAM =====

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"[HIBA] Nem találom az input CSV-t: {INPUT_CSV}")
        return

    print(f"[INFO] Input:  {INPUT_CSV}")
    print(f"[INFO] Output: {OUTPUT_CSV}")

    with open(INPUT_CSV, "r", encoding="utf-8-sig", newline="") as f_in, \
         open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f_out:

        reader = csv.DictReader(f_in)
        fieldnames = list(reader.fieldnames) if reader.fieldnames else []
        if "findora_main" not in fieldnames:
            fieldnames.append("findora_main")

        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        counter = Counter()
        total = 0

        for row in reader:
            total += 1
            cat_text = row.get("category_text", "")
            cat_root = row.get("category_root", "")

            findora_main = map_tchibo_to_findora(cat_text, cat_root)
            row["findora_main"] = findora_main
            writer.writerow(row)

            counter[findora_main] += 1

    print(f"[OK] Kész: {OUTPUT_CSV}")
    print(f"[INFO] Összes termék: {total}")
    print("[INFO] Eloszlás findora_main szerint:")
    for k, v in sorted(counter.items(), key=lambda kv: kv[0]):
        print(f"  {k:20s} {v}")


if __name__ == "__main__":
    main()
