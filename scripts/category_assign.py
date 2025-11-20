# category_assign.py
#
# Központi kategória-hozzárendelés Findora-hoz.
# Használat:
#   from category_assign import assign_category
#   cat = assign_category(partner, category_path, title, description)
#
# Visszatérés: egy Findora-főkategória az alábbiak közül:
#   "otthon", "elektronika", "haztartasi", "kert",
#   "jatekok", "divat", "szepseg", "sport",
#   "latas", "allatok", "konyv", "utazas", "multi"

import re
import unicodedata


FINDORA_CATEGORIES = {
    "otthon",
    "elektronika",
    "haztartasi",
    "kert",
    "jatekok",
    "divat",
    "szepseg",
    "sport",
    "latas",
    "allatok",
    "konyv",
    "utazas",
    "multi",
}


def _normalize_text(*parts: str) -> str:
    """Összefűzi a szövegeket, kisbetűsít, ékezetmentesít."""
    s = " ".join(p for p in parts if p)
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _match_any(text: str, keywords) -> bool:
    return any(k in text for k in keywords)


def _assign_for_tchibo(text: str) -> str:
    """Durva, de jól működő Tchibo-szabályok."""
    # Gyerek / játék
    if _match_any(text, ["gyerek", "baba", "jatek", "játé", "pluss", "lego"]):
        return "jatekok"

    # Sport
    if _match_any(
        text,
        [
            "sport",
            "futas",
            "futás",
            "joga",
            "jóga",
            "fitness",
            "edz",
            "kerekpar",
            "kerékpár",
        ],
    ):
        return "sport"

    # Divat (ruházat, cipő, fehérnemű)
    if _match_any(
        text,
        [
            "polo",
            "póló",
            "pulover",
            "pulóver",
            "nadrag",
            "nadrág",
            "farmer",
            "szoknya",
            "ruha",
            "kabát",
            "kabát",
            "dzseki",
            "dzseki",
            "cipo",
            "cipő",
            "csizma",
            "szandal",
            "szandál",
            "fehernemu",
            "fehérnemű",
            "melltarto",
            "melltartó",
            "bugyi",
            "tanga",
            "zokni",
            "harisnya",
            "pizsama",
        ],
    ):
        return "divat"

    # Szépség / kozmetika
    if _match_any(
        text,
        [
            "kozmetika",
            "kozmetikum",
            "parfum",
            "parfüm",
            "smink",
            "borapolo",
            "bőrápoló",
            "hajapol",
            "fürdő",
            "furdo",
            "szepseg",
            "szépség",
        ],
    ):
        return "szepseg"

    # Háztartási gép
    if _match_any(
        text,
        [
            "porszivo",
            "porszívó",
            "mosogep",
            "mosógép",
            "mosogatogep",
            "mosogatógép",
            "huto",
            "hűtő",
            "mikro",
            "suto",
            "sütő",
            "kavefozo",
            "kávéfőző",
            "robotgep",
            "gofrisuto",
            "vasalo",
            "vasaló",
        ],
    ):
        return "haztartasi"

    # Konyha / otthon
    if _match_any(
        text,
        [
            "konyha",
            "edeny",
            "edény",
            "serpenyo",
            "serpenyő",
            "sutoliszt",
            "sütemény",
            "sutiforma",
            "sütőforma",
            "tál",
            "tal",
            "pohar",
            "pohár",
            "poharkeszlet",
            "pohárkészlet",
            "agynemu",
            "ágynemű",
            "parna",
            "párna",
            "takaró",
            "fuggony",
            "függöny",
            "szonyeg",
            "szőnyeg",
            "lampa",
            "lámpa",
            "dekor",
            "lakberendezes",
            "lakberendezés",
        ],
    ):
        return "otthon"

    # Alap fallback Tchibo-ra
    return "otthon"


def _assign_for_alza(text: str) -> str:
    """Alza-specifikus szabályok a fő kategóriákhoz."""
    # Állatok
    if _match_any(text, ["allat", "állat", "kutya", "macska", "kutyatáp", "macskatáp"]):
        return "allatok"

    # Látás (optika)
    if _match_any(
        text,
        [
            "szemuveg",
            "szemüveg",
            "napszemuveg",
            "napszemüveg",
            "kontaktlencse",
            "optika",
            "optikus",
        ],
    ):
        return "latas"

    # Könyv
    if _match_any(text, ["konyv", "könyv", "regeny", "regény", "szotar", "szótár"]):
        return "konyv"

    # Sport
    if _match_any(
        text,
        [
            "sport",
            "fitness",
            "futas",
            "futás",
            "kerekpar",
            "kerékpár",
            "bicikli",
            "labda",
            "foci",
            "kosarlabda",
            "kosárlabda",
            "horgasz",
            "horgász",
            "sator",
            "sátor",
            "kemping",
            "golf",
            "rollerek",
            "kori",
            "korcsolya",
            "proteint",
            "feherje",
            "fehérje",
        ],
    ):
        return "sport"

    # Szépség / drogéria / parfűm, kozmetika, egészség
    if _match_any(
        text,
        [
            "drogeria",
            "drogéria",
            "szepseg",
            "szépség",
            "kozmetika",
            "kozmetikum",
            "parfum",
            "parfüm",
            "smink",
            "borapolo",
            "bőrápoló",
            "borapolas",
            "hajapolo",
            "hajápolás",
            "fogadoapolas",
            "fogapolas",
            "fogkefe",
            "fogkrém",
            "fogkrem",
            "borotvalkoz",
            "borotválkoz",
            "dezodor",
            "illat",
            "eletminoseg javitasa",
            "gyogyaszati segedeszkoz",
            "gyógyászati segédeszköz",
            "rehabilitacios segedeszkoz",
            "rehabilitációs segédeszköz",
        ],
    ):
        return "szepseg"

    # Játékok
    if _match_any(
        text,
        [
            "jatek",
            "játék",
            "lego",
            "playmobil",
            "baba",
            "pluss",
            "tarsasjatek",
            "társasjáték",
            "tarsas",
            "jatekfigura",
            "jatekszett",
        ],
    ):
        return "jatekok"

    # Divat (ruházat, ékszer, óra)
    if _match_any(
        text,
        [
            "polo",
            "póló",
            "pulover",
            "pulóver",
            "nadrag",
            "nadrág",
            "szoknya",
            "ruha",
            "kabát",
            "dzseki",
            "cipo",
            "cipő",
            "csizma",
            "szandál",
            "szandal",
            "zokni",
            "fehernemu",
            "fehérnemű",
            "melltarto",
            "melltartó",
            "ora",
            "óra",
            "karora",
            "karóra",
            "ekszer",
            "ékszer",
            "taska",
            "táska",
            "hatizsak",
            "hátizsák",
        ],
    ):
        return "divat"

    # Háztartási gépek
    if _match_any(
        text,
        [
            "haztartasi gep",
            "háztartási gép",
            "mosogep",
            "mosógép",
            "mosogatogep",
            "mosogatógép",
            "mosogatoge",
            "mosogatasi",
            "porszivo",
            "porszívó",
            "suto",
            "sütő",
            "futo",
            "fűtő",
            "boiler",
            "hutogep",
            "hűtőszekrény",
            "hutolada",
            "hűtőláda",
            "kavefozo",
            "kávéfőző",
            "mikro",
            "robotgep",
            "kenyersut",
            "sodastream",
            "mosogatogep",
            "parologtato",
            "párologtató",
        ],
    ):
        return "haztartasi"

    # Elektronika
    if _match_any(
        text,
        [
            "laptop",
            "notebook",
            "szamitogep",
            "számítógép",
            "pc ",
            " gamer",
            "monitor",
            "videokartya",
            "videókártya",
            "processzor",
            "alaplap",
            "ssd",
            "hdd",
            "memoria",
            "memória",
            "tv ",
            "televizio",
            "televízió",
            "okostelefon",
            "okos telefon",
            "mobiltelefon",
            "tablet",
            "konzol",
            "playstation",
            "xbox",
            "nintendo",
            "fejhallgato",
            "fejhallgató",
            "hangszoro",
            "hangszóró",
            "projektor",
            "router",
            "halozati eszkoz",
            "hálózati eszköz",
            "nyomtato",
            "nyomtató",
            "3d nyomtat",
        ],
    ):
        return "elektronika"

    # Kert
    if _match_any(
        text,
        [
            "kert",
            "kerti",
            "locsolo",
            "locsoló",
            "grill",
            "faszenes",
            "medence",
            "trampolin",
            "trambulin",
            "furesz",
            "fűrész",
            "fukasza",
            "fűkasza",
            "funyiro",
            "fűnyíró",
            "lombszivo",
            "lombszívó",
            "kerti butor",
            "kerti bútor",
            "kerti szék",
            "kerti asztal",
        ],
    ):
        return "kert"

    # Otthon (lakberendezés, bútor, világítás, takarítás stb.)
    if _match_any(
        text,
        [
            "otthon, barkacs, kert",
            "otthon",
            "butor",
            "bútor",
            "komod",
            "kanape",
            "kanapé",
            "agykeret",
            "ágykeret",
            "matrac",
            "matrac",
            "lampa",
            "lámpa",
            "vilagitastechnika",
            "világítástechnika",
            "fuggony",
            "függöny",
            "szonyeg",
            "szőnyeg",
            "parna",
            "párna",
            "agynemu",
            "ágynemű",
            "toroalkozo",
            "törölköző",
            "torolkozo",
            "takaritas",
            "takarítás",
            "tisztitoszer",
            "tisztítószer",
            "mosopor",
            "mosópor",
            "mososzer",
            "mosószer",
            "lakberendezes",
            "lakberendezés",
        ],
    ):
        return "otthon"

    # Utazás / autó – egyelőre mehet "utazas"
    if _match_any(
        text,
        [
            "auto-motor",
            "autó-motor",
            "autokozmetika",
            "autókiegészítők",
            "autokiegeszitok",
            "autogumi",
            "csomagtarto",
            "csomagtartó",
            "utazotaska",
            "utazótáska",
            "borond",
            "bőrönd",
            "lakokocsi",
            "lakókocsi",
            "hajo",
            "hajó",
            "csónak",
            "csonak",
        ],
    ):
        return "utazas"

    # Ha semmi nem talált – Multi fallback
    return "multi"


def assign_category(partner: str, category_path: str, title: str, description: str) -> str:
    """
    Főkategória meghatározása partner + category_path + title + description alapján.
    """
    text = _normalize_text(category_path, title, description)
    if not text:
        return "multi"

    partner = (partner or "").lower().strip()

    if partner == "tchibo":
        cat = _assign_for_tchibo(text)
    elif partner == "alza":
        cat = _assign_for_alza(text)
    else:
        # Default – ha később új partnert kötünk, ide is lehet rakni szabályt
        cat = _assign_for_alza(text)

    if cat not in FINDORA_CATEGORIES:
        return "multi"
    return cat
