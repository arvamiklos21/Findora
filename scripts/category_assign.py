# category_assign.py
#
# Központi kategória-hozzárendelés partnerenként.
# Visszaadott érték: findora_main (elektronika, otthon, divat,
# jatekok, sport, kert, haztartasi_gepek, multi)

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
#   ALZA → FINDORA MAIN CATEGORY
# =======================================================

def _alza_findora_main(cat_path: str, title: str, desc: str) -> str:
    """
    Alza kategória + cím + leírás → Findora főkategória.
    A cat_path tipikusan ilyen:
      "Sport, szabadidő|Kerékpározás|Kerekpár kiegészítők|Fékkar|Fékpofák"
    """

    s = f"{cat_path or ''} {title or ''} {desc or ''}".lower()

    # ===== ELEKTRONIKA =====
    if any(k in s for k in [
        "notebook", "laptop", "ultrabook",
        "pc ", "számítógép", "szamitogep",
        "monitor", "videokártya", "videokartya",
        "alaplap", "processzor", "cpu",
        "ssd", "hdd", "memória", "ram",
        "tv", "televízió", "televizio",
        "tablet", "okostelefon", "okos telefon",
        "smartphone", "telefon",
        "játék konzol", "játékkonzol", "playstation", "xbox", "nintendo",
        "router", "wifi router",
        "hangfal", "hangszóró", "hangsugárzó", "fejhallgató", "fülhallgató",
    ]):
        return "elektronika"

    # ===== HÁZTARTÁSI GÉPEK =====
    if any(k in s for k in [
        "mosógép", "mosogep",
        "mosogatógép", "mosogatogep",
        "hűtőszekrény", "hutő", "huto", "fagyasztó",
        "porszívó", "porszivo",
        "mikrohullámú", "mikrohullamu", "mikro",
        "sütő", "suto",
        "klíma", "klima", "légkondi", "legkondi",
        "konyhai robot", "turmix", "botmixer",
        "kávéfőző", "kavefozo", "kávégép", "kavegep",
    ]):
        return "haztartasi_gepek"

    # ===== OTTHON =====
    if any(k in s for k in [
        "bútor", "butor",
        "szekrény", "szekreny",
        "asztal", "szék", "szek",
        "polc", "komód", "komod",
        "kanapé", "kanape", "fotel",
        "szőnyeg", "szonyeg",
        "dekor", "dísz", "disz",
        "világítás", "vilagitas", "lámpa", "lampa",
        "takaró", "takaro", "párna", "parna",
        "függöny", "fuggony",
        "ágynemű", "agynemu",
    ]):
        return "otthon"

    # ===== DIVAT =====
    if any(k in s for k in [
        "ruházat", "ruhazat", "ruha",
        "kabát", "kabat", "dzseki",
        "pulóver", "pulover",
        "nadrág", "nadrag",
        "szoknya", "blúz", "bluz",
        "ing", "póló", "polo",
        "cipő", "cipo", "csizma", "papucs",
        "fehérnemű", "fehernemu", "melltartó", "melltarto",
        "alsónadrág", "alsonadrag",
        "harisnya", "leggings",
    ]):
        return "divat"

    # ===== JÁTÉKOK =====
    if any(k in s for k in [
        "lego",
        "játék", "jatekok", "játékszett", "jatekszett",
        "társasjáték", "tarsasjatek",
        "puzzle",
        "plüss", "plus", "figura",
        "baba", "babakocsi",
        "kreatív játék", "kreativ jatek",
    ]):
        return "jatekok"

    # ===== SPORT =====
    if any(k in s for k in [
        "sport", "sportszer",
        "kerékpár", "kerekpar", "bicikli", "kerékpáros", "kerekparos",
        "futópad", "futopad",
        "súlyzó", "sulyzo",
        "edzés", "edzes", "fitnesz", "fitness",
        "túra", "tura",
        "kemping", "sátor", "sator",
        "sí", "si", "snowboard",
    ]):
        return "sport"

    # ===== KERT =====
    if any(k in s for k in [
        "kert", "kerti",
        "grill",
        "fűnyíró", "funyiro",
        "locsoló", "locsolo", "slag",
        "medence", "trambulin",
        "ültető", "virágláda", "viraglada",
        "növényvédő", "novenyvedo",
    ]):
        return "kert"

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
    - cat_path: eredeti feed kategória
    - title / desc: kulcsszavas finomításra
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
