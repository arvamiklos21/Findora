# category_assign.py
#
# Központi kategória-hozzárendelés partnerenként.
# Visszaadott érték: findora_main
#   (elektronika, otthon, divat, jatekok, sport, kert,
#    haztartasi_gepek, szepseg, konyv, allatok, latas,
#    utazas, multi, ...)

from typing import Optional


# =======================================================
#   TCHIBO → FINDORA MAIN CATEGORY  (MEGMARAD)
# =======================================================

def _tchibo_findora_main(cat_path: str) -> str:
    """
    Tchibo kategória → Findora főkategória.

    A cat_path tipikusan:
      - CATEGORYTEXT
      - PARAM_CATEGORY
    pl:
      "Apparel & Accessories > Clothing > Outerwear > Coats & Jackets"
      "Home & Garden > Kitchen & Dining > Kitchen Appliances"
    """

    s = (cat_path or "").lower().strip()

    # ===== DIVAT =====
    if any(k in s for k in [
        "apparel & accessories",
        "clothing",
        "outerwear",
        "bras",
        "underwear & socks",
        "shoes",
        "sleepwear & loungewear",
        "skirts",
        "pants",
        "dresses",
        "baby & toddler clothing",
        "toddler underwear",
        "socks & tights",
    ]):
        return "divat"

    # ===== OTTHON =====
    if any(k in s for k in [
        "home & garden",
        "furniture",
        "kitchen & dining",
        "decor",
        "bedding",
        "linens & bedding",
        "lighting",
        "household cleaning supplies",
        "household supplies",
        "cabinets & storage",
        "shelving",
        "bookcases",
    ]):
        return "otthon"

    # ===== JÁTÉKOK =====
    if any(k in s for k in [
        "baby toys & activity equipment",
        "baby toys",
        "toys",
        "board games",
        "puzzles",
    ]):
        return "jatekok"

    # ===== SPORT =====
    if any(k in s for k in [
        "sporting goods",
        "cycling",
        "bicycle accessories",
        "cycling apparel & accessories",
        "camping & hiking",
        "exercise & fitness",
        "outdoor recreation",
    ]):
        return "sport"

    # ===== KERT =====
    if any(k in s for k in [
        "outdoor furniture",
        "outdoor furniture accessories",
        "outdoor furniture sets",
        "outdoor furniture covers",
        "birdhouses",
        "bird & wildlife houses",
    ]):
        return "kert"

    # ===== HÁZTARTÁSI GÉPEK =====
    if any(k in s for k in [
        "kitchen appliances",
        "small appliances",
        "kitchen tools & utensils",
        "can openers",
        "colanders & strainers",
        "tableware",
        "flatware",
    ]):
        return "haztartasi_gepek"

    # ===== ALAPÉRTELMEZETT =====
    return "multi"


# =======================================================
#   ALZA → FINDORA MAIN CATEGORY  (ÚJ LOGIKA)
#   CSAK AZ ALZA CATEGORY_PATH ELSŐ SZINTJÉT NÉZZÜK.
#   NINCS kulcsszózás title/desc alapján.
# =======================================================

# Alza top-level kategória → Findora fő kategória
# (minden kulcs kisbetűs!)
_ALZA_TOP_MAP = {
    # Elektronika / számítástechnika
    "elektronika": "elektronika",
    "számítógép": "elektronika",
    "számítógép, notebook": "elektronika",
    "mobiltelefon": "elektronika",
    "mobiltelefon, tablet": "elektronika",
    "játékkonzolok, gaming": "elektronika",

    # Háztartási gépek / háztartás
    "háztartási gépek": "haztartasi_gepek",
    "háztartás": "haztartasi_gepek",

    # Otthon / bútor / dekor
    "otthon": "otthon",
    "otthon és kert": "otthon",
    "bútor": "otthon",
    "dekoráció": "otthon",

    # Kert
    "kert": "kert",

    # Játékok / gyerek
    "játékok": "jatekok",
    "gyermek, mama": "jatekok",
    "gyermek, mama, játékok": "jatekok",

    # Sport
    "sport, szabadidő": "sport",
    "sport": "sport",
    "sport és szabadidő": "sport",

    # Szépség
    "szépség, egészség": "szepseg",
    "szépség és egészség": "szepseg",
    "drogéria": "szepseg",

    # Könyvek
    "könyvek": "konyv",
    "könyvek, e-könyvek, filmek, zenék": "konyv",

    # Állatok
    "állateledel, állatfelszerelés": "allatok",
    "állateledel": "allatok",

    # Látás / optika
    "látás, optika": "latas",

    # Utazás / autó
    "utazás": "utazas",
    "utazás és autó": "utazas",
    "autó, motor": "utazas",
}


def _normalize_alza_top(cat_path: str) -> str:
    """
    Alza category_path normalizálása:
    - csak az első szintet vesszük (a '|' előtti részt)
    - kisbetűsítjük, levágjuk a fölösleges szóközöket
    """
    s = (cat_path or "").strip().lower()
    if not s:
        return ""
    first = s.split("|", 1)[0].strip()
    return first


def _alza_findora_main(cat_path: str, title: str = "", desc: str = "") -> str:
    """
    Alza kategória → Findora főkategória.

    FONTOS:
    - Nem használunk kulcsszót a title/desc mezőkből.
    - Csak az Alza saját category_path TOP szintje számít.
    - Így NINCS átcsúszás (borotva nem megy Játékokba, fékpofa
      nem megy Elektronikába stb.).
    """
    top = _normalize_alza_top(cat_path)

    if not top:
        return "multi"

    # Direkt, pontos egyezés a mapping táblával
    if top in _ALZA_TOP_MAP:
        return _ALZA_TOP_MAP[top]

    # Ha valami új / ritka fő kategória jön,
    # inkább menjen a 'multi' blokkba, mint rossz helyre.
    return "multi"


# =======================================================
#   ÁLTALÁNOS HOZZÁRENDELÉS – több partner támogatása
# =======================================================

def assign_category(
    partner_id: str,
    cat_path: Optional[str],
    title: str = "",
    desc: str = "",
) -> str:
    """
    Központi kategória-hozzárendelés.
    - partner_id: 'tchibo', 'alza', később 'pepita', stb.
    - cat_path: eredeti feed kategória
    - title / desc: jelenleg csak Tchibónál használjuk finomításra
    """
    pid = (partner_id or "").lower()

    # ===== TCHIBO =====
    if pid == "tchibo":
        return _tchibo_findora_main(cat_path or "")

    # ===== ALZA =====
    if pid == "alza":
        return _alza_findora_main(cat_path or "", title or "", desc or "")

    # ===== további partnerek később =====
    # if pid == "pepita":
    #     ...

    # ===== alapértelmezett =====
    return "multi"
