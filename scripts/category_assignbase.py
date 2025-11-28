# scripts/category_assign_base.py
#
# Egyszerű, univerzális kategória-besoroló minden partnernek.
#
# LOGIKA:
#   - cím + leírás + kategória mező + brand alapján kulcsszavas pontozás
#   - a legmagasabb pontszámú kategória nyer
#   - ha semmi nem talál (minden 0 pont), akkor:
#       1) ha van partner_default (pl. jatekok), azt adja vissza
#       2) különben 'multi'
#
# Használat partner scriptekben:
#
#   from category_assign_base import assign_category
#
#   cat = assign_category(
#       title=title,
#       desc=description,
#       category_path=cat_path,
#       brand=brand,
#       partner="jateksziget",        # opcionális
#       partner_default=None          # opcionális – ha None, partner alapján próbál tippelni
#   )

import re
import unicodedata

# 25 Findora fő kategória
FINDORA_CATS = [
    "elektronika",
    "haztartasi_gepek",
    "szamitastechnika",
    "mobil",
    "gaming",
    "smart_home",
    "otthon",
    "lakberendezes",
    "konyha_fozes",
    "kert",
    "jatekok",
    "divat",
    "szepseg",
    "drogeria",
    "baba",
    "sport",
    "egeszseg",
    "latas",
    "allatok",
    "konyv",
    "utazas",
    "iroda_iskola",
    "szerszam_barkacs",
    "auto_motor",
    "multi",
]

# Partner → alap kategória fallback
# Ha nem találunk semmilyen kulcsszót, erre esik vissza.
PARTNER_DEFAULTS = {
    # Játékos boltok
    "jateksziget": "jatekok",
    "regiojatek": "jatekok",
    "jateknet": "jatekok",
    "jatekshop": "jatekok",

    # Tchibo – főleg otthon/lakás, ruha
    "tchibo": "otthon",

    # Pepita sok minden – maradhat multi
    "pepita": "multi",

    # Alza: vegyes, hagyjuk multi-n
    "alza": "multi",
}


def _normalize_text(text: str) -> str:
    """
    Kisbetű, ékezetmentesítés, extra whitespace eltávolítása.
    """
    if not text:
        return ""
    t = str(text)
    t = t.lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")  # ékezetmentes
    t = re.sub(r"\s+", " ", t).strip()
    return t


# Alap kulcsszó-lista kategóriákhoz.
# Ezt később bármikor bővíthetjük, finomíthatjuk.
CATEGORY_KEYWORDS = {
    "elektronika": [
        "tv", "televizio", "televizor", "hangfal", "hangszoro", "hifi",
        "projektor", "erősítő", "erosito", "radio", "bluetooth hangszoro",
        "dron", "videojatek konzol", "soundbar",
    ],
    "haztartasi_gepek": [
        "porszivo", "mosogep", "mosogatogep", "hutogep", "mikrohullamu",
        "mikro", "parologtato", "levegoparologtato", "klima", "futotest",
        "kapszulas kavefozo", "kavefozo", "vasalo", "botmixer", "turmix",
        "konyhai robotgep", "szeletelo", "levegofritozo", "fritoz",
    ],
    "szamitastechnika": [
        "laptop", "notebook", "pc", "szamitogep", "asztali gep", "monitor",
        "bilentyuzet", "eger", "ssd", "merevlemez", "hard drive",
        "videokartya", "grafikus kartya", "router", "switch", "nas",
        "webkamera", "dokkolo allomas",
    ],
    "mobil": [
        "okostelefon", "okos telefon", "smartphone", "mobiltelefon",
        "telefon tok", "telefon tok", "screen protector", "kijelzovedo",
        "powerbank", "vezetek nelkuli tolto", "autostarto" ,
    ],
    "gaming": [
        "gamer", "gaming", "jatek konzol", "playstation", "xbox", "nintendo",
        "gaming szek", "gamer szek", "gaming eger", "gamer eger",
        "gaming billentyuzet", "gamer billentyuzet",
    ],
    "smart_home": [
        "okos izzo", "okosizzó", "okos dugalj", "okos konnektor",
        "okos otthon", "smart home", "wifi kamera", "ip kamera",
        "kamera rendszer", "biztonsagi kamera", "termosztat okos",
    ],
    "otthon": [
        "dekoracio", "dekoracio", "fuggony", "parna", "takaro", "paplan",
        "agyruha", "szonyeg", "fali ora", "fali dekor", "lampa",
        "asztali lampa", "allolampa", "lakberendezesi targy",
    ],
    "lakberendezes": [
        "kanape", "fotel", "szek", "asztal", "konyhaszekreny", "komod",
        "szekreny", "polc", "butor", "gardrob", "agykeret", "elo szoba butor",
    ],
    "konyha_fozes": [
        "edeny", "fazek", "labas", "serpenyo", "tepsi", "sutotál",
        "sutotal", "vago deszka", "keskeszlet", "konyhai kes",
        "merokanna", "kavecsesze", "tányér", "tanyer", "konyhai kiegészítő",
    ],
    "kert": [
        "fukosza", "fukaszalo", "fuvago", "funyiro", "lancfuresz",
        "agvago", "ontozorendszer", "locsolotomeg", "kerti szerszam",
        "kerti butor", "trampolin", "trambulin", "medence", "napernyo",
        "kerti grill", "grillsuto", "kerti haz", "kerti tarolo",
    ],
    "jatekok": [
        "jatekszett", "tarsasjatek", "tarsas", "lego", "playmobil",
        "barbibaba", "baba jatek", "jatekbaba", "kartyajatek",
        "kirako", "puzzle", "tarsasjatek", "baby jatek", "pluss jatek",
        "jatek figura", "jatekvonat", "jatekkonyha", "jatekgari",
    ],
    "divat": [
        "polo", "poloing", "nadrag", "farmer", "szoknya", "ruha",
        "pulover", "kapucnis", "dzseki", "kabat", "zako", "cipő",
        "cipo", "csizma", "szandál", "szandal", "papucs", "taska",
        "hatizsak", "oldaltaska", "penztarca", "ov", "kesztyu",
        "sapka", "sál", "sal",
    ],
    "szepseg": [
        "parfum", "parfüm", "dezodor", "smink", "alapozó", "alapozo",
        "szempillaspiral", "szempilla spirál", "ruzs", "szajfeny",
        "borapolas", "hajapolo", "sampon", "kondicionalo", "hajfixalo",
        "kozmetikum", "kozmetikai szer",
    ],
    "drogeria": [
        "mosopor", "mososzer", "oblito", "tisztitoszer", "fertotlenito",
        "wc tisztito", "zsebkendo", "papirzsebkendo", "toalettpapir",
        "szalveta", "mosogatoszer", "mosogatotabletta",
    ],
    "baba": [
        "pelenka", "bepantos pelenka", "babaapolo", "baba apolo",
        "babaolaj", "babakrem", "baba krem", "kismama", "eteto szek",
        "hordozo", "babakocsi", "jaroka", "baba ruhazat", "babaruha",
        "cumisuveg", "cumi", "baba jatek",
    ],
    "sport": [
        "futocipo", "edzocipo", "fitnesz", "edzopad", "sulyzo",
        "kettlebell", "futopad", "kerekpar", "bicikli", "roller",
        "focilabda", "kosarlabda", "edzoruha", "melegito", "sportmelltarto",
    ],
    "egeszseg": [
        "vitamin", "taplalekkiegeszito", "taplalek kiegeszito",
        "vernyomasmero", "lazmero", "inhalator", "maszk", "fogyokuras",
        "gyogyaszati", "csuklotamasz", "hatmasziro", "massziro",
    ],
    "latas": [
        "kontaktlencse", "napi lencse", "heti lencse", "havi lencse",
        "optikai", "szemuvegkeret", "szemuveg keret", "napszemuveg",
        "lencseapolo", "lencse folyadek", "kontaktlencse folyadek",
    ],
    "allatok": [
        "kutyatap", "macskatap", "allateledel", "allat eledel",
        "macskaalom", "kutya fekhely", "macska fekhely", "póráz",
        "poraz", "nyakörv", "nyakorv", "kaparofa", "akvarium",
        "terrarium", "hazallat",
    ],
    "konyv": [
        "regeny", "szakkonyv", "szak konyv", "gyerekkonyv", "mese konyv",
        "kifesto", "album", "konyvsorozat", "novellaskotet",
    ],
    "utazas": [
        "borond", "bőrönd", "utazotaska", "utazo taska", "utazo parna",
        "utazasi szett", "borton cimke", "bőrönd cimke",
    ],
    "iroda_iskola": [
        "tolltarto", "fuzet", "spiralfuzet", "spiral fuzet", "toll",
        "ceruza", "radir", "filctoll", "markero", "irodai szek",
        "iroasztal", "nyomtatopapir", "post it", "irattarto",
    ],
    "szerszam_barkacs": [
        "csavarozo", "furogep", "akkus furo", "flex", "sarokcsiszolo",
        "csiszologep", "kalapacs", "csavarhuzo", "keszlet szerszam",
        "fogó", "fogo", "lemezvago", "villaskulcs",
    ],
    "auto_motor": [
        "motorolaj", "motor olaj", "autogumi", "teligumi", "nyarigumi",
        "szelvedo", "ablakmoso", "illatosito", "autosoft", "csomagtarto",
        "kerekpar tarto", "vonohorog", "autokiegeszito",
    ],
    # 'multi' – tudatosan nem kap kulcsszavakat; ez a “minden-amire-nincs-jó-szabály”
}


def _score_category(slug: str, text: str) -> int:
    """
    Egyszerű pontozás: minden talált kulcsszó +1 pont.
    (Lehet később súlyozni, regexezni stb.)
    """
    if slug not in CATEGORY_KEYWORDS:
        return 0
    score = 0
    for kw in CATEGORY_KEYWORDS[slug]:
        if kw in text:
            score += 1
    return score


def _auto_partner_default(partner: str | None) -> str | None:
    """
    Ha nincs explicit partner_default megadva, de ismerjük a partnert,
    próbálunk kitalálni egy ésszerű alap kategóriát.
    """
    if not partner:
        return None
    partner = partner.lower()
    return PARTNER_DEFAULTS.get(partner)


def assign_category(
    title: str = "",
    desc: str = "",
    category_path: str = "",
    brand: str = "",
    partner: str | None = None,
    partner_default: str | None = None,
) -> str:
    """
    Általános kategória-besoroló.
    Visszaad egy Findora fő kategória SLUG-ot.

    Fallback logika:
      - ha nem talál kulcsszavakat → partner_default (ha van és érvényes)
      - különben: 'multi'
    """
    # 1) Partner default eldöntése
    if not partner_default:
        partner_default = _auto_partner_default(partner)

    if partner_default not in FINDORA_CATS:
        partner_default = None

    # 2) Szövegek összefűzése, normalizálása
    combined = " | ".join(
        x for x in [title, desc, category_path, brand] if x
    )
    norm = _normalize_text(combined)

    if not norm:
        # nincs semmi használható szöveg → direkt fallback
        return partner_default or "multi"

    # 3) Pontozás minden kategóriára
    best_slug = None
    best_score = 0

    for slug in FINDORA_CATS:
        if slug == "multi":
            # a "multi" csak fallback, szándékosan nem pontozzuk
            continue
        s = _score_category(slug, norm)
        if s > best_score:
            best_score = s
            best_slug = slug

    # 4) Eredmény eldöntése
    if best_slug is None or best_score <= 0:
        # nincs találat → partner default vagy multi
        return partner_default or "multi"

    return best_slug


if __name__ == "__main__":
    # Gyors kézi teszt, hogy lásd nagyjából hogy működik.
    tests = [
        {
            "title": "Lego City rendőrautó készlet",
            "desc": "Szuper építőjáték gyerekeknek",
            "category_path": "Játékok | Építőjáték",
            "partner": "jateksziget",
        },
        {
            "title": "Samsung 55\" 4K UHD Smart TV",
            "desc": "Modern okostévé HDR funkcióval",
            "category_path": "Elektronika | TV",
            "partner": "alza",
        },
        {
            "title": "Pelenka csomag újszülötteknek",
            "desc": "Kiváló nedvszívó képesség",
            "category_path": "Baba-mama | Pelenkák",
            "partner": "pepita",
        },
    ]

    for t in tests:
        cat = assign_category(
            title=t.get("title", ""),
            desc=t.get("desc", ""),
            category_path=t.get("category_path", ""),
            brand=t.get("brand", ""),
            partner=t.get("partner"),
        )
        print(f"[TEST] {t['title']}  →  {cat}")
