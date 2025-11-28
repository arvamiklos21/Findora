# scripts/category_assign_decathlon.py

import re

# Findora fő kategória ID-k – direktben itt definiálva,
# hogy ne kelljen a category_assign modulból importálni.
KAT_ELEK   = "elektronika"
KAT_GEPEK  = "haztartasi_gepek"
KAT_OTTHON = "otthon"
KAT_JATEK  = "jatekok"
KAT_DIVAT  = "divat"
KAT_SZEPSEG = "szepseg"
KAT_SPORT   = "sport"
KAT_KONYV   = "konyv"
KAT_ALLAT   = "allatok"
KAT_LATAS   = "latas"
KAT_MULTI   = "multi"


def _normalize(text: str) -> str:
    return (text or "").lower()


def _root_from_path(cat_path: str) -> str:
    """
    Decathlon product_type első szintje ( > előtt).
    Példa:
      "Sportok > Sportgyaloglás > Utcai gyaloglócipők > Férfi gyaloglócipő"
      → "sportok"
    """
    if not cat_path:
        return ""
    root = cat_path.split(">")[0]
    return root.strip().lower()


# Kulcsszavak, ha később finomítani akarunk Decathlonon belül
SPORT_KEYWORDS = [
    "sportok",
    "sportgyaloglás",
    "futás",
    "futócipő",
    "gyaloglócipő",
    "gyaloglás",
    "kerékpár",
    "bicikli",
    "kerékpáros",
    "fitnesz",
    "edzés",
    "jóga",
    "úszás",
    "uszoda",
    "labdarúgás",
    "foci",
    "kosárlabda",
    "kézilabda",
    "tenisz",
    "asztalitenisz",
    "pingpong",
    "sí",
    "snowboard",
    "túrázás",
    "trekking",
    "kemping",
]

ELECTRO_KEYWORDS = [
    "óra",
    "óra.",
    "sportóra",
    "pulzusmérő",
    "pulzusmero",
    "gps",
    "activity tracker",
    "okosóra",
    "okosora",
    "headphones",
    "fülhallgató",
    "bluetooth",
]

HOME_KEYWORDS = [
    "otthon",
    "lakberendezés",
    "bútor",
    "asztal",
    "szék",
    "polc",
    "tároló",
]


def assign_category(
    product_type: str = "",
    google_cat: str = "",
    title: str = "",
    desc: str = "",
) -> str:
    """
    Decathlon-specifikus kategória hozzárendelés.

    Bemenet: Decathlon feed mezők:
      - product_type   → g:product_type (pl. "Sportok > Sportgyaloglás > ...")
      - google_cat     → g:google_product_category (pl. "Apparel & Accessories > Shoes")
      - title          → g:title
      - desc           → g:description

    Kimenet: Findora fő kategória ID (pl. "sport", "elektronika", stb. – a KAT_* konstansok).
    """

    pt_norm = _normalize(product_type)
    gc_norm = _normalize(google_cat)
    t_norm  = _normalize(title)
    d_norm  = _normalize(desc)

    full_text = " ".join(x for x in [pt_norm, gc_norm, t_norm, d_norm] if x)

    # 1) Ha product_type gyökerében „sportok” van → egyértelműen sport
    root = _root_from_path(product_type)
    if root.startswith("sport"):
        return KAT_SPORT

    # 2) Ha bármelyik sport kulcsszó szerepel → sport
    if any(kw in full_text for kw in SPORT_KEYWORDS):
        return KAT_SPORT

    # 3) Ha jellemzően sportcipő / sport ruházat (Decathlon esetek 90%-a) → sport
    if (
        "cipő" in full_text
        or "cipo" in full_text
        or "edzőcipő" in full_text
        or "sportmelltartó" in full_text
    ):
        return KAT_SPORT

    # 4) Sport elektronika – ha később külön akarjuk venni elektronikába
    if any(kw in full_text for kw in ELECTRO_KEYWORDS):
        # Dönthetsz úgy is, hogy sportban marad, de most elektronikába tesszük:
        return KAT_ELEK

    # 5) Otthon / bútor jellegű termékek
    if any(kw in full_text for kw in HOME_KEYWORDS):
        # Ha otthonba akarod tolni:
        # return KAT_OTTHON
        return KAT_SPORT

    # 6) Ha csak „Apparel & Accessories > Shoes” van, sportkörnyezet nélkül,
    # még akkor is sportként kezeljük (Decathlon márka)
    if "apparel & accessories" in gc_norm or "shoes" in gc_norm:
        return KAT_SPORT

    # 7) Biztonsági alapértelmezett: Decathlon partner → sport
    return KAT_SPORT
