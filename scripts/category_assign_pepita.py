# category_assign.py
#
# Findora – egyszerű, szabályalapú kategorizáló több partner feedjéhez.
# Logika: a termék több szövegmezőjét összefűzzük, kulcsszavak alapján
# pontozzuk a kategóriákat, a legtöbb pontot elérő kategória nyer.
#
# Kategóriák:
#   elektronika
#   haztartasi_gepek
#   otthon
#   kert
#   jatekok
#   divat
#   szepseg
#   sport
#   latas
#   allatok
#   konyv
#   utazas
#   multi   (ha semmi másra nem illik)

import re
from typing import Dict, Any

# Ezekből a mezőkből építjük fel a szöveget.
# FONTOS: az XML-ben a tageket már namespace/prefix nélkül kapjuk meg
# (child.tag.split("}")[-1]), tehát pl. g:product_type → "product_type"
TEXT_TAG_KEYS = [
    # általános szövegmezők
    "title",
    "name",
    "description",
    "short_description",
    "long_description",
    "product_type",
    "category",
    "CATEGORYTEXT",
    "manufacturer",

    # egyes partnerek speciális mezői
    "PRODUCTNAME",
    "ITEMNAME",
    "PRODUCTNAME_FULL",
]

# ---- KULCSSZAVAK KATEGÓRIÁNKÉNT (RÖVID, DE HASZNÁLHATÓ VERZIÓ) ----
# Kulcsszó -> súly (1–4). Később bővíthetjük / finomhangolhatjuk.

CATEGORIES: Dict[str, Dict[str, int]] = {
    "elektronika": {
        "tv": 3, "televizio": 4, "televízió": 4,
        "monitor": 3,
        "laptop": 4, "notebook": 4,
        "tablet": 3,
        "telefon": 3, "okostelefon": 3, "smartphone": 3,
        "konzol": 4, "ps4": 4, "ps5": 4, "xbox": 4,
        "kamera": 3, "fényképező": 3, "fenykepezo": 3,
        "nyomtató": 3, "nyomtato": 3,
        "hangszóró": 3, "hangszoro": 3,
        "fejhallgató": 3, "fejhallgato": 3,
        "elektronika": 2,
    },

    "haztartasi_gepek": {
        "mosógép": 4, "mosogep": 4,
        "mosogatógép": 4, "mosogatogep": 4,
        "hűtő": 4, "huto": 4, "hűtőszekrény": 4,
        "fagyasztó": 3, "fagyaszto": 3,
        "porszívó": 4, "porszivo": 4, "robotporszívó": 4, "robotporszivo": 4,
        "sütő": 3, "suto": 3, "tűzhely": 3, "tuzhely": 3,
        "mikrohullámú": 3, "mikrohullamu": 3, "mikró": 3, "micro": 3,
        "kávéfőző": 4, "kavefozo": 4,
        "vízforraló": 3, "vizforralo": 3,
        "turmix": 3,
        "robotgép": 3, "robotgep": 3,
        "klíma": 3, "klima": 3, "légkondicionáló": 3, "legkondicionalo": 3,
        "háztartási gép": 2, "haztartasi gep": 2,
    },

    "otthon": {
        # bútor, lakber
        "bútor": 4, "butor": 4,
        "kanapé": 4, "kanape": 4, "fotel": 3,
        "ágy": 3, "agy": 3, "matrac": 4,
        "szekrény": 3, "szekreny": 3, "komód": 3, "komod": 3,
        "szék": 3, "szek": 3, "asztal": 3,
        "szőnyeg": 3, "szonyeg": 3,
        "függöny": 3, "fuggony": 3,
        "párna": 3, "parna": 3,
        "takaró": 3, "takaro": 3,
        "ágynemű": 3, "agy nemu": 3,
        "dekor": 2, "dekoráció": 2, "dekoracio": 2,
        "lakberendezés": 2, "lakberendezes": 2,
        "pohár": 3, "pohar": 3, "tányér": 3, "tanyer": 3,
        "evőeszköz": 3, "evőeszközök": 3, "evoszkoz": 3,
        "bögre": 3, "bogre": 3,
        "csaptelep": 3,
        "mosogatótálca": 3, "mosogatotalca": 3,
        "szemetes": 3,
        "tároló": 2, "tarolo": 2,
        "otthon": 2,

        # építkezés / felújítás / szerelvények
        "építkezés": 2, "epitkezes": 2,
        "felújítás": 2, "felujitas": 2,
        "wc ": 3, "wc-": 3, "wc szett": 4,
        "wc tartály": 3, "wc tartaly": 3,
        "golyóscsap": 3, "golyozcsap": 3, "golyoscsap": 3,
        "hollanderes szelep": 4, "szelep": 2,
        "szerelvény": 2, "szerelveny": 2,

        # babás cuccok – ide gyűjtjük, amíg nincs külön "baba" kategória
        "babák": 3, "babák & tipegők": 3, "babák & tipegok": 3,
        "baba ": 2,  # szó elején/után
        "babatáplálás": 3, "babataplalas": 3,
        "baba fürdetés": 3, "baba furdetes": 3,
        "pelenka": 3, "úszópelenka": 3, "uszopelenka": 3,
        "törlőkendő": 3, "torlokendo": 3,
        "popsikrém": 3, "popsikrem": 3,
        "babakád": 3, "babakad": 3,
        "babaülőke": 3, "babauloke": 3,
        "babatartó": 3, "babatarto": 3,
        "baba fogkefe": 3,
        "cumisüveg": 3, "cumisuveg": 3,
        "cumi ": 3, "cumis": 3,
        "etetőcumi": 3, "etetocumi": 3,
        "mellszívó": 3, "mellszivo": 3,
        "babaszoba": 2,
        "babakocsi": 3,
        "babakocsi kiegészítők": 3, "babakocsi kiegeszitok": 3,
        "babakocsi napernyő": 3, "babakocsi napernyo": 3,
        "napfénytető": 3, "napfenyteto": 3,
    },

    "kert": {
        "kerti": 2, "kertészeti": 2, "kerteszeti": 2,
        "fűnyíró": 4, "funyiro": 4,
        "láncfűrész": 4, "lancfuresz": 4,
        "sövényvágó": 3, "sovenyvago": 3,
        "locsoló": 3, "locsolo": 3,
        "tömlő": 3, "tomlo": 3, "slag": 3,
        "gereblye": 3, "ásó": 3, "aso": 3, "lapát": 3, "lapat": 3,
        "vetőmag": 2, "vetomag": 2,
        "virágföld": 2, "viragfold": 2,
        "grill": 3, "kerti grill": 3,
        "kerti bútor": 3, "kerti butor": 3,
        "barkács": 2, "barkacs": 2,
        "szerszám": 2, "szerszam": 2,
    },

    "jatekok": {
        "játék": 3, "jatek": 3,
        "játékok": 3, "jatekok": 3,
        "gyerekjáték": 3, "gyerekjatek": 3,
        "játékbolt": 2, "jateksziget": 2,
        "társasjáték": 4, "tarsasjatek": 4, "társas": 3, "tarsas": 3,
        "puzzle": 3, "kirakó": 3, "kirako": 3,
        "plüss": 4, "pluss": 4, "plüssfigura": 3, "plussfigura": 3,
        "játékautó": 3, "jatekauto": 3, "kisautó": 3, "kisauto": 3,
        "babaház": 3, "babahaz": 3,
        "gyurma": 2,
        "lego": 4, "duplo": 4,
        "playmobil": 4,
    },

    "divat": {
        "póló": 3, "polo": 3, "trikó": 2, "triko": 2,
        "pulóver": 3, "pulover": 3,
        "nadrág": 3, "nadrag": 3, "farmer": 3,
        "ruha": 3, "szoknya": 3,
        "kabát": 3, "kabat": 3, "dzseki": 3,
        "cipő": 3, "cipo": 3, "csizma": 3, "bakancs": 3,
        "szandál": 3, "szandal": 3, "papucs": 3,
        "fehérnemű": 4, "fehernemu": 4,
        "bugyi": 4,
        "melltartó": 4, "melltarto": 4,
        "zokni": 3, "harisnya": 3,
        "sapka": 2, "sál": 2, "sal": 2, "kesztyű": 2, "kesztyu": 2,
        "táska": 3, "taska": 3, "hátizsák": 3, "hatizsak": 3,
        "ékszer": 3, "ekszer": 3,
        "óra": 3, "ora": 3,
        "divat": 2, "fashion": 2,
    },

    "szepseg": {
        # alap szépség / kozmetika
        "sampon": 3,
        "tusfürdő": 3, "tusfurdo": 3,
        "testápoló": 3, "testapolo": 3,
        "arckrém": 3, "arckrem": 3,
        "szérum": 3, "szerum": 3,
        "smink": 3, "alapozó": 3, "alapozo": 3,
        "rúzs": 3, "ruzs": 3,
        "körömlakk": 3, "koromlakk": 3,
        "szempillaspirál": 3, "szempillaspiral": 3,
        "dezodor": 3, "deo": 2,
        "parfüm": 3, "parfum": 3,
        "borotva": 3,
        "epilátor": 3, "epilator": 3,
        "hajszárító": 3, "hajszarito": 3,
        "hajvasaló": 3, "hajvasalo": 3,
        "kozmetikum": 2, "kozmetika": 2,
        "wellness": 2,

        # intim higiénia, betét, síkosító
        "tisztasági betét": 4, "tisztasagi betet": 4,
        "egészségügyi betét": 4, "egeszsegugyi betet": 4,
        "intimbetét": 4, "intimbetet": 4,
        "intim higiénia": 3, "intim higienia": 3,
        "síkosító": 4, "sikosito": 4,
        "libresse": 3, "naturella": 3, "durex": 3,
        "ajakhápoló": 3, "ajakápoló": 3, "ajakbalzsam": 3, "ajakapolo": 3,

        # szájápolás
        "szájápolás": 3, "szajapolas": 3,
        "fogkefe": 3, "fogkefék": 3, "fogkefek": 3,
        "elektromos fogkefe": 4,
        "szájzuhany": 4, "szajzuhany": 4,
        "pótfej": 3, "potfej": 3,

        # egészségügyi eszközök
        "tesztcsík": 2, "tesztcsik": 2,
        "lázmérő": 4, "lazmero": 4,
        "személymérleg": 4, "szemelymerleg": 4,
        "testelemző": 4, "testelemzo": 4,
        "légzésfigyelő": 3, "legzesfigyelo": 3,
        "levegőkezelés": 2, "levegokezeles": 2,
        "légtisztító": 4, "legtisztito": 4,
        "szellőztető ventilátor": 3, "szellozteto ventilator": 3,

        # egyéb szépség/ápolás eszközök
        "hajformázó": 4, "hajformazo": 4,
        "hajcsavaró": 4, "hajcsavaro": 4,
        "hajvágó": 4, "hajvago": 4,
        "szemmasszírozó": 4, "szemmasszirozo": 4,
        "szakállolaj": 4, "szakallolaj": 4,

        # márkák (tipikusan szépség / higiénia)
        "libresse": 3, "bella": 2, "rexona": 2, "signal": 2,
        "vaseline": 3, "chicco": 2, "phillips sonicare": 2,
        "oclean": 2, "leukoplast": 2,
    },

    "sport": {
        "futópad": 4, "futopad": 4,
        "szobabicikli": 4, "szobakerékpár": 4, "szobakerekpar": 4,
        "súlyzó": 3, "sulyzo": 3,
        "edzőpad": 3, "edzopad": 3,
        "fitnesz": 3, "fitness": 3,
        "jóga": 3, "joga": 3, "jógaszőnyeg": 3, "jogaszonyeg": 3,
        "labda": 2, "focilabda": 3, "kosárlabda": 3, "kosarlabda": 3,
        "pingpong": 3, "asztalitenisz": 3,
        "bicikli": 3, "kerékpár": 3, "kerekpar": 3,
        "roller": 3, "gördeszka": 3, "gordeszka": 3,
        "sátor": 3, "sator": 3,
        "hálózsák": 3, "halozsak": 3,
        "sportszer": 2, "sportfelszerelés": 2, "sportfelszereles": 2,
        # lovaglás mint sport – a "lókaparó" egyértelmű jel
        "lovaglás": 3, "lovaglas": 3,
        "ló": 2, "lo ": 2,
    },

    "latas": {
        "kontaktlencse": 4,
        "lencsefolyadék": 4, "lencsefolyadek": 4,
        "szemcsepp": 4,
        "műkönny": 3, "mukonny": 3,
        "optika": 3, "optikai": 3,
        "szemüveg": 3, "szemuveg": 3,
        "napszemüveg": 3, "napszemuveg": 3,
        "dioptria": 3,
    },

    "allatok": {
        # házi kedvencek
        "kutyatáp": 4, "kutyatap": 4, "kutyaeledel": 4,
        "macskatáp": 4, "macskatáp": 4, "macskaeledel": 4,
        "jutalomfalat": 3,
        "póráz": 3, "poraz": 3,
        "nyakörv": 3, "nyakorv": 3,
        "hám": 3, "ham": 3,
        "fekhely": 3,
        "kaparófa": 3, "kaparo fa": 3,
        "macskaalom": 4,
        "alomtálca": 3, "alomtalca": 3,
        "kutyaház": 4, "kutyahaz": 4,
        "kutyapiszok": 4,
        "kutyapiszok zacskó": 4, "kutyapiszok zacskok": 4,

        # haszonállat tartás
        "állattartás": 3, "allattartas": 3,
        "haszonállat": 3, "haszonallat": 3,
        "baromfi": 3,
        "itató": 4, "itato": 4, "itatók": 4,
        "etető": 4, "eteto": 4,
        "borjúitató": 4, "borjuitato": 4,
        "bárányitató": 4, "baranyitato": 4,
        "sertés orrfogó": 4, "sertes orrfogo": 4,

        # egyéb állatos
        "lókaparó": 3, "lokaparo": 3,
        "kutyaház": 4, "kutyahaz": 4,
    },

    "konyv": {
        "könyv": 4, "konyv": 4,
        "regény": 3, "regeny": 3,
        "krimi": 3,
        "mese": 3, "mesekönyv": 3, "mesekonyv": 3,
        "gyerekkönyv": 3, "gyerekkonyv": 3,
        "szakkönyv": 3, "szakkonyv": 3,
        "tankönyv": 3, "tankonyv": 3,
        "munkafüzet": 3, "munkafuzet": 3,
        "album": 3,
        "enciklopédia": 3, "enciklopedia": 3,
        "füzet": 3, "fuzet": 3,
        "jegyzetfüzet": 3, "jegyzetfuzet": 3,
        "toll": 3, "ceruza": 3, "filctoll": 3,
        "írószer": 2, "iro szer": 2, "iroszer": 2,
    },

    "utazas": {
        "bőrönd": 4, "borond": 4,
        "utazótáska": 4, "utazotaska": 4,
        "kézipoggyász": 3, "kezipoggyasz": 3,
        "utazópárna": 3, "utazoparna": 3, "nyakpárna": 3, "nyakparna": 3,
        "neszesszer": 3,
        "utazási": 2, "utazasi": 2, "utazás": 2, "utazas": 2,
        "travel": 2,
        "gps": 3, "navigáció": 3, "navigacio": 3,
        "tetőbox": 3, "tetobox": 3,
    },

    # "multi" szándékosan üres – ide csak akkor esik bármi,
    # ha minden más kategória 0 pontot kap.
    "multi": {}
}

MIN_SCORE = 1  # ha minden kategória 0 pont, akkor "multi"


def normalize_text(s: str) -> str:
    """Kisbetű, ékezetek megtartva, nem betű/szám → szóköz."""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^0-9a-záéíóöőúüű]+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_text_blob(fields: Dict[str, Any]) -> str:
    """A TEXT_TAG_KEYS mezőket összefűzi egy nagy szöveggé."""
    parts = []
    for key in TEXT_TAG_KEYS:
        val = fields.get(key)
        if val:
            parts.append(str(val))
    return normalize_text(" ".join(parts))


def score_category(text: str, keywords: Dict[str, int]) -> int:
    """Egyszerű substring-alapú pontozás."""
    score = 0
    for kw, weight in keywords.items():
        if kw in text:
            score += weight
    return score


def assign_category(fields: Dict[str, Any]) -> str:
    """
    Fő belépési pont.
    fields: XML-ből kitöltött dict a fontos mezőkkel.

    Visszatér: kategória az alábbiak közül:
      elektronika, haztartasi_gepek, otthon, kert, jatekok, divat,
      szepseg, sport, latas, allatok, konyv, utazas, multi
    """
    text = build_text_blob(fields)
    if not text:
        return "multi"

    best_cat = "multi"
    best_score = 0

    for cat, kw in CATEGORIES.items():
        if cat == "multi":
            continue
        s = score_category(text, kw)
        if s > best_score:
            best_score = s
            best_cat = cat

    if best_score < MIN_SCORE:
        return "multi"

    return best_cat
