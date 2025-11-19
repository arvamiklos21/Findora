# scripts/category_assign.py

import unicodedata

def normalize_text(s: str) -> str:
    """Egyszerű normalizálás: kisbetű, ékezet nélkül, felesleges whitespace nélkül."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    # dobjuk a kombináló ékezeteket
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower()
    for ch in [".", ",", ":", ";", "!", "?", "(", ")", "[", "]", "/", "\\", "-", "_", "–"]:
        s = s.replace(ch, " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s.strip()


# Alap kategória partner szerint (ha semmi kulcsszó nem talál)
BASE_BY_PARTNER = {
    "tchibo": "kat-otthon",
    "alza": "kat-elektronika",
    "eoptika": "kat-latas",
    "cj-eoptika": "kat-latas",
    "cj-jateknet": "kat-jatekok",
    "jateksziget": "kat-jatekok",
    "regiojatek": "kat-jatekok",
    "onlinemarkabolt": "kat-otthon",
    "otthonmarket": "kat-otthon",
    "pepita": "kat-multi",
}

# Kulcsszó-listák – szabadon bővíthetők később
FASHION = [
    "nadrag",
    "leggings",
    "ruha",
    "polo",
    "szoknya",
    "kabat",
    "kabát",
    "dzseki",
    "melltarto",
    "fehernemu",
    "fehérnemu",
    "also",
    "alsó",
    "cipo",
    "cipő",
    "csizma",
    "papucs",
    "pulover",
    "pulóver",
    "pizsama",
    "gyerek",
    "sportnadrag",
    "kendo",
    "kendő",
    "kesztyu",
    "kesztyű",
]

APPLIANCES = [
    "mosogep",
    "mosógép",
    "mosogatogep",
    "szaritogep",
    "szárítógép",
    "fagyaszto",
    "fagyasztó",
    "hutoszekreny",
    "hűtőszekrény",
    "huto",
    "hűtő",
    "suto",
    "sütő",
    "tuzhely",
    "tűzhely",
    "kifozolap",
    "főzőlapp",
    "főzőlapp",
    "fozolap",
    "robotporszivó",
    "robotporszivo",
    "porszivo",
    "porszívó",
    "mikrohullamu",
    "mikrohullámu",
    "kavefozo",
    "kávéfőző",
    "kavegep",
    "kávégép",
    "turmix",
    "botmixer",
    "konyhagep",
    "konyhagé",
]

TOYS = [
    "jatek",
    "játék",
    "jatekszett",
    "játékszett",
    "lego",
    "tarsasjatek",
    "társasjáték",
    "baba",
    "pluss",
    "plüss",
    "jarmu",
    "jármű",
    "jarmu",
]

SPORT = [
    "futópad",
    "futopad",
    "labda",
    "foci",
    "kosar",
    "kosárlabda",
    "tenisz",
    "edzopad",
    "edzőpad",
    "futocipo",
    "futócipő",
]

VISION = [
    "szemuveg",
    "szemüveg",
    "napszemuveg",
    "napszemüveg",
    "kontaktlencse",
    "optika",
    "lencse",
]

HOME = [
    "parna",
    "párna",
    "takaro",
    "takaró",
    "agyynemu",
    "agyynemű",
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
    "asztalk",
    "szek",
    "szék",
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
    "fenykepezo",
    "fényképező",
    "router",
    "nyomtato",
    "nyomtató",
    "projektor",
]

BOOKS = [
    "konyv",
    "könyv",
    "konyvek",
    "könyvek",
    "regeny",
    "regény",
    "roman",
    "novella",
    "tankonyv",
    "tankönyv",
    "mesekonyv",
    "mesekönyv",
    "gyerekkonyv",
    "gyerekkönyv",
    "kepregeny",
    "képregény",
]


def assign_category(partner_id: str, item: dict) -> str:
    """
    Partner + termék szövege alapján Findora kategória ID-t ad vissza (pl. 'kat-jatekok').
    item: dict – ugyanaz a struktúra, amit a feed-ben is használunk (title, desc, categoryPath, description…).
    """
    base = BASE_BY_PARTNER.get(partner_id, "kat-multi")

    # mindent egy nagy szövegbe: title + category + categoryPath + desc + description
    text_src = " ".join(
        str(x)
        for x in [
            item.get("title", ""),
            item.get("category", ""),
            item.get("categoryPath", ""),
            item.get("desc", ""),
            item.get("description", ""),
        ]
        if x is not None
    )

    text = normalize_text(text_src)

    def has(words):
        return any(w in text for w in words)

    # Ha nincs szöveg, menjen az alap partner-kategória
    if not text:
        return base

    # 1) játékok
    if has(TOYS):
        return "kat-jatekok"

    # 2) háztartási gépek
    if has(APPLIANCES):
        return "kat-gepek"

    # 3) elektronika
    if has(ELECTRONICS):
        return "kat-elektronika"

    # 4) divat
    if has(FASHION):
        return "kat-divat"

    # 5) sport
    if has(SPORT):
        return "kat-sport"

    # 6) látás / optika
    if has(VISION):
        return "kat-latas"

    # 7) otthon
    if has(HOME):
        return "kat-otthon"

    # 8) könyv
    if has(BOOKS):
        return "kat-konyv"

    # Ha egyik sem, akkor partner alap kategória, vagy multi
    return base
