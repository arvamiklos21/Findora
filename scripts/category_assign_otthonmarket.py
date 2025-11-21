# category_assign_otthonmarket.py
"""
Kategória-besoroló Otthon Market termékekhez.

Bemenet: XML mezők (category, name, description)
Kimenet: Findora fő kategória ID (pl. "kat-otthon", "kat-kert", stb.)
"""

# ===== Findora kategória ID-k =====
KAT_ELEK = "kat-elektronika"
KAT_GEPEK = "kat-gepek"
KAT_OTTHON = "kat-otthon"
KAT_JATEK = "kat-jatekok"
KAT_DIVAT = "kat-divat"
KAT_SZEPSEG = "kat-szepseg"
KAT_SPORT = "kat-sport"
KAT_KONYV = "kat-konyv"
KAT_ALLAT = "kat-allatok"
KAT_LATAS = "kat-latas"
KAT_MULTI = "kat-multi"
KAT_KERT = "kat-kert"
KAT_UTAZAS = "kat-utazas"


def _norm(s: str) -> str:
    """Egyszerű normalizálás: lower + strip."""
    return (s or "").strip().lower()


def assign_category(category: str, name: str = "", description: str = "") -> str:
    """
    Otthon Market termékek Findora fő kategória besorolása.

    Paraméterek:
      - category: XML <category> mező (pl. "Bútorok / Asztalok / ...")
      - name:     XML <name> mező (terméknév)
      - description: XML <description> (ha kell plusz kulcsszóhoz)

    Visszatérés:
      - "kat-otthon", "kat-kert", "kat-gepek", stb.
    """
    cat = _norm(category)
    title = _norm(name)
    desc = _norm(description)

    # Összefűzött szöveg, hogy cím/leírás alapján is tudjunk dönteni
    text = " ".join(t for t in [cat, title, desc] if t)

    # ===== 1. Erős, egyértelmű kategóriák =====

    # Játékok
    if "játék" in text or "játékszer" in text or "játékok" in text:
        return KAT_JATEK

    # Állatok
    if "állat" in text or "kutya" in text or "macska" in text or "terrárium" in text:
        return KAT_ALLAT

    # Könyv
    if "könyv" in text or "könyvek" in text:
        return KAT_KONYV

    # Sport / fitnesz cuccok
    if (
        "sport" in text
        or "fitnesz" in text
        or "fitness" in text
        or "edzés" in text
    ):
        return KAT_SPORT

    # Divat / ruházat / cipő
    if any(
        w in text
        for w in [
            "ruházat",
            "ruha ",
            "ruha,",
            "ruha.",
            "kabát",
            "dzseki",
            "kabátok",
            "pulóver",
            "póló",
            "polo",
            "nadrág",
            "leggings",
            "szoknya",
            "cipő",
            "csizma",
            "szandál",
            "papucs",
            "ing",
            "blúz",
            "melltartó",
            "fehérnemű",
        ]
    ):
        return KAT_DIVAT

    # Szépség / kozmetika
    if any(
        w in text
        for w in [
            "kozmetika",
            "kozmetikum",
            "kozmetikumok",
            "smink",
            "szempillaspirál",
            "rúzs",
            "parfüm",
            "parfum",
            "dezodor",
            "szépségápolás",
            "bőrápolás",
            "bőrápoló",
            "sampon",
            "hajbalzsam",
            "tusfürdő",
        ]
    ):
        return KAT_SZEPSEG

    # Látás (ha lenne szemüveg, kontaktlencse, stb.)
    if any(
        w in text
        for w in [
            "szemüveg",
            "szemuveg",
            "lencse",
            "kontaktlencse",
        ]
    ):
        return KAT_LATAS

    # Utazás – bőrönd, utazótáska, stb.
    if any(
        w in text
        for w in [
            "bőrönd",
            "borond",
            "utazótáska",
            "utazotaska",
            "utazó táska",
            "utazó",
            "travel",
        ]
    ):
        return KAT_UTAZAS

    # ===== 2. Elektronika vs háztartási gépek =====

    # Háztartási gépek
    if any(
        w in text
        for w in [
            "mosógép",
            "mosogep",
            "mosogatógép",
            "mosogatogep",
            "hűtőszekrény",
            "hűtő",
            "huto",
            "fagyasztó",
            "fagyaszto",
            "sütő",
            "sutő",
            "mikrohullámú",
            "mikrohullamu",
            "porszívó",
            "porszivo",
            "gőztisztító",
            "goztisztito",
            "háztartási gép",
            "haztartasi gep",
        ]
    ):
        return KAT_GEPEK

    # Elektronika – tv, monitor, pc, laptop, konzol, audio stb.
    if any(
        w in text
        for w in [
            "tv",
            "televízió",
            "televizio",
            "monitor",
            "laptop",
            "notebook",
            "tablet",
            "okostelefon",
            "telefon",
            "konzol",
            "ps5",
            "playstation",
            "xbox",
            "játék konzol",
            "pc ",
            "pc-",
            "pc.",
            "hangszóró",
            "hangszoro",
            "soundbar",
            "hangfal",
        ]
    ):
        return KAT_ELEK

    # ===== 3. Kert / kültéri dolgok =====
    if any(
        w in text
        for w in [
            "kerti",
            "kert ",
            "kert,",
            "kert.",
            "kültéri",
            "kulteri",
            "grill",
            "medence",
            "napernyő",
            "napernyo",
            "kerti bútor",
            "kerti szék",
            "kerti asztal",
            "kerti pad",
        ]
    ):
        return KAT_KERT

    # ===== 4. Bútor, tárolás, otthon =====
    # Ezekből a példákból is látszik:
    # - "Bútorok / Asztalok / Asztalkák / Kisasztalok"
    # - "Bútorok / Szekrények és tárolók / Tárolók és zárható szekrények"
    # - "Bútorok / Szórakoztató központok és tévéállványok"
    if any(
        w in text
        for w in [
            "bútorok",
            "bútor",
            "butor",
            "szekrény",
            "szekreny",
            "tároló",
            "tarolo",
            "tárolók",
            "komód",
            "komod",
            "asztal",
            "asztalok",
            "kisasztal",
            "kanapé",
            "kanape",
            "fotel",
            "szék",
            "szek",
            "székek",
            "polc",
            "könyvespolc",
            "konyvespolc",
            "tálalóasztal",
            "tv-állvány",
            "tévéállvány",
            "teveallvany",
            "szórakoztató központ",
            "szorakoztato kozpont",
            "monitorállvány",
            "monitorallvany",
        ]
    ):
        return KAT_OTTHON

    # ===== 5. Fallback =====
    # Otthon Market alap profilja lakberendezés/bútor,
    # ezért ha semmi nem fogta meg, biztonságos fallback az otthon.
    return KAT_OTTHON


if __name__ == "__main__":
    # Egyszerű teszt – hogy lásd, mit ad vissza
    samples = [
        ("Bútorok / Asztalok / Asztalkák / Kisasztalok", "2 db tömör mangófa kisasztal", ""),
        ("Bútorok / Szekrények és tárolók / Tárolók és zárható szekrények", "Fehér acél nyeregszekrény 53 x 53 x 140 cm", ""),
        ("Bútorok / Szórakoztató központok és tévéállványok", "Tömör fenyőfa monitorállvány 100 x 27 x 15 cm", ""),
    ]

    for cat, name, desc in samples:
        print(name, "→", assign_category(cat, name, desc))
