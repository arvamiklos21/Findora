# scripts/category_assign.py

import unicodedata


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower()
    for ch in [",", ".", ":", ";", "!", "?", "(", ")", "[", "]", "/", "\\", "-", "_"]:
        s = s.replace(ch, " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s.strip()


# Melyik partner alapból melyik fő kategória, ha semmi nem talál
BASE_BY_PARTNER = {
    "tchibo": "kat-otthon",
    "alza": "kat-elektronika",
    "cj-eoptika": "kat-latas",
    "cj-jateknet": "kat-jatekok",
    "jateksziget": "kat-jatekok",
    "regiojatek": "kat-jatekok",
    "onlinemarkabolt": "kat-otthon",
    "otthonmarket": "kat-otthon",
    "pepita": "kat-multi",
}

# ---- kulcsszó-listák (NEM teljesek, csak irányt mutatnak) ----

FASHION = [
    "nadrag",
    "leggings",
    "farmernadrag",
    "ruha",
    "overal",
    "overal",
    "polo",
    "póló",
    "szoknya",
    "kabat",
    "kabát",
    "dzseki",
    "dzseki",
    "melleny",
    "mellény",
    "dzsekit",
    "dzsekit",
    "melltarto",
    "melltartó",
    "fehernemu",
    "fehérnemu",
    "alsonemű",
    "alsó",
    "also",
    "bugyi",
    "alsó",
    "cipo",
    "cipő",
    "csizma",
    "bakancs",
    "papucs",
    "szandál",
    "szandal",
    "pulover",
    "pulóver",
    "pizsama",
    "hálóruha",
    "haloruha",
    "body",
    "furdoaruha",
    "furdoruha",
    "bikini",
    "zokni",
    "harisnya",
    "kesztyu",
    "kesztyű",
    "sapka",
    "sapkat",
    "sál",
    "sal",
    "kendő",
    "kendo",
    "öv",
    "ov",
]

APPLIANCES = [
    "mosogep",
    "mosógép",
    "mosogatogep",
    "mosogatógép",
    "szaritogep",
    "szárítógép",
    "fagyaszto",
    "fagyasztó",
    "hutoszekreny",
    "hűtőszekrény",
    "huto",
    "hűtő",
    "sutogep",
    "sütő",
    "tuzehely",
    "tűzhely",
    "fozolap",
    "főzőlap",
    "robotgep",
    "robotgép",
    "robotporszivo",
    "robotporszívó",
    "porszivo",
    "porszívó",
    "mikrohullamu",
    "mikrohullámu",
    "mikro",
    "kavefozo",
    "kávéfőző",
    "kavegep",
    "kávégép",
    "turmix",
]

TOYS = [
    "jatek",
    "játék",
    "jatekszett",
    "játékszett",
    "jatekszorakoztato",
    "játékszórakoztató",
    "jatekfigura",
    "játékfigura",
    "jatekauto",
    "játékauto",
    "jatekkonyha",
    "játékkonyha",
    "lego",
    "tarsasjatek",
    "társasjáték",
    "tarsas",
    "társas",
    "kirako",
    "kirakó",
    "puzzle",
    "kirakos",
    "kirakós",
    "baba",
    "babakocsi",
    "pluss",
    "plüss",
]

SPORT = [
    "futocipo",
    "futócipő",
    "futás",
    "edzocipo",
    "futó",
    "labda",
    "foci",
    "kosar",
    "kosárlabda",
    "tenisz",
    "edzopolo",
    "edzőpóló",
    "futodzseki",
]

VISION = [
    "szemuveg",
    "szemüveg",
    "napszemuveg",
    "napszemüveg",
    "kontaktlencse",
    "lencse",
]

HOME = [
    "parna",
    "párna",
    "takaro",
    "takaró",
    "agyynemu",
    "ágynemű",
    "lepedo",
    "lepedő",
    "szonyeg",
    "szőnyeg",
    "fuggony",
    "függöny",
    "kanape",
    "kanapé",
    "fotel",
    "asztal",
    "szekreny",
    "szekrény",
    "komod",
    "komód",
    "dekoracio",
    "dekoráció",
    "gyertya",
    "polc",
    "asztalka",
    "szenyestartó",
]

ELECTRONICS = [
    "tv",
    "televizio",
    "televízió",
    "monitor",
    "laptop",
    "tablet",
    "telefon",
    "okostelefon",
    "konzol",
    "playstation",
    "ps5",
    "xbox",
    "hangfal",
    "hangszoro",
    "hangszóró",
    "soundbar",
    "headset",
    "fulhallgato",
    "fülhallgató",
    "kamera",
    "fenykepezogep",
    "fényképezőgép",
    "router",
    "nyomtato",
    "nyomtató",
    "projektor",
]

BOOKS = [
    "konyv",
    "könyv",
    "regeny",
    "regény",
    "roman",
    "novella",
    "tankonyv",
    "mesekonyv",
    "gyerekkonyv",
    "képregény",
    "kepregeny",
]


def has_any(text: str, words) -> bool:
    return any(w in text for w in words)


def assign_category(partner_id: str, item: dict) -> str:
    """
    Egységes Findora fő kategória meghatározása egy termékre.
    Első a ruha vs játék ütközés kezelése, utána háztartási gép, elektronika, stb.
    """
    base = BASE_BY_PARTNER.get(partner_id, "kat-multi")

    title = (item.get("title") or "") + " " + (item.get("name") or "")
    category_path = (
        item.get("categoryPath")
        or item.get("category_path")
        or item.get("category")
        or ""
    )
    description = item.get("desc") or item.get("description") or ""

    text_all = normalize_text(" ".join([title, category_path, description]))
    text_title = normalize_text(title)

    if not text_all:
        return base

    # Jelzők
    has_fashion = has_any(text_title, FASHION) or has_any(text_all, FASHION)
    has_toys = has_any(text_title, TOYS) or (
        "jatek" in text_all or "játék" in text_all
    )
    has_appl = has_any(text_all, APPLIANCES)
    has_elec = has_any(text_all, ELECTRONICS)
    has_sport = has_any(text_all, SPORT)
    has_vision = has_any(text_all, VISION)
    has_home = has_any(text_all, HOME)
    has_books = has_any(text_all, BOOKS)

    # 1) Ruházat mindig fontosabb, mint játék – ha kabát / nadrág / leggings stb. szerepel,
    #    akkor DIVAT, még ha a Tchibo kategória fában van is "játék" szó.
    if has_fashion:
        return "kat-divat"

    # 2) Játék – csak akkor, ha nincs erős ellentmondó jel (pl. elektronika / háztartási gép)
    if has_toys and not has_appl and not has_elec:
        return "kat-jatekok"

    # 3) Háztartási gépek
    if has_appl:
        return "kat-gepek"

    # 4) Elektronika
    if has_elec:
        return "kat-elektronika"

    # 5) Sport
    if has_sport:
        return "kat-sport"

    # 6) Látás (szemüveg, lencse)
    if has_vision:
        return "kat-latas"

    # 7) Könyv
    if has_books:
        return "kat-konyv"

    # 8) Otthon/bútor
    if has_home:
        return "kat-otthon"

    # 9) Ha semmi nem talált, menjen a partner-alapértelmezett kategóriába
    return base
