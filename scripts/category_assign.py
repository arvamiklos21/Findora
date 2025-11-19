# category_assign.py
#
# Központi kategória-hozzárendelés partnerenként.
# Első körben csak Tchibo, később bővíthető (Alza, Pepita, stb.).
#
# Visszaadott érték: findora_main (elektronika, otthon, divat, jatekok, sport, kert, haztartasi_gepek, multi)

from typing import Optional


def _tchibo_findora_main(cat_path: str) -> str:
    """
    Tchibo XML/CSV kategória -> Findora főkategória (findora_main).
    A bemenet tipikusan a param_category mező, pl.:
      "Apparel & Accessories > Clothing > Outerwear > Coats & Jackets"
      "Home & Garden > Kitchen & Dining > Kitchen Appliances"
    """

    s = (cat_path or "").lower()

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
        "socks & tights"
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
        "bookcases"
    ]):
        return "otthon"

    # ===== JÁTÉKOK =====
    if any(k in s for k in [
        "baby toys & activity equipment",
        "baby toys",
        "toys",
        "board games",
        "puzzles"
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
        "outdoor recreation"
    ]):
        return "sport"

    # ===== KERT =====
    if any(k in s for k in [
        "outdoor furniture",
        "outdoor furniture accessories",
        "outdoor furniture sets",
        "outdoor furniture covers",
        "birdhouses",
        "bird & wildlife houses"
    ]):
        return "kert"

    # ===== HÁZTARTÁSI GÉPEK / HÁZTARTÁS =====
    if any(k in s for k in [
        "kitchen appliances",
        "small appliances",
        "kitchen tools & utensils",
        "can openers",
        "colanders & strainers",
        "tableware",
        "flatware"
    ]):
        return "haztartasi_gepek"

    # ===== ALAPÉRTELMEZETT =====
    # Ide esik:
    # - Luggage & Bags
    # - bármilyen ismeretlen / új kategória
    return "multi"


def assign_category(
    partner_id: str,
    cat_path: Optional[str],
    title: str = "",
    desc: str = "",
) -> str:
    """
    Általános belépőpont:
    - partner_id: 'tchibo', később 'alza', 'pepita', stb.
    - cat_path: feed kategória útvonal (param_category / CATEGORY_PATH / stb.)
    - title, desc: később finomhangoláshoz (ha kell kulcsszó)
    """

    pid = (partner_id or "").lower()

    if pid == "tchibo":
        return _tchibo_findora_main(cat_path or "")

    # Később ide jönnek:
    # if pid == "alza": ...
    # if pid == "pepita": ...

    # Ha nincs specifikus szabály, multi
    return "multi"
