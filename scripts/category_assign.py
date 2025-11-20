# scripts/category_assign.py
# Egységes kategória-hozzárendelés a Findora feedekhez.

import re
from typing import Optional


def _norm(s: Optional[str]) -> str:
    if not s:
        return ""
    return str(s).strip().lower()


# ===== Partner-specifikus logika: ALZA =====

def _assign_alza(cat_path: str, title: str, desc: str) -> Optional[str]:
    """
    Alza-specifikus kategória hozzárendelés.
    A legfontosabb: Háztartási kisgép / Háztartási nagygép -> 'haztartasi'.
    """
    cat_path = _norm(cat_path)
    title = _norm(title)
    desc = _norm(desc)
    all_text = " ".join([cat_path, title, desc])

    # 1) product_type első szintje (head)
    head = cat_path.split("|", 1)[0].strip() if cat_path else ""
    head_l = head.lower()

    # --- KRITIKUS FIX: Háztartási gépek feltöltése ---
    if head_l.startswith("háztartási kisgép") or head_l.startswith("háztartási nagygép"):
        return "haztartasi"

    # 2) Egyéb főcsoportok mappingje
    # Sport
    if head_l.startswith("sport, szabadidő"):
        return "sport"

    # Elektronika
    if head_l.startswith("tv, fotó, audió, videó") or \
       head_l.startswith("tv, foto, audio-video") or \
       head_l.startswith("telefon, tablet, okosóra") or \
       head_l.startswith("pc és laptop") or \
       head_l.startswith("gaming és szórakozás") or \
       head_l.startswith("okosotthon") or \
       "notebook" in cat_path or "laptop" in cat_path:
        return "elektronika"

    # Játék
    if head_l.startswith("játék, baba-mama"):
        return "jatek"

    # Szépség / egészség
    if head_l.startswith("egészségmegőrzés") or \
       head_l.startswith("illatszer, ékszer") or \
       "kozmetika" in cat_path or "drogéria" in cat_path:
        return "szepseg"

    # Kert vs Otthon
    if head_l.startswith("otthon, barkács, kert") or \
       "dílna a zahrada" in head_l or "dílna a zahrada" in cat_path:
        # ha a teljes pathban benne van, hogy kert / kerti / grill / medence -> "kert"
        if any(k in cat_path for k in ["kert", "kerti", "grill", "medence", "locsoló", "zahrada"]):
            return "kert"
        return "otthon"

    # Autó
    if head_l.startswith("autó-motor") or head_l.startswith("auto-moto"):
        return "auto"

    # Állatok – ha a pathban vagy a szövegben állatos kulcsszavak vannak
    if any(k in all_text for k in ["kutyatáp", "macskatáp", "állateledel", "kutyahám", "póráz", "macskaalom"]):
        return "allatok"

    # Látás – optikai cuccok
    if any(k in all_text for k in ["kontaktlencse", "dioptriás", "optika", "szemüvegkeret", "napszemüveg"]):
        return "latas"

    # Háztartási gép kulcsszavak – extra biztosíték Alzára
    HAZT_KW = [
        "mosógép", "mosogatógép", "szárítógép",
        "hűtőszekrény", "hűtő", "fagyasztó",
        "mikrohullámú", "mikrosütő", "sütő",
        "tűzhely", "tűzhelyek", "porszívó",
        "robotporszívó", "gőztisztító",
        "konyhai robot", "turmixgép", "botmixer",
        "kávéfőző", "kávégép", "fritőz", "airfryer",
        "vasaló"
    ]
    if any(k in all_text for k in HAZT_KW):
        return "haztartasi"

    # Ha idáig nem találtunk semmit, ne döntsünk itt, menjen az általános logikára.
    return None


# ===== Általános (partner-független) kulcsszavas logika =====

def _assign_generic(cat_path: str, title: str, desc: str) -> str:
    cat_path = _norm(cat_path)
    title = _norm(title)
    desc = _norm(desc)
    all_text = " ".join([cat_path, title, desc])

    # 1) Direkt kulcsszavak kategóriákra

    # Háztartási gépek – általános
    if any(k in all_text for k in [
        "háztartási kisgép", "háztartási nagygép",
        "mosógép", "mosogatógép", "hűtőszekrény", "hűtő",
        "fagyasztó", "szárítógép", "mikrohullámú", "mikrosütő",
        "porszívó", "robotporszívó", "turmixgép", "konyhai robot",
        "kávéfőző", "kávégép", "airfryer", "fritőz", "vasaló"
    ]):
        return "haztartasi"

    # Elektronika
    if any(k in all_text for k in [
        "tv ", "televízió", "monitor", "laptop", "notebook",
        "pc ", "számítógép", "konzol", "xbox", "playstation", "ps4", "ps5",
        "okostelefon", "okos telefon", "mobiltelefon", "tablet",
        "router", "wifi", "ssd", "hdd", "pendrive", "usb meghajtó",
        "fejhallgató", "fülhallgató", "hangfal", "soundbar"
    ]):
        return "elektronika"

    # Játékok
    if any(k in all_text for k in [
        "játék", "játékok", "lego", "plüss", "társasjáték",
        "társas játék", "puzzle", "baba-játék", "babakocsi játék",
    ]):
        return "jatek"

    # Divat
    if any(k in all_text for k in [
        "ruha", "ruházat", "póló", "pulóver", "nadrág",
        "farmer", "szoknya", "kabát", "dzseki", "ing",
        "cipő", "csizma", "szandál", "blúz", "harisnya",
        "fehérnemű", "melltartó", "alsónadrág", "tanga", "zokni"
    ]):
        return "divat"

    # Szépség / kozmetika / egészség
    if any(k in all_text for k in [
        "kozmetikum", "krém", "arckrém", "testápoló",
        "parfüm", "illat", "smink", "rúzs", "szempillaspirál",
        "sampon", "tusfürdő", "dezodor", "hajbalzsam",
        "vitamin", "táplálékkiegészítő"
    ]):
        return "szepseg"

    # Sport
    if any(k in all_text for k in [
        "sport", "kerékpár", "bicikli", "futás", "futócipő",
        "fitnesz", "fitnesz", "edzőpad", "súlyzó", "edzés",
        "sporttáska", "sportszer"
    ]):
        return "sport"

    # Kert
    if any(k in all_text for k in [
        "kert", "kerti", "locsoló", "fűnyíró", "fűnyírás",
        "trambulin", "medence", "kerti bútor", "grill"
    ]):
        return "kert"

    # Állatok
    if any(k in all_text for k in [
        "kutya", "macska", "rágcsáló", "terrárium", "akvárium",
        "kutyatáp", "macskatáp", "állateledel", "póráz", "nyakörv",
    ]):
        return "allatok"

    # Látás / optika
    if any(k in all_text for k in [
        "kontaktlencse", "kontakt lencse", "lencse",
        "szemüvegkeret", "szemüveg keret", "napszemüveg",
        "dioptria", "optika"
    ]):
        return "latas"

    # Könyv
    if "könyv" in all_text or "regény" in all_text or "képregény" in all_text:
        return "konyv"

    # Utazás – bőrönd, hátizsák stb. (ha semmi más nem illik)
    if any(k in all_text for k in [
        "bőrönd", "utazótáska", "travel backpack", "utazó hátizsák"
    ]):
        return "utazas"

    # Ha semmi nem stimmel, akkor dobjuk "otthon"-ba
    return "otthon"


# ===== Publikus API =====

def assign_category(partner: str,
                    cat_path: Optional[str],
                    title: Optional[str],
                    desc: Optional[str]) -> str:
    """
    Fő belépési pont: partner + (product_type/category_path, title, description) -> Findora kategória ID.
    Visszatérés: 'elektronika', 'haztartasi', 'otthon', 'kert', 'jatek', 'divat', 'szepseg',
                 'sport', 'allatok', 'konyv', 'latas', 'auto', 'utazas', 'multi', stb.
    """
    partner = _norm(partner)
    cat_path = cat_path or ""
    title = title or ""
    desc = desc or ""

    # 1) Partner-specifikus logika
    if partner == "alza":
        cat = _assign_alza(cat_path, title, desc)
        if cat:
            return cat

    # 2) Általános fallback logika
    return _assign_generic(cat_path, title, desc)
