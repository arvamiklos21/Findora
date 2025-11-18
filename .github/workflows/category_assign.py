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
    "nadrag", "legging", "ruha", "polo", "szoknya", "kabát", "kabat",
    "dzseki", "melltarto", "fehernemu", "alsó", "also", "cipo", "csizma",
    "papucs", "pulover", "pizsama", "gyerek", "sportnadrag"
]

APPLIANCES = [
    "mosogep", "mosogatogep", "szaritogep", "fagyaszto",
    "hutoszekreny", "huto", "suto", "sutogep", "tuzhely",
    "fozolap", "főzőlap", "főzolap", "robotporszivo", "porszivo",
    "mikro", "mikrohullamu", "kavefozo", "kavegep", "turmix",
    "botmixer", "konyhagep"
]

TOYS = [
    "jatek", "jatekszett", "lego", "tarsasjatek", "baba",
    "pluss", "jarmu", "jarmű"
]

SPORT = [
    "sport", "labda", "foci", "kosar", "kosarlabda",
    "tenisz", "edzopad", "futocipo"
]

VISION = [
    "szemuveg", "szemüveg", "napszemuveg", "kontaktlencse",
    "optika", "lencse"
]

HOME = [
    "parna", "takaro", "agynemu", "lepedo", "szonyeg", "fuggony",
    "kanape", "fotel", "asztal", "szekreny", "komod",
    "dekoracio", "gyertya"
]

def assign_category(partner_id: str, item: dict) -> str:
    base = BASE_BY_PARTNER.get(partner_id, "kat-multi")

    text_src = " ".join(
        str(x) for x in [
            item.get("title", ""),
            item.get("category", ""),
            item.get("categoryPath", ""),
            item.get("desc", ""),
            item.get("description", "")
        ]
        if x
    )
    text = normalize_text(text_src)

    def has(words): return any(w in text for w in words)

    if has(VISION): return "kat-latas"
    if has(TOYS): return "kat-jatekok"
    if has(APPLIANCES): return "kat-gepek"
    if has(FASHION): return "kat-divat"
    if has(SPORT): return "kat-sport"
    if has(HOME): return "kat-otthon"

    return base
