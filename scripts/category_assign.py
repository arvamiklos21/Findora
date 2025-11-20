# category_assign.py
#
# Központi kategória-hozzárendelés partnerenként.
# Visszaadott érték: findora_main:
#   elektronika, otthon, divat, jatekok, sport, kert,
#   haztartasi_gepek, konyv, allatok, utazas, multi

from typing import Optional
import re


# =======================================================
#   TCHIBO → FINDORA MAIN CATEGORY  (VÁLTOZATLAN!)
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
#   CSAK category_path-ból dolgozunk, cím/desc nem számít
# =======================================================

def _alza_findora_main(cat_path: str, title: str = "", desc: str = "") -> str:
    """
    Alza kategória → Findora főkategória.
    cat_path pl.:
      "Sport, szabadidő|Kerékpározás|Kerékpár kiegészítők|Lámpák"
      "Telefon, tablet, okosóra|Okosórák"
      "Otthon, barkács, kert|Kert|Kerti bútorok|Nyugágyak"
    """

    s = (cat_path or "").strip()
    if not s:
        return "multi"

    # |, >, / mentén darabolunk, kisbetűsítve
    parts = [p.strip().lower() for p in re.split(r"[|>/]", s) if p.strip()]
    if not parts:
        return "multi"

    root = parts[0]           # főkategória – ez az Alza felső menü
    full = " ".join(parts)    # minden szint egyben

    # ===== JÁTÉKOK =====
    if "játék" in root or "jatek" in root or "baba-mama" in root:
        return "jatekok"

    # ===== KÖNYV =====
    if "könyv" in root or "konyv" in root:
        return "konyv"

    # ===== ÁLLATOK =====
    if "állat" in full or "allat" in full:
        return "allatok"

    # ===== SPORT =====
    if "sport" in root or "szabadidő" in root or "szabadido" in root:
        return "sport"

    # ===== ELEKTRONIKA – telefon, pc, gaming, tv, okosotthon =====
    if any(kw in root for kw in [
        "telefon", "tablet", "okosóra", "okosora",
        "pc", "laptop", "számítógép", "szamitogep",
        "gaming",
        "tv", "fotó", "foto", "audió", "audio",
    ]):
        return "elektronika"

    if "okosotthon" in root:
        return "elektronika"

    # ===== HÁZTARTÁSI GÉPEK =====
    if "háztartási kisgép" in root or "haztartasi kisgep" in root:
        return "haztartasi_gepek"
    if "háztartási nagygép" in root or "haztartasi nagyg" in root:
        return "haztartasi_gepek"

    # Konyha, háztartás → ha kis/nagygép jellegű, akkor haztartasi_gepek, különben otthon
    if "konyha, háztartás" in root or "konyha, haztartas" in root:
        if any(kw in full for kw in [
            "kisgép", "kisgep", "nagygép", "nagyg",
            "konyhai kisgép", "konyhai kisgep"
        ]):
            return "haztartasi_gepek"
        return "otthon"

    # ===== OTTHON + KERT =====
    if "otthon, barkács, kert" in root or "otthon, barkacs, kert" in root:
        # ha van 'kert' szint – menjen a KERT kategóriába
        if any("kert" in p for p in parts[1:]):
            return "kert"
        # különben sima otthon
        return "otthon"

    # ===== UTAZÁS =====
    if any("utazás" in p or "utazas" in p for p in parts):
        return "utazas"

    # ===== SZÉPSÉG / DROGÉRIA – egyelőre MULTI-ba megy =====
    if any(kw in root for kw in ["drogéria", "drogeria", "illatszer", "kozmetika"]):
        return "multi"

    # ===== AUTÓ, EGÉSZSÉG, IRODA, ÉLELMISZER – vegyes dolgok → multi =====
    if any(kw in root for kw in [
        "autó-motor", "auto-motor",
        "egészség", "egeszseg",
        "irodai felszerelés", "irodai felszereles",
        "élelmiszer", "elelmiszer",
    ]):
        return "multi"

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
    - partner_id: 'tchibo', 'alza', később 'pepita', stb.
    - cat_path: eredeti feed kategória (Alza: "X|Y|Z", Tchibo: "A > B > C")
    - title / desc: most ALZA-nál NEM használjuk, csak későbbi finomhangoláshoz hagyjuk bent.
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
