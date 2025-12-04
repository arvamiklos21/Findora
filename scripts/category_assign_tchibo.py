# category_assign_tchibo.py
#
# Tchibo – CATEGORYTEXT alapú, tisztán szabályos kategória-hozzárendelés
#
# FŐ INTERFÉSZ (amit a build_tchibo.py használ):
#
#   from category_assign_tchibo import assign_category
#
#   findora_main = assign_category(fields)
#
# ahol fields egy dict pl.:
#   {
#     "product_type": "...",
#     "category": "...",
#     "categorytext": "...",
#     "title": "...",
#     "description": "..."
#   }
#
# A hozzárendelés CSAK a CATEGORYTEXT / product_type alapján dönt
# (Google taxo → Findora 25 fő kategória).


import os
import csv
from collections import Counter
from typing import Dict, Any

# ===== Findora 25 fő kategória (slugok) =====
# FONTOS: ezeknek egyezniük kell a globál Findora kategória-listával.
FINDORA_CATS = [
    "elektronika",
    "haztartasi_gepek",
    "szamitastechnika",
    "mobil",
    "gaming",
    "smart_home",
    "otthon",
    "lakberendezes",
    "konyha_fozes",
    "kert",
    "jatekok",
    "divat",
    "szepseg",
    "drogeria",
    "baba",
    "sport",
    "egeszseg",
    "latas",
    "allatok",
    "konyv",
    "utazas",
    "iroda_iskola",
    "szerszam_barkacs",
    "auto_motor",
    "multi",
]

# ===== CSV módhoz default utak (opcionális, csak ha __main__-ben futtatod) =====

INPUT_CSV = os.environ.get("TCHIBO_INPUT_CSV", r"D:\tchibo\tchibo_clean.csv")
OUTPUT_CSV = os.environ.get("TCHIBO_OUTPUT_CSV", r"D:\tchibo\tchibo_with_categories.csv")

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
    Electronics / Cameras & Optics finomhang (pl. mobil).
    """
    cat = (category_text or "").strip()

    # Mobil & kiegészítők
    if "Mobile Phone" in cat:
        return "mobil"

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


# ===== SEGÉDFÜGGVÉNYEK AZ assign_category-hez =====

def _extract_category_path(fields: Dict[str, Any]) -> str:
    """
    A lehető legjobb kategória-path kivétele a kapott mezőkből.
    Tchibónál ez lényegében CATEGORYTEXT / PARAM_CATEGORY / product_type.
    """
    # build_tchibo.py: "product_type", "category", "categorytext"
    for key in ("category_text", "categorytext", "product_type", "category", "product_category"):
        v = fields.get(key)
        if v:
            return str(v)
    return ""


def _extract_category_root_from_path(cat_path: str) -> str:
    """
    Gyökér (root) kivétele a path-ből.
    Pl.: 'Home & Garden > Kitchen & Dining > ...' → 'Home & Garden'
    """
    if not cat_path:
        return ""
    parts = [p.strip() for p in str(cat_path).split(">") if p.strip()]
    return parts[0] if parts else str(cat_path).strip()


# ===== FŐ INTERFÉSZ: assign_category(fields) =====

def assign_category(fields: Dict[str, Any]) -> str:
    """
    Ezt hívja a build_tchibo.py.

    fields: tetszőleges termékmezők dict-je:
      - elsősorban: categorytext / product_type / category
      - másodlagosan: title / description, stb. (most nem használjuk, de később lehet)

    Visszatérési érték: Findora fő kategória slug (pl. 'divat', 'otthon', stb.)
    """
    cat_path = _extract_category_path(fields)
    root = _extract_category_root_from_path(cat_path)

    cat = map_tchibo_to_findora(cat_path, root) or "multi"
    if cat not in FINDORA_CATS:
        cat = "multi"
    return cat


# ===== Opcionális: parancssoros futtatás CSV-re (mint a régi verzió) =====

def _assign_on_csv(input_csv: str, output_csv: str):
    """
    Ha közvetlenül futtatod a scriptet, egy tchibo_clean.csv-ből
    gyárt tchibo_with_categories.csv-t (findora_main mezővel).
    """
    if not os.path.exists(input_csv):
        print(f"[HIBA] Nem találom az input CSV-t: {input_csv}")
        return

    print(f"[INFO] Input:  {input_csv}")
    print(f"[INFO] Output: {output_csv}")

    with open(input_csv, "r", encoding="utf-8-sig", newline="") as f_in, \
         open(output_csv, "w", encoding="utf-8-sig", newline="") as f_out:

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
            cat_text = row.get("category_text", "") or row.get("categorytext", "")
            cat_root = row.get("category_root", "")

            # ha category_root nincs CSV-ben, path-ből is ki tudjuk szedni
            if not cat_root:
                cat_root = _extract_category_root_from_path(cat_text)

            findora_main = map_tchibo_to_findora(cat_text, cat_root) or "multi"
            if findora_main not in FINDORA_CATS:
                findora_main = "multi"

            row["findora_main"] = findora_main
            writer.writerow(row)

            counter[findora_main] += 1

    print(f"[OK] Kész: {output_csv}")
    print(f"[INFO] Összes termék: {total}")
    print("[INFO] Eloszlás findora_main szerint:")
    for k, v in sorted(counter.items(), key=lambda kv: kv[0]):
        print(f"  {k:20s} {v}")


if __name__ == "__main__":
    # Lokális használat esetén:
    # python category_assign_tchibo.py
    # -> TCHIBO_INPUT_CSV / TCHIBO_OUTPUT_CSV env változókkal felülírható az alapértelmezett D:\ paths
    _assign_on_csv(INPUT_CSV, OUTPUT_CSV)
