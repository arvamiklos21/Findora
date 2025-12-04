# category_assign_bolt.py
#
# Onlinemarkaboltok / BOLT – egyszerű, szabályalapú kategorizálás
# CÉL: csak két Findora fő kategória:
#   - haztartasi_gepek  (minden, ami gép / elektromos cucc)
#   - otthon            (minden más)
#
# FŐ INTERFÉSZ (build scripthez):
#
#   from category_assign_bolt import assign_category
#   cat = assign_category(fields)
#
# ahol fields egy dict pl.:
#   {
#     "category_text": "...",
#     "category": "...",
#     "product_type": "...",
#     "title": "...",
#   }
#
# CLI mód:
#   INPUT_CSV (bolt_clean.csv: title, desc, category_text, category_root)
#   → OUTPUT_CSV (bolt_with_categories.csv: + findora_main)

import os
import csv
import unicodedata
from typing import Dict, Any
from collections import Counter

# ===== Findora kategória slugok (referencia) =====

FINDORA_CATS = [
    "elektronika",
    "haztartasi_gepek",
    "szamitastechnika",
    "mobiltelefon",
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

# Itt most *valójában* csak kettőt fogunk használni:
APPLIANCE_CAT = "haztartasi_gepek"
HOME_CAT = "otthon"

# ===== CSV mód alapértelmezett útvonalak =====

INPUT_CSV = os.environ.get("BOLT_INPUT_CSV", r"D:\bolt\bolt_clean.csv")
OUTPUT_CSV = os.environ.get("BOLT_OUTPUT_CSV", r"D:\bolt\bolt_with_categories.csv")


def normalize_text(s: str) -> str:
    """
    Kisbetű, ékezetek lecsupaszítása, extra whitespace eltüntetése.
    Így könnyebb kulcsszóra keresni (hutoszekreny vs hűtőszekrény).
    """
    if not s:
        return ""
    s = str(s)
    # kisbetű
    s = s.lower()
    # ékezetek levétele
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    # whitespace tisztítás
    s = " ".join(s.split())
    return s


# ===== ELEKTROMOS / GÉP JELLEG DETEKTÁLÁS =====

APPLIANCE_KEYWORDS = [
    # Nagygépek
    "beepitheto suto",
    "gozsuto",
    "gozparolo",
    "fozolap",
    "indukcios fozolap",
    "gaz fozolap",
    "keramia fozolap",
    "hutohutofagyaszto",  # biztonsag kedveert, de altalaban:
    "hutohutofagyaszto",  # duplán se árt
    "hutohutofagyaszto >",
    "hutotaska",  # ez kicsit határeset, de simán mehet gépnek is

    "hutohuto",  # általános: "hutoszekreny"
    "hutoszekreny",
    "fagyaszto",
    "fagyasztolada",
    "fagyasztoszekreny",
    "felulfagyasztos hutok",
    "side-by-side",  # side-by-side hűtők
    "4 ajtos hutok",

    # Mosógép / mosogatógép / szárító / kombinált
    "mosogatogep",
    "beepitheto mosogatogep",
    "szabadon allo mosogatogep",
    "szabadonallo mosogatogep",
    "mosogep",
    "eloltoltos mosogep",
    "felultoltos mosogep",
    "moso- es szaritogep",
    "szaritogep",
    "hoszivattyus szaritogep",

    # Tűzhely
    "tuzhely",
    "elektromos tuzhely",
    "gaztuzhely",
    "kombinalt tuzhely",

    # Mikrohullámú
    "mikrohullamu suto",
    "mikrohullamu sutok",

    # Konyhai kisgépek (ezeket is gépnek vesszük)
    "konyhai kisgepek",
    "kavefozo",
    "filters kavefozo",
    "orlomuves automata kavefozo",
    "kaveorlo",
    "kavedaralo",
    "vizforralo",
    "kenyerpirito",
    "kenyersuto",
    "robotgep",
    "botmixer",
    "kezi mixer",
    "talas kezi mixer",
    "turmix",
    "goffrisuto",
    "szendvicssuto",
    "grill",
    "kontaktgrill",
    "gyumolcs centrifuga",
    "fagylaltkeszito",
    "aszalo",
    "jegkocka keszito",
    "gozsuto fritozok fozoedenyek",
    "vacuumcsomagolo",
    "szeletelogep",

    # Porszívó / takarítógép
    "porszivo",
    "porzsakos porszivo",
    "porzsak nelkuli porszivo",
    "robotporszivo",
    "morzsaporszivo",
    "akkus kezi porszivo",
    "szaraz-nedves porszivo",
    "vizszuro porszivo",
    "takaritogep",
    "porszivo es takaritogepek",

    # Vasalás
    "vasalo",
    "gozallomas",
    "vasalodeszka",

    # Légtechnika, klíma, fűtés
    "futestechnika",
    "hoszivattyu",
    "mobil klima",
    "levego parasito",
    "levego paramenetesito",
    "legtisztito",
    "parasito, paramenetesito, legtisztito",
    "paramenetesito",

    # Szellőztető ventilátor
    "szellozteto ventilator",
    "egyhelyseges hovisszanyero szellozteto ventilator",

    # Egyéb kategóriás kulcsszavak, amik biztosan gépek:
    "haztartasi hutoszekreny",
    "haztartasi nagygepek",
    "haztartasi keszulekek",
]

# plusz olyan kulcsszó-csoportok, amiket egy az egyben gépnek veszünk
APPLIANCE_ROOT_KEYWORDS = [
    "haztartasi hutoszekreny es fagyaszto",
    "haztartasi nagygepek",
    "haztartasi keszulekek",
]


def is_appliance_category(category_text: str) -> bool:
    """
    Eldönti, hogy a BOLT generic category_text háztartási gép-e.
    Egyszerű substring-keresés a normalizált szövegben.
    """
    norm = normalize_text(category_text)

    # root-szintű kulcsszavak
    for kw in APPLIANCE_ROOT_KEYWORDS:
        if kw in norm:
            return True

    # részletesebb kulcsszavak
    for kw in APPLIANCE_KEYWORDS:
        if kw in norm:
            return True

    return False


# ===== PATH KINYERŐ =====

def extract_category_path(fields: Dict[str, Any]) -> str:
    """
    BOLT termékmezők közül a legjobb kategória-path kiválasztása.
    """
    for key in ("category_text", "categorytext", "product_type", "category"):
        v = fields.get(key)
        if v:
            return str(v)
    return ""


# ===== FŐ MAPPING =====

def map_bolt_to_findora(category_text: str) -> str:
    """
    Egyszerű szabály:
      - ha a kategória "gépes" → haztartasi_gepek
      - egyébként            → otthon
    """
    if not category_text:
        return HOME_CAT

    if is_appliance_category(category_text):
        return APPLIANCE_CAT

    return HOME_CAT


# ===== KÜLSŐ INTERFÉSZ, amit a build script hív =====

def assign_category(fields: Dict[str, Any]) -> str:
    """
    Fő belépési pont: BOLT termékmezők → Findora fő kategória slug.
    """
    cat_path = extract_category_path(fields)
    cat = map_bolt_to_findora(cat_path)

    # Biztonság kedvéért, ha valami félremenne:
    if cat not in FINDORA_CATS:
        cat = HOME_CAT

    return cat


# ===== CSV mód: bolt_clean.csv → bolt_with_categories.csv =====

def _assign_on_csv(input_csv: str, output_csv: str):
    """
    Ha közvetlenül futtatod a scriptet:
      - beolvassa a bolt_clean.csv-t
      - hozzárak egy findora_main oszlopot (haztartasi_gepek / otthon)
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

            findora_main = map_bolt_to_findora(cat_text)
            if findora_main not in FINDORA_CATS:
                findora_main = HOME_CAT

            row["findora_main"] = findora_main
            writer.writerow(row)

            counter[findora_main] += 1

    print(f"[OK] Kész: {output_csv}")
    print(f"[INFO] Összes termék: {total}")
    print("[INFO] Eloszlás findora_main szerint:")
    for k, v in sorted(counter.items(), key=lambda kv: kv[0]):
        print(f"  {k:20s} {v}")


if __name__ == "__main__":
    # Lokál teszt:
    #   python category_assign_bolt.py
    #
    # Tetszés szerint:
    #   set BOLT_INPUT_CSV=D:\bolt\bolt_clean.csv
    #   set BOLT_OUTPUT_CSV=D:\bolt\bolt_with_categories.csv
    _assign_on_csv(INPUT_CSV, OUTPUT_CSV)
