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
    "decathlon": "kat-sport",
    "onlinemarkabolt": "kat-otthon",
    "otthonmarket": "kat-otthon",
    "pepita": "kat-multi",
}

FASHION_WORDS = [
    "nadrag", "ruha", "polo", "szoknya", "kabát", "kabat", "dzseki",
    "melltarto", "fehernemu", "zokni", "cipo", "csizma", "papucs",
]

APPLIANCE_WORDS = [
    "mosogep", "mosogatogep", "szaritogep", "fagyaszto",
    "hutoszekreny", "huto", "sutogep", "tuzhely", "főzőlap", "fozőlapp", "fozolap",
    "porszivo", "robotporszivo", "mikrohullamu", "mikro",
    "kavefozo", "kavegep", "turmix", "botmixer", "konyhagep",
]

TOY_WORDS = [
    "jatek", "jatekszett", "lego", "tarsasjatek", "baba", "pluss",
]

SPORT_WORDS = [
    "futocipo", "foci", "kosarlabda", "tenisz", "sport", "edzopad",
]

VISION_WORDS = [
    "szemuveg", "napszemuveg", "kontaktlencse", "optika", "lencse",
]

HOME_WORDS = [
    "parna", "takaro", "agynemu", "lepedo", "szonyeg", "fuggony",
    "kanape", "fotel", "asztal", "szekreny", "komod", "dekoracio", "gyertya",
]

def assign_category(partner_id: str, item: dict) -> str:
    base = BASE_BY_PARTNER.get(partner_id, "kat-multi")

    text_raw = " ".join(
        str(x) for x in [
            item.get("title", ""),
            item.get("desc", ""),
            item.get("description", ""),
            item.get("category", ""),
            item.get("categoryPath", ""),
        ]
        if x
    )
    text = normalize_text(text_raw)

    def has_any(words):
        return any(w in text for w in words)

    # 1) erős jel: látás, játék, gép, divat, stb.
    if has_any(VISION_WORDS):
        return "kat-latas"
    if has_any(TOY_WORDS):
        return "kat-jatekok"
    if has_any(APPLIANCE_WORDS):
        return "kat-gepek"
    if has_any(FASHION_WORDS):
        return "kat-divat"
    if has_any(SPORT_WORDS):
        return "kat-sport"
    if has_any(HOME_WORDS):
        return "kat-otthon"

    # 2) fallback: partner alap csoport
    return base
