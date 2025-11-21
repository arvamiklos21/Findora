# scripts/category_assign_pepita.py
import re

# ===== Findora kategória ID-k =====
KAT_ELEK    = "kat-elektronika"
KAT_GEPEK   = "kat-gepek"
KAT_OTTHON  = "kat-otthon"
KAT_JATEK   = "kat-jatekok"
KAT_DIVAT   = "kat-divat"
KAT_SZEPSEG = "kat-szepseg"
KAT_SPORT   = "kat-sport"
KAT_KONYV   = "kat-konyv"
KAT_ALLAT   = "kat-allatok"
KAT_LATAS   = "kat-latas"
KAT_MULTI   = "kat-multi"


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _root_from_cat(cat: str) -> str:
    """
    Pepita <category> pl:
      - 'Szépség & Egészség > Testápolás & Higiénia > Intim higiénia > Óvszerek'
      - 'Otthon & Kert > Konyha & Étkezés > Főzőedények & Sütőedények > Edénykészletek'
      - 'Babák & Tipegők > Babaszoba > Zenélő forgók, vetítő forgók'
      - 'Játékok > Kreatív játékok & Fejlesztő játékok > Fejlesztő játékok babáknak'
    Mi csak az első szintet nézzük.
    """
    if not cat:
        return ""
    root = cat.split(">")[0].split("/")[0]
    return root.strip().lower()


def assign_category(cat_path: str, title: str = "", desc: str = "") -> str:
    """
    Pepita fő Findora-kategória hozzárendelése:
      - Szépség & Egészség  → kat-szepseg
      - Otthon & Kert       → kat-otthon
      - Babák & Tipegők     → kat-jatekok (baba cuccok → játék/baba világ)
      - Játékok             → kat-jatekok
      - egyéb esetben kulcsszavak alapján, végül kat-multi
    """
    cat_path = cat_path or ""
    title = title or ""
    desc = desc or ""

    root = _root_from_cat(cat_path)
    text = _norm(title + " " + desc)
    cat_low = _norm(cat_path)

    # --- 1. Root alapú döntés ---

    # Szépség & Egészség → szépség
    if "szépség" in root or "szepseg" in root:
        return KAT_SZEPSEG

    # Otthon & Kert → otthon
    if "otthon" in root or "kert" in root:
        return KAT_OTTHON

    # Babák & Tipegők → baba / játék világ
    if "babák" in root or "babak" in root or "tipegők" in root or "tipegok" in root:
        return KAT_JATEK

    # Játékok → játék
    if "játékok" in root or "jatekok" in root:
        return KAT_JATEK

    # Ha a root nem egyértelmű, de a path utal rá:
    if "babaszoba" in cat_low or "babajáték" in cat_low or "baba játék" in cat_low:
        return KAT_JATEK

    if "mosás" in cat_low or "mososzerek" in cat_low or "háztartási kellékek" in cat_low:
        return KAT_OTTHON

    # --- 2. Kulcsszavas finomítás ---

    # Intim cuccok, óvszer, szőrtelenítés → szépség / testápolás
    if any(k in text for k in (
        "óvszer", "ovszer", "intim higiénia", "intim higienia",
        "szőrtelenítő", "szortelenito", "gyanta", "borotva"
    )):
        return KAT_SZEPSEG

    # Mosás, tisztítószer → otthon
    if any(k in text for k in (
        "mosószer", "mososzer", "folteltávolító", "folttisztito",
        "fehérítő por", "feheritő", "tisztító", "tisztitoszer"
    )):
        return KAT_OTTHON

    # Konyhai edény, serpenyő, edénykészlet → otthon
    if any(k in text for k in (
        "serpenyő", "serpenyo", "edénykészlet", "edenykeszlet",
        "lábas", "labas", "főzőedény", "fozoedeny", "konyha"
    )):
        return KAT_OTTHON

    # Baba / gyerek cuccok → játék
    if any(k in text for k in (
        "baba", "babab", "pocakpárna", "pocakparna",
        "zenélő forgó", "zenelo forgo", "etetőszék", "etetoszek",
        "bili", "gyermek wc", "gyermek wc"
    )):
        return KAT_JATEK

    # Ha explicit "játék" szó benne van a névben/leírásban
    if "játék" in text or "jatek" in text:
        return KAT_JATEK

    # --- 3. Végső fallback ---
    return KAT_MULTI
