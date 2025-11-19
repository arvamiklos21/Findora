# scripts/category_assign.py

import unicodedata
from typing import Dict, Any


def normalize_text(s: str) -> str:
    """Szöveg normalizálása: ékezet le, kisbetű, felesleges jelek kidobása."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower()
    for ch in [".", ",", ";", ":", "!", "?", "(", ")", "[", "]", "{", "}", "/", "\\", "-", "_", "|", "\"", "'"]:
        s = s.replace(ch, " ")
    while "  " in s:
        s = s.replace("  ", " ")
    return s.strip()


# ===== Partner alapértelmezett Findora-kategória =====
BASE_BY_PARTNER: Dict[str, str] = {
    "tchibo": "kat-otthon",
    "alza": "kat-elektronika",
    "cj-eoptika": "kat-latas",
    "cj-jateknet": "kat-jatekok",
    "jateksziget": "kat-jatekok",
    "regiojatek": "kat-jatekok",
    "cj-karcher": "kat-kert",
    "onlinemarkabolt": "kat-otthon",
    "otthonmarket": "kat-otthon",
    "pepita": "kat-multi",
    "karacsonydekor": "kat-otthon",
    "kozmetikaotthon": "kat-szepseg",
    "ekszereshop": "kat-szepseg",
}


# ===== Kulcsszavak kategóriánként (globálisan, minden partnerhez) =====

FASHION = {
    "ruha", "ruhak", "szoknya", "szoknyak", "nadrag", "leggings", "farmer",
    "bluz", "ing", "polo", "polok", "pulover", "kardigan", "kabát", "kabat",
    "dzseki", "dzseki", "dzseki", "melleny", "mellény", "dzseki", "dzseki",
    "overal", "kezeslabas", "harisnya", "harisnyanadrag", "zokni", "zoknik",
    "fehernemu", "melltarto", "bugyi", "alsonemu", "alsonadrag", "alsok",
    "pizsama", "haloing", "hálóing", "haloruha", "halo nadrag",
    "gyerekruha", "gyerek kabat", "gyerek pulover", "gyerek nadrag",
    "sapka", "sapkasal", "kendo", "sal", "kesztyu", "csizma", "cipo",
    "bakancs", "szandal", "papucs", "sportcipo", "edzocipo",
    "napszemuveg", "ov", "taska", "hatizsak", "borond", "tarisznya",
    "divatkellek", "divatkiegészítő",
}

SPORT = {
    "sport", "fitnesz", "fitness", "edzotermek", "edzes", "edzocipo",
    "futocipo", "futas", "futó", "foci", "labda", "kosarlabda", "tenisz",
    "pingpong", "asztalitenisz", "kispad", "sieles", "siszett", "snowboard",
    "bukosisak", "bicikli", "kerekpar", "roller", "tura", "turabot",
    "túrazsak", "túrahátizsák", "sportmelltarto", "sportmelltartó",
    "fitnessz szalag", "sulyzo", "súlyzó", "fitnessz labda",
}

ELECTRONICS = {
    "tv", "televizio", "monitor", "laptop", "notebook", "tablet", "okostelefon",
    "telefon", "smartphone", "konzol", "playstation", "xbox", "switch",
    "jatek konzol", "kamera", "fényképező", "hangszoro", "hangsugo",
    "soundbar", "fejhallgato", "fulhallgato", "router", "wifi", "wlan",
    "szamitogep", "pc", "ssd", "hdd", "memoria kartya", "pendrive",
    "projektor", "nyomtato", "egér", "billentyu", "billentyuzet", "egerk",
}

APPLIANCES = {
    "mosogep", "mosogatogep", "hutogep", "fagyaszto", "porszivo",
    "robotporszivo", "kavefozo", "mikrohullamu", "mikrohullámu",
    "suto", "sutogep", "fozolap", "indukcios lap", "légkeveréses sütő",
    "légkondi", "klima", "klima berendezes", "paratlanito", "parologtato",
    "levegoparologtato", "légszűrő", "levegőtisztító", "mosogatogép",
}

TOYS = {
    "jatek", "jatekok", "jatekszett", "jatekkeszlet",
    "lego", "duplo", "playmobil", "barbie", "baba", "babakocsi",
    "tarsasjatek", "tarsas", "tarsasok", "kirakos", "puzzle",
    "pluss", "pluss allat", "pluss jatek", "kreativkeszlet",
    "kreativ jatek", "gyerekjatek", "fajatek", "epitojatek",
    "tarsasjatekok", "tarsasjatek-keszlet",
}

BOOKS = {
    "konyv", "konyvek", "regeny", "novella", "mesekonyv",
    "gyerekkonyv", "tankonyv", "szakkonyv", "kepregeny",
    "album", "lexikon", "szotar",
}

VISION = {
    "szemuveg", "szemuvegkeret", "szemüvegkeret",
    "napszemuveg", "kontaktlencse", "kontakt lencse",
    "lencse", "optika", "optikai",
}

BEAUTY = {
    "parfum", "parfüm", "illatszer", "smink", "sminkkeszlet",
    "puder", "alapozó", "spiral", "szempillaspiral", "szempillaspirál",
    "krem", "arckrem", "testapolo", "dezodor", "borotva", "epilo",
    "hajvasalo", "hajszaritó", "hajszarito", "hajvasalo", "fodrasz",
    "kozmetikum", "kozmetika", "szepsegapolas", "szépségápolás",
}

HOME = {
    "parna", "parnahuzat", "paplan", "agyruha", "agyruha szett",
    "takaró", "takarópléd", "pléd", "szonyeg", "fuggony", "fuggonykarnis",
    "fuggonytarto", "dohanyzoasztal", "fotel", "kanape", "kanapé",
    "szek", "asztal", "szekreny", "komod", "tarolodoboz", "doboztarolo",
    "dekoracio", "diszparna", "diszpárna", "gyertya", "fenylanc",
    "lampasor", "lampafuzer", "lampa", "fali lampa", "asztali lampa",
    "konyhai kes", "edeny", "serpenyo", "fazek", "sutotepsi",
}

GARDEN = {
    "kerti", "kert", "locsolo", "locsolotomeg", "ontozo", "onto rendszer",
    "fukasza", "funyiro", "lombszivo", "magasnyomasu", "magasnyomású",
    "karcher", "slag", "kerti szerszam", "metszoollo", "gereblye",
    "lapat", "cserep", "viragcserép", "kerti dísz", "kerti dekor",
}

PETS = {
    "kutya", "macska", "allateledel", "tap", "jutalomfalat",
    "macskalom", "kaparofa", "póráz", "nyakörv", "kutyajatek",
    "macskajatek",
}

TRAVEL = {
    "utazas", "utazás", "csomag", "szallas", "szállás", "nyaralas",
    "hotel", "repulojegy", "repulőjegy", "repülőjegy", "kemping",
    "sator", "hálózsák", "utazotaska", "bőrönd", "bortáska",
}


CATEGORY_IDS = {
    "kat-elektronika",
    "kat-gepek",
    "kat-otthon",
    "kat-kert",
    "kat-jatekok",
    "kat-divat",
    "kat-szepseg",
    "kat-sport",
    "kat-latas",
    "kat-allatok",
    "kat-konyv",
    "kat-utazas",
    "kat-multi",
}


def has_words(text: str, words: set) -> bool:
    return any(w in text for w in words)


def assign_category(partner_id: str, item: Dict[str, Any]) -> str:
    """
    Globális kategória-hozzárendelés.
    partner_id: pl. "tchibo"
    item: olyan dict, amiben legalább title / category_path / description lehet.
    """
    base = BASE_BY_PARTNER.get(partner_id, "kat-multi")

    if not isinstance(item, dict):
        return base

    parts = []
    for key in [
        "title",
        "name",
        "category",
        "categoryPath",
        "category_path",
        "product_type",
        "desc",
        "description",
    ]:
        v = item.get(key)
        if v:
            parts.append(str(v))

    text = normalize_text(" ".join(parts))
    if not text:
        return base

    # Első a nagyon egyértelműk
    if has_words(text, BOOKS):
        return "kat-konyv"
    if has_words(text, VISION):
        return "kat-latas"
    if has_words(text, TOYS):
        return "kat-jatekok"
    if has_words(text, ELECTRONICS):
        return "kat-elektronika"
    if has_words(text, APPLIANCES):
        return "kat-gepek"
    if has_words(text, SPORT):
        return "kat-sport"
    if has_words(text, FASHION):
        return "kat-divat"
    if has_words(text, BEAUTY):
        return "kat-szepseg"
    if has_words(text, PETS):
        return "kat-allatok"
    if has_words(text, GARDEN):
        return "kat-kert"
    if has_words(text, TRAVEL):
        return "kat-utazas"
    if has_words(text, HOME):
        return "kat-otthon"

    # Ha semmi nem talált, essen vissza a partner alap kategóriájára
    if base in CATEGORY_IDS:
        return base
    return "kat-multi"
