# category_assign.py
#
# Központi kategória-hozzárendelés partnerenként.
# Visszaadott érték: findora_main (elektronika, otthon, divat, jatekok, sport, kert, haztartasi_gepek, multi)

from typing import Optional


# =======================================================
#   TCHIBO → FINDORA MAIN CATEGORY
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
    - partner_id: 'tchibo', később 'alza', 'pepita', stb.
    - cat_path: eredeti feed kategória
    - title / desc: későbbi kulcsszavas finomításra
    """

    pid = (partner_id or "").lower()

    # ===== TCHIBO =====
    if pid == "tchibo":
        return _tchibo_findora_main(cat_path or "")

    # ===== további partnerek később =====
    # if pid == "alza": ...
    # if pid == "pepita": ...

    # ===== alapértelmezett =====
    return "multi"
