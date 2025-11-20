# scripts/category_assign.py
#
# Egységes kategória-hozzárendelés Findora menühöz.
# Visszatérési érték mindig a menü feliratával egyező string:
#   "Elektronika", "Háztartási gépek", "Otthon", "Kert", "Játékok",
#   "Divat", "Szépség", "Sport", "Látás", "Állatok", "Könyv",
#   "Utazás", "Multi"

import unicodedata


FALLBACK_CATEGORY = "Multi"


def _norm(s: str) -> str:
    """Kisbetű, ékezet nélkül, whitespace leszedve."""
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s


def _contains_any(text: str, keywords) -> bool:
    return any(k in text for k in keywords)


def assign_category(product_type: str = "", title: str = "", description: str = "") -> str:
    """
    Egységes kategória-besorolás.
    - product_type: pl. Alza <g:product_type> első 1–2 szint
    - title / description: terméknév, leírás (ha van)
    """
    pt = _norm(product_type or "")
    txt = _norm(" ".join([product_type or "", title or "", description or ""]))

    # ==== 1. Speciális ALZA csoportok – főágak kezelése ====

    # --- Autó-motor: jelenleg menüben nincs külön autós kategória -> Multi ---
    if "auto-motor" in pt or "auto motor" in pt:
        # Ha erősen elektronika jellegű (pl. autós hűtő, autós audio), mehet Elektronikába,
        # különben Multi.
        if _contains_any(txt, ["radio", "hangfal", "fejegyse", "kamera", "dvd"]):
            return "Elektronika"
        return "Multi"

    # --- Dům, dílna a zahrada -> Otthon / Kert / Háztartási gépek ---
    if "dum, dilna a zahrada" in pt or "dum dilna a zahrada" in pt:
        if _contains_any(txt, ["zahrad", "kert", "fukasz", "nyiro", "locsolo"]):
            return "Kert"
        if _contains_any(txt, ["osvetlen", "vilagit", "lampa"]):
            return "Otthon"
        return "Otthon"

    # --- Otthon, barkács, kert ---
    if "otthon, barkacs, kert" in pt:
        if _contains_any(pt, ["kert"]):
            return "Kert"
        if _contains_any(pt, ["muhely", "szerszam", "barkacs"]):
            return "Kert"
        if _contains_any(pt, ["vilagit", "elektromos halozat", "lakberendezes"]):
            return "Otthon"
        return "Otthon"

    # --- Okosotthon ---
    if "okosotthon" in pt:
        if "smartpet" in pt or "smartpet" in txt:
            return "Állatok"
        # biztonságtechnika / okos hálózat / otthon vezérlése
        return "Otthon"

    # --- Gaming és szórakozás ---
    if "gaming es szorakozas" in pt:
        # Konzol, xbox, VR – inkább Játékok menü
        return "Játékok"

    # --- Mobilny, chytre hodinky, tablety (cseh csoport) ---
    if "mobilny, chytre hodinky, tablety" in pt:
        return "Elektronika"

    # --- PC és laptop / Počítače a notebooky ---
    if "pc es laptop" in pt or "pocitace a notebooky" in pt:
        return "Elektronika"

    # --- TV, fotó, audió, videó ---
    if "tv, foto, audio, video" in pt or "tv foto audio video" in pt:
        return "Elektronika"

    # --- Telefon, tablet, okosora ---
    if "telefon, tablet, okosora" in pt or "telefon tablet okosora" in pt:
        return "Elektronika"

    # --- Sport, szabadidő ---
    if "sport, szabadido" in pt:
        return "Sport"

    # ==== 2. Általános kulcsszavas logika – bármely partnerre működik ====

    # 2.1. Látás – optika, szemüveg, kontaktlencse
    if _contains_any(txt, ["kontaktlencse", "optika", "szemuveg", "napszemuveg", "dioptria"]):
        return "Látás"

    # 2.2. Állatok
    if _contains_any(txt, ["allateledel", "kutya", "macska", "akvarium", "terrarium", "pet", "allat"]):
        return "Állatok"

    # 2.3. Könyv
    if _contains_any(txt, ["konyv", "book", "e-book", "ebook", "regeny", "szakkonyv"]):
        return "Könyv"

    # 2.4. Játékok
    if _contains_any(txt, ["jatek", "lego", "tarsasjatek", "puzzle", "baba", "drone", "konzol", "xbox", "playstation"]):
        return "Játékok"

    # 2.5. Sport
    if _contains_any(txt, ["sport", "futocipo", "kerekpar", "bicikli", "fitnesz", "fitness", "kemping", "tura"]):
        return "Sport"

    # 2.6. Divat
    if _contains_any(
        txt,
        [
            "polo", "pulover", "nadrag", "szoknya", "ruha", "kabát", "kabát ",
            "cipo", "csizma", "melltarto", "bugyi", "tanga", "zokni", "kosztum",
            "bluz", "tunika", "kardigan", "overal"
        ],
    ):
        return "Divat"

    # 2.7. Szépség
    if _contains_any(
        txt,
        [
            "parfum", "parfüm", "smink", "borapolas", "borápolás", "dezodor",
            "sampon", "krem", "kozmetikum", "kozmetika"
        ],
    ):
        return "Szépség"

    # 2.8. Háztartási gépek
    if _contains_any(
        txt,
        [
            "mosogep", "mosogatogep", "hutoszekreny", "suto", "fozolap", "mikrohullamu",
            "porszivo", "szaritoszekreny", "fagyaszto", "kavefozo"
        ],
    ):
        return "Háztartási gépek"

    # 2.9. Otthon
    if _contains_any(
        txt,
        [
            "lampa", "vilagitas", "dekoracio", "diszparna", "fuggony", "agynemu",
            "szonyeg", "butor", "szekreny", "polc", "asztal", "szek"
        ],
    ):
        return "Otthon"

    # 2.10. Kert
    if _contains_any(
        txt,
        [
            "kert", "kerti", "locsolo", "toloalfa", "fukaszalo", "funyiro",
            "noveny", "viragfold", "zahrad"
        ],
    ):
        return "Kert"

    # 2.11. Elektronika (általános fogás)
    if _contains_any(
        txt,
        [
            "tv", "televizio", "monitor", "projektor", "laptop", "notebook",
            "tablet", "mobil", "okostelefon", "okosora", "kamera",
            "hangfal", "hangsugarzo", "fejhallgato", "fulhallgato",
            "bluetooth", "wifi", "router"
        ],
    ):
        return "Elektronika"

    # 2.12. Utazás – ha valahol fény derül rá (később bővíthető)
    if _contains_any(txt, ["utazas", "utazasi", "bőrönd", "borond", "bőrönd", "travel"]):
        return "Utazás"

    # Ha semmi nem talált:
    return FALLBACK_CATEGORY
