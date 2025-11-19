# scripts/category_assign.py

import unicodedata

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower()
    for ch in [".", ",", ";", ":", "!", "?", "(", ")", "[", "]", "/", "\\", "-", "_"]:
        s = s.replace(ch, " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s.strip()

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

FASHION = [
    "nadrag", "legging", "ruha", "polo", "szoknya", "kabat",
    "dzseki", "melltarto", "fehernemu", "also", "cipo", "csizma",
    "papucs", "pulover", "pizsama", "gyerek", "sportnadrag",
    "kendo", "kesztyu",
]

APPLIANCES = [
    "mosogep", "mosogatogep", "szaritogep", "fagyaszto",
    "hutoszekreny", "huto", "suto", "sutogep", "tuzhely",
    "fozolap", "robotporszivo", "porszivo",
    "mikro", "mikrohullamu", "kavefozo", "kavegep", "turmix",
    "botmixer", "konyhagep",
]

TOYS = [
    "jatek", "jatekszett", "lego", "tarsasjatek", "tarsas",
    "baba", "pluss", "jarmu", "jatekauto", "autopalya",
]

SPORT = [
    "sport", "labda", "foci", "football", "kosar", "kosarlabda",
    "tenisz", "edzopad", "futogep", "futocipo", "kondigep",
]

VISION = [
    "szemuveg", "napszemuveg", "kontaktlencse",
    "optika", "lencse", "olvasoszemuveg",
]

HOME = [
    "parna", "takaro", "agynemu", "lepedo", "szonyeg", "fuggony",
    "kanape", "fotel", "asztal", "szekreny", "komod",
    "dekoracio", "gyertya", "polc", "disztargy", "vaza",
]

ELECTRONICS = [
    # fo termekcsoportok
    "tv", "televizio", "monitor",
    "laptop", "notebook", "tablet", "okostelefon",
    "telefon", "smartphone", "okos telefon",

    # konzol / gaming
    "konzol", "playstation", "ps4", "ps5",
    "xbox", "nintendo", "switch", "jatekgep",

    # hang / audio
    "hangfal", "hangszoro", "bluetooth hangszoro", "soundbar",
    "fejhallgato", "headset", "fulhallgato",

    # kamera / foto
    "kamera", "fenykepezo", "action camera", "gopro",
    "webkamera",

    # szamtech / halozat
    "router", "wifi router", "mesh", "modem",
    "hdd", "ssd", "memoriakartya",
    "nyomtato", "szkenner", "scanner",
    "projektor",

    # okoseszkozok
    "okosora", "fitneszora", "fitnesz ora",
    "fitneszkarkoto", "fitnesz karkoto", "activity tracker",
]

BOOKS = [
    "konyv", "konyvek",
    "regeny", "roman", "novella",
    "szakkonyv", "tankonyv",
    "kepregeny",
    "mesekonyv", "gyerekkonyv",
    "ifjusagi konyv", "ifjusagi",
    "verseskotet",
    "album", "lexikon", "enciklopedia",
]


def assign_category(partner_id: str, item: dict) -> str:
    """
    Visszaad egy frontend kategória ID-t (kat-...), ha találunk mintát,
    különben a partner-alapú base kategóriát.
    """
    base = BASE_BY_PARTNER.get(partner_id, "kat-multi")

    text_src = " ".join(
        str(x)
        for x in [
            item.get("title", ""),
            item.get("category", ""),
            item.get("categoryPath", ""),
            item.get("desc", ""),
            item.get("description", ""),
        ]
        if x
    )
    text = normalize_text(text_src)

    def has(words): 
        return any(w in text for w in words)

    # sorrend: ahol legbiztosabb a találat
    if has(VISION):
        return "kat-latas"
    if has(TOYS):
        return "kat-jatekok"
    if has(ELECTRONICS):
        return "kat-elektronika"
    if has(APPLIANCES):
        return "kat-gepek"
    if has(FASHION):
        return "kat-divat"
    if has(SPORT):
        return "kat-sport"
    if has(HOME):
        return "kat-otthon"
    if has(BOOKS):
        return "kat-konyv"

    # ha semmi nem talál, marad a partner-alapú default
    return base
