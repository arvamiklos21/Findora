# scripts/category_assign.py
#
# Findora – partnerfüggetlen kategória-hozzárendelés
# Bemenet:
#   - partner (opcionális, pl. "alza", "tchibo")
#   - category_path (Alza: "Sport, szabadidő|Kemping és túra|...", Tchibo: "Női ruházat > Pulóverek", stb.)
#   - title
#   - desc
#
# Kimenet:
#   - "kat-elektronika" | "kat-gepek" | "kat-otthon" | "kat-jatekok" |
#     "kat-sport" | "kat-konyv" | "kat-divat" | "kat-szepseg" |
#     "kat-allatok" | "kat-egyeb"

import re

# ===== Segédfüggvények =====

def _norm(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip().lower()

def _has_any(text: str, words):
    t = _norm(text)
    return any(w in t for w in words if w)

def _root_from_cat_path(cat_path: str) -> str:
    """
    Alza-szerű product_type / category_path első szintje:
    pl. "Sport, szabadidő|Kemping..." → "sport, szabadidő"
    """
    if not cat_path:
        return ""
    base = str(cat_path).split("|")[0]
    base = base.split(">")[0]
    return _norm(base)


# ===== Közös kulcsszó-csoportok (minden partnerhez) =====

DIVAT_WORDS = [
    "kabát", "kabat", "dzseki", "dzsek", "pulóver", "pulover", "póló", "polo",
    "ing", "nadrág", "nadrag", "farmer", "szoknya", "ruha", "leggings",
    "harisnya", "melltartó", "bugyi", "tanga", "fehérnemű", "cipő", "cipo",
    "csizma", "bakancs", "papucs", "szandál", "szandal", "pullover", "tunika",
    "kardigán", "kardigan", "overál", "overal", "pizsama", "melegítő", "melegito"
]

SZEPSEG_WORDS = [
    "kozmetikum", "kozmetika", "smink", "rúzs", "szempillaspirál",
    "alapozó", "púder", "korrektor", "highlighter",
    "hajápolás", "hajapolas", "sampon", "balzsam", "hajpakolás",
    "parfüm", "parfum", "eau de toilette", "edt", "edp",
    "dezodor", "deo", "borotválkozás", "borotvalkozas",
    "testápoló", "testapolo", "kézkrém", "kezkrem", "arckrém", "arckrem",
]

ALLAT_WORDS = [
    "kutya", "macska", "hörcsög", "hörcsog", "nyúl", "nyul",
    "állateledel", "allateledel", "kutyaeledel", "macskaeledel",
    "pet", "terrárium", "terrarium", "akvárium", "akvarium",
]

JATEK_WORDS = [
    "lego", "playmobil", "társasjáték", "tarsasjatek",
    "kirakó", "kirako", "puzzle", "plüss", "baba", "babakocsi",
    "játék", "jatekok", "játékok", "jatek", "jatekfigura",
    "építőkocka", "epitokocka", "kreatív készlet", "kreativ keszlet",
]

SPORT_WORDS = [
    "fitness", "futópad", "futopad", "súlyzó", "sulyzo",
    "bicikli", "kerékpár", "kerekpar", "roller", "gördeszka",
    "labda", "focilabda", "kosárlabda", "kosarlabda", "edzőcipő", "edzocipo",
    "horgász", "horgasz", "túra", "tura", "kemping",
]

KONYV_WORDS = [
    "könyv", "konyv", "regény", "regeny", "szakkönyv", "tankönyv",
    "mesekönyv", "mese könyv", "novella",
]

ELEKTRONIKA_KEYWORDS = [
    "tv", "televízió", "televizio",
    "monitor", "laptop", "notebook", "pc",
    "konzol", "xbox", "playstation", "ps4", "ps5", "nintendo switch",
    "okostelefon", "okos telefon", "mobiltelefon", "mobiltelefonok",
    "okosóra", "okosora", "tablet",
    "headset", "fejhallgató", "fejhallgato", "fülhallgató", "fulhallgato",
    "soundbar", "hangfal", "hangszóró", "hangszoro",
    "projektor", "fotoaparát", "fotoaparat", "fényképező", "fenykepezo",
]

HAZTARTAS_GEP_WORDS = [
    "mosógép", "mosogep", "szárítógép", "szaritogep", "mosogatógép","mosogatogep",
    "porszívó", "porszivo", "robotporszívó", "robotporszivo",
    "mosógép-szárító", "hűtő", "huto", "hűtőszekrény", "hutőszekrény",
    "tűzhely", "tuzhely", "mikrohullámú", "mikrohullamu",
    "mosogatógép", "sütő", "suto", "főzőlap", "főzőluzlap", "főzőlap",
]

OTTHON_WORDS = [
    "bútor", "butor", "szekrény", "asztal", "szék", "szek", "kanapé", "kanape",
    "ágy", "agy", "polc", "dekoráció", "dekoracio",
    "takaró", "takaro", "párna", "parna", "szőnyeg", "szonyeg",
    "lakásdekor", "lakberendezés", "lakberendezes",
    "lámpa", "lampa", "izzó", "izzó", "világítás", "vilagitas",
    "takarítószer", "takaritoszer", "tisztítószer", "tisztitoszer",
    "mosószer", "mososzer", "öblítő", "oblito",
]


# ===== ALZA-specifikus hozzárendelés =====

def _assign_alza(cat_path: str, title: str, desc: str) -> str:
    """Alza kategóriák → Findora kat-*"""
    cat_path = cat_path or ""
    title = title or ""
    desc = desc or ""
    root = _root_from_cat_path(cat_path)
    all_text = " ".join([cat_path, title, desc]).lower()

    # 1) Erős kulcsszavas felülbírálások

    # Divat (ruha, cipő, stb.)
    if _has_any(all_text, DIVAT_WORDS):
        return "kat-divat"

    # Könyv
    if _has_any(all_text, KONYV_WORDS):
        return "kat-konyv"

    # Állatok
    if _has_any(all_text, ALLAT_WORDS):
        return "kat-allatok"

    # Játék (klasszikus gyerekjáték, társasjáték stb.)
    if _has_any(all_text, JATEK_WORDS):
        return "kat-jatekok"

    # Sport
    if _has_any(all_text, SPORT_WORDS):
        return "kat-sport"

    # Szépség
    if _has_any(all_text, SZEPSEG_WORDS) or "illatszer" in all_text or "kozmetika" in all_text:
        return "kat-szepseg"

    # Elektronika tipikus kulcsszavak
    if _has_any(all_text, ELEKTRONIKA_KEYWORDS):
        return "kat-elektronika"

    # Háztartási gépek
    if _has_any(all_text, HAZTARTAS_GEP_WORDS):
        return "kat-gepek"

    # 2) Root-alapú csoportosítás (product_type első szintje alapján)

    # Elektronika gyökerek
    elek_roots = {
        "tv, fotó, audió, videó",
        "tv, foto, audio-video",
        "pc és laptop",
        "počítače a notebooky",
        "telefon, tablet, okosóra",
        "mobily, chytré hodinky, tablety",
        "gaming és szórakozás",
        "gaming, hry a zábava",
        "okosotthon",
        "chytrá domácnost",
        "okosotthon | okos elektromos hálózat",
    }

    # Háztartási gép gyökerek
    gepek_roots = {
        "háztartási kisgép",
        "domácí a osobní spotřebiče",
        "háztartási nagygép",
        "velké spotřebiče",
    }

    # Otthon/barkács/kert + konyha
    otthon_roots = {
        "otthon, barkács, kert",
        "dům, dílna a zahrada",
        "konyha, háztartás",
        "kuchyňské a domácí potřeby",
        "irodai felszerelés",
        "kancelář a papírnictví",
    }

    # Játék
    jatek_roots = {
        "játék, baba-mama",
        "hračky, pro děti a miminka",
    }

    # Sport
    sport_roots = {
        "sport, szabadidő",
        "sport a outdoor",
    }

    # Szépség / drogéria
    szepseg_roots = {
        "illatszer, ékszer",
        "kosmetika, parfémy a krása",
    }
    drogeria_roots = {
        "drogéria",
        "drogerie",
    }

    # Egészség / gyógyszertár
    egeszseg_roots = {
        "egészségmegőrzés",
        "lékárna a zdraví",
    }

    # Élelmiszer
    elelmiszer_roots = {
        "élelmiszer",
    }

    # Root szerinti döntés

    if root in elek_roots:
        return "kat-elektronika"

    if root in gepek_roots:
        return "kat-gepek"

    if root in sport_roots:
        return "kat-sport"

    if root in jatek_roots:
        return "kat-jatekok"

    if root in szepseg_roots:
        return "kat-szepseg"

    if root in drogeria_roots:
        # Drogéria: ha inkább mosó-/tisztítószer → otthon, ha szépség → szepseg
        if any(w in all_text for w in ["mosószer", "mososzer", "tisztítószer", "tisztitoszer", "öblítő", "oblito", "tisztítás", "tisztitas"]):
            return "kat-otthon"
        if any(w in all_text for w in ["sampon", "balzsam", "dezodor", "deo", "borotva", "borotválkozás", "borotvalkozas"]):
            return "kat-szepseg"
        return "kat-otthon"

    if root in otthon_roots:
        return "kat-otthon"

    if root in egeszseg_roots:
        # Egészségmegőrzés mehet egyelőre egyébbe
        return "kat-egyeb"

    if root in elelmiszer_roots:
        # Élelmiszer is mehet egyelőre egyébbe
        return "kat-egyeb"

    # Ha semmi nem illik: egyéb
    return "kat-egyeb"


# ===== TCHIBO-specifikus hozzárendelés (egyszerűsítve) =====

def _assign_tchibo(cat_path: str, title: str, desc: str) -> str:
    """
    Tchibo-nál tipikusan:
      - Női ruházat > Pulóverek → kat-divat
      - Férfi ruházat, Gyerek ruházat → kat-divat
      - Otthon, Lakberendezés, Konyha → kat-otthon
      - Kávé → kat-egyeb
      - Játékok → kat-jatekok
    """
    cat_path = cat_path or ""
    title = title or ""
    desc = desc or ""
    all_text = " ".join([cat_path, title, desc]).lower()

    # Divat
    if any(w in all_text for w in ["női ruházat", "noi ruhazat", "férfi ruházat", "ferfi ruhazat", "gyerek ruházat", "gyerekruha"]):
        return "kat-divat"
    if _has_any(all_text, DIVAT_WORDS):
        return "kat-divat"

    # Otthon / lakberendezés / konyha
    if any(w in all_text for w in ["otthon", "lakberendezés", "lakberendezes", "konyha"]):
        return "kat-otthon"

    # Játék
    if "játék" in all_text or "jatekok" in all_text or "gyerekjáték" in all_text:
        return "kat-jatekok"

    # Sport / szabadidő
    if any(w in all_text for w in ["sport", "jóga", "yoga", "futás", "futas", "edzés", "edzes"]):
        return "kat-sport"

    # Szépség / wellness
    if any(w in all_text for w in ["wellness", "kozmetika", "ápolás", "apolas"]):
        return "kat-szepseg"

    # Kávé, kapszula, tea → egyéb (vagy később élelmiszer)
    if any(w in all_text for w in ["kávé", "kave", "kapszula", "espresso", "tea"]):
        return "kat-egyeb"

    # Ha semmi különös, rakjuk otthon vagy egyéb közé
    if "otthon" in all_text:
        return "kat-otthon"

    return "kat-egyeb"


# ===== Default / egyéb partnerek =====

def _assign_default(cat_path: str, title: str, desc: str) -> str:
    """Egyszerű fallback logika más partnerekhez."""
    all_text = " ".join([cat_path or "", title or "", desc or ""]).lower()

    if _has_any(all_text, DIVAT_WORDS):
        return "kat-divat"
    if _has_any(all_text, JATEK_WORDS):
        return "kat-jatekok"
    if _has_any(all_text, SPORT_WORDS):
        return "kat-sport"
    if _has_any(all_text, SZEPSEG_WORDS):
        return "kat-szepseg"
    if _has_any(all_text, ELEKTRONIKA_KEYWORDS):
        return "kat-elektronika"
    if _has_any(all_text, HAZTARTAS_GEP_WORDS):
        return "kat-gepek"
    if _has_any(all_text, OTTHON_WORDS):
        return "kat-otthon"
    if _has_any(all_text, KONYV_WORDS):
        return "kat-konyv"
    if _has_any(all_text, ALLAT_WORDS):
        return "kat-allatok"

    return "kat-egyeb"


# ===== Publikus belépési pont =====

def assign_category(*args) -> str:
    """
    Rugalmas wrapper, hogy a régi és új hívás is működjön:

    - régi: assign_category(cat_path, title, desc)
      → partner = "alza"

    - új: assign_category(partner, cat_path, title, desc)
      → partner szerint ágazik (alza, tchibo, stb.)
    """
    partner = "alza"
    cat_path = ""
    title = ""
    desc = ""

    if len(args) == 3:
        # (cat_path, title, desc) – default: alza
        cat_path, title, desc = args
    elif len(args) == 4:
        # (partner, cat_path, title, desc)
        partner, cat_path, title, desc = args
        partner = (partner or "").lower()
    else:
        # Rossz hívás – inkább adjunk vissza egy kategóriát, mint hogy elszálljon
        return "kat-egyeb"

    if partner == "alza":
        return _assign_alza(cat_path, title, desc)
    if partner == "tchibo":
        return _assign_tchibo(cat_path, title, desc)

    # Egyéb partnerek
    return _assign_default(cat_path, title, desc)
