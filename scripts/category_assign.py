# category_assign.py
#
# Központi kategória-hozzárendelés partnerenként.
# Visszaadott érték: findora_main
#   elektronika, otthon, divat, jatekok, sport, kert, haztartasi_gepek,
#   allatok, konyv, auto_motor, utazas, szepseg, multi
#
# Jelenleg támogatott partnerek:
#   - tchibo
#   - alza

from typing import Optional
import unicodedata


# ==========================
#   Segédfüggvények
# ==========================

def _norm(s: str) -> str:
    """Kisbetű, ékezetek nélkül, extra space-ek nélkül."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower()
    s = " ".join(s.split())
    return s


def _norm_cat_path(cat_path: str) -> str:
    return _norm(cat_path)


def _root_segment(cat_path: str) -> str:
    """Alza-jellegű path első szegmens (pl. 'Sport, szabadidő')."""
    if not cat_path:
        return ""
    raw = cat_path.split("|", 1)[0].strip()
    return raw


# =======================================================
#   TCHIBO → FINDORA MAIN CATEGORY
#   (Ezt kérted változatlanul meghagyni.)
# =======================================================

def _tchibo_findora_main(cat_path: str) -> str:
    """
    Tchibo kategória → Findora főkategória.
    cat_path tipikus forrása:
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
    Alza kategória → Findora főkategória.
    cat_path jellegzetes formája pl.:
      "Sport, szabadidő|Kerékpározás|Kerékpár kiegészítők|Lámpák"
      "Telefon, tablet, okosóra|Mobiltelefon tartozékok|Tokok"
      "Otthon, barkács, kert|Kert|Kerti bútorok|Nyugágyak"
      stb.
    """

    raw_cat = cat_path or ""
    root = _root_segment(raw_cat)
    n_cat = _norm(raw_cat)
    n_root = _norm(root)
    n_title = _norm(title)
    n_desc = _norm(desc)
    text_all = f"{n_cat} {n_title} {n_desc}"

    # ===== SPECÁLIS KIVÉTELEK / FELÜLÍRÁSOK =====

    # 1) Állatok (állattartás, pet, kutya, macska…)
    if any(w in text_all for w in ["allattartas", "allat", "kutya", "macska", "petfood", "pet shop"]):
        return "allatok"

    # 2) Könyv
    if any(w in text_all for w in ["konyv", "regeny", "novella", "szakkonyv"]):
        return "konyv"

    # 3) Kontroller / gamepad → ELEKTRONIKA (ne menjen játékokba)
    if any(w in text_all for w in ["gamepad", "kontroller", "xbox", "playstation", "ps4", "ps5", "dualshock", "dual sense"]):
        return "elektronika"

    # 4) PC / konzol / gaming perifériák (billentyűzet, egér, headset, monitor…)
    if any(w in text_all for w in [
        "gaming es szorakozas",
        "jatekgep",
        "konzol",
        "ps5",
        "ps4",
        "xbox",
        "nintendo switch",
        "game console",
        "gaming billentyuzet",
        "gaming eger",
        "gaming headset",
    ]):
        return "elektronika"

    # 5) Háztartási kisgépek kulcsszavak (porszívó, turmix, robotgép stb.)
    if any(w in text_all for w in [
        "haztartasi kisgep",
        "mosogatogep",
        "porszivo",
        "mosogep",
        "hutogep",
        "kotogep",
        "suto",
        "mikrohullamu",
        "robotgep",
        "mixeres",
        "kavefozo",
    ]):
        return "haztartasi_gepek"

    # ===== ROOT SZEGMENS ALAPÚ LOGIKA =====

    # Sport, szabadidő
    if "sport, szabadido" in n_root:
        return "sport"

    # Telefon / tablet / okosóra → elektronika
    if "telefon, tablet, okosora" in n_root:
        return "elektronika"

    # PC és laptop → elektronika
    if "pc es laptop" in n_root:
        return "elektronika"

    # TV, fotó, audió, videó → elektronika
    if "tv, foto, audio" in n_root or "tv, foto, audio-video" in n_root:
        return "elektronika"

    # Gaming és szórakozás → elektronika (hardver + kiegészítők)
    if "gaming es szorakozas" in n_root:
        return "elektronika"

    # Játék, baba-mama → játékok
    if "jatek, baba-mama" in n_root:
        return "jatekok"

    # Otthon, barkács, kert
    if "otthon, barkacs, kert" in n_root:
        # ha "kert" / "kerti" a pathban → kert
        if any(w in n_cat for w in ["kert", "kerti", "kerti butor", "kerti szerszam"]):
            return "kert"
        # egyébként általános otthon
        return "otthon"

    # Konyha, háztartás → háztartási gépek / otthon
    if "konyha, haztartas" in n_root:
        return "haztartasi_gepek"

    # Háztartási kisgép → háztartási gépek
    if "haztartasi kisgep" in n_root:
        return "haztartasi_gepek"

    # Állattartás → állatok
    if "allattartas" in n_root:
        return "allatok"

    # Könyvek, filmek, játékok / Könyv → könyv
    if "konyv" in n_root:
        return "konyv"

    # Drogéria, Illatszer, kozmetikumok → szépség
    if "drogeria" in n_root or "illatszer" in n_root or "kozmetikumok" in n_cat:
        return "szepseg"

    # Egészségmegőrzés → szépség / health
    if "egeszsegmegorzes" in n_root:
        return "szepseg"

    # Autó-motor
    if "auto-motor" in n_root or "auto motor" in n_root:
        return "auto_motor"

    # Élelmiszer, sporttáplálék → sport / otthon
    if "sporttapanyag" in n_cat or "sporttapszerek" in n_cat or "sporttapszerek" in n_root:
        return "sport"
    if "elelmiszer" in n_root:
        return "otthon"

    # Irodai felszerelés → otthon (iroda / home office)
    if "irodai felszereles" in n_root:
        return "otthon"

    # Utazási kiegészítők / bőröndök / hátizsákok – ha root pl. "Sport, szabadidő" marad sport,
    # de ha dedikált "Utazás" root lenne, az → utazas (most csak fallback kulcsszó):
    if "utazas" in n_root:
        return "utazas"
    if any(w in n_cat for w in ["borond", "utazotaska", "utazasi kiegeszitok"]):
        # ha nem sport alatt szerepel, akkor utazás
        if "sport, szabadido" not in n_root:
            return "utazas"

    # ===== Fallback kulcsszavas besorolás, ha a root nem elég volt =====

    # Elektronika kulcsszavak
    if any(w in text_all for w in [
        "okostelefon", "mobiltelefon", "mobiltelefon tartozek",
        "laptop", "notebook", "tablet", "okosora", "monitor",
        "hangfal", "fejhallgato", "fulhallgato", "fotoapparat",
        "kamera", "projektor",
    ]):
        return "elektronika"

    # Játékok kulcsszavak (de a kontroller-eseteket már fent kivettük)
    if any(w in text_all for w in [
        "lego", "tarsasjatek", "babakocsi", "jatekbaba", "jatekkonyha",
        "jatekszett", "jatekszer",
    ]):
        return "jatekok"

    # Sport kulcsszavak
    if any(w in text_all for w in [
        "futopad", "elliptikus", "kettlebell", "sulyzo", "görgő",
        "fitness", "trambulin", "futball", "kosarlabda", "röplabda", "roplabda",
    ]):
        return "sport"

    # Kert kulcsszavak
    if any(w in text_all for w in [
        "kerti", "kerti butor", "locsolo", "onto rendszer", "novenyvedo",
        "fuves", "nyugagy", "medence", "grill",
    ]):
        return "kert"

    # Háztartási gép kulcsszavak – fallback
    if any(w in text_all for w in [
        "porszivo", "vasalo", "gofrisuto", "botmixer", "mikro",
        "kavefozo", "konyhai robotgep", "kenyerpirit", "szarnyialom",
    ]):
        return "haztartasi_gepek"

    # Otthon kulcsszavak
    if any(w in text_all for w in [
        "latogato szonyeg", "szonyeg", "fuggony", "agynemu", "plaid",
        "parna", "szek", "asztal", "komod", "szekreny", "polc",
    ]):
        return "otthon"

    # Könyv kulcsszavak fallback
    if any(w in text_all for w in ["konyv", "regeny", "szakkonyv", "album"]):
        return "konyv"

    # Állatok kulcsszavak fallback
    if any(w in text_all for w in ["allat", "kutya", "macska", "terrarium", "akvarium"]):
        return "allatok"

    # Utazás kulcsszavak fallback
    if any(w in text_all for w in ["borond", "utazotaska", "necceszer"]):
        return "utazas"

    # Szépség / kozmetikum kulcsszavak
    if any(w in text_all for w in [
        "parfum", "smink", "krem", "testapolo", "hidratlo", "dezodor",
        "szempillaspiral", "puder", "koromlakk",
    ]):
        return "szepseg"

    # Végső fallback
    return "multi"


# =======================================================
#   ÁLTALÁNOS assign_category()
# =======================================================

def assign_category(
    partner_id: str,
    cat_path: Optional[str],
    title: str = "",
    desc: str = "",
) -> str:
    """
    Központi kategória-hozzárendelés.
    - partner_id: 'tchibo', 'alza', később más partnerek
    - cat_path: eredeti feed kategória (category_path / CATEGORYTEXT stb.)
    - title / desc: kulcsszavas finomításra
    """
    pid = (partner_id or "").lower()

    # ===== TCHIBO =====
    if pid == "tchibo":
        return _tchibo_findora_main(cat_path or "")

    # ===== ALZA =====
    if pid == "alza":
        return _alza_findora_main(cat_path or "", title or "", desc or "")

    # ===== további partnerek később ide jöhetnek =====
    # if pid == "pepita":
    #     ...

    # ===== alapértelmezett =====
    return "multi"
