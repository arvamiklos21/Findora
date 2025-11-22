# category_assign.py
#
# Findora – egyszerű szabályalapú kategorizáló több partner feedjéhez.
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
#   multi   (csak ha semmi másra nem illik)

import re
from typing import Dict, Any

# Ezekből a mezőkből építjük fel a szöveget (XML tag nevek vége szerint)
TEXT_TAG_KEYS = [
    "PRODUCTNAME",
    "ITEMNAME",
    "PRODUCTNAME_FULL",
    "CATEGORYTEXT",
    "g:product_type",
    # onlinemarkaboltok.hu / egyéb feedek:
    "name",
    "category",
]

# ---- KULCSSZAVAK KATEGÓRIÁNKÉNT ----
# Kulcsszó -> súly (1–4). Nyugodtan bővíthető / finomhangolható.

CATEGORIES: Dict[str, Dict[str, int]] = {
    "elektronika": {
        # hard elektronika
        "tv": 3, "televizio": 4, "televízió": 4,
        "monitor": 3, "projektor": 3,
        "pc": 3, "szamitogep": 3, "számítógép": 3,
        "laptop": 4, "notebook": 4, "ultrabook": 3,
        "tablet": 3, "okostelefon": 3, "okosora": 3, "okosóra": 3,
        "telefon": 2, "smartphone": 2,
        "router": 3, "wifi": 2, "modem": 2,
        "ssd": 3, "hdd": 3, "merevlemez": 2,
        "pendrive": 3, "memoriakartya": 3, "memóriakártya": 3,
        "bluetooth": 2, "hangszoro": 3, "hangszóró": 3, "soundbar": 3,
        "fejhallgato": 3, "fejhallgató": 3, "fulhallgato": 2, "fülhallgató": 2,
        "konzol": 4, "ps4": 4, "ps5": 4, "playstation": 4,
        "xbox": 4, "nintendo switch": 4, "switch": 3,
        "pc jatek": 3, "pc játék": 3, "videójáték": 3, "videojatek": 3,
        "digitalis kod": 3, "digitális kód": 3,
        "kamera": 3, "fényképező": 3, "fenykepezo": 3, "webkamera": 3,
        "vr": 3, "vr szemüveg": 3,
        "nyomtato": 3, "nyomtató": 3,
        "alaplap": 3, "videokartya": 3, "videókártya": 3,
        "processzor": 3, "cpu": 3, "ram": 2,
        "powerbank": 2, "dokkoló": 2, "dokkolostacio": 2,
        "usb": 2, "hdmi": 2, "displayport": 2,
        "elektronika": 2, "elektronikus": 1,
    },

    "haztartasi_gepek": {
        "mosogep": 4, "mosógép": 4, "mososzarito": 4, "mosó-szárító": 4,
        "szaritogep": 4, "szárítógép": 4,
        "mosogatogep": 4, "mosogatógép": 4,
        "hutó": 4, "huto": 4, "hűtőszekrény": 4, "fagyaszto": 3, "fagyasztó": 3,
        "tuzhely": 4, "tűzhely": 4, "gaztuzhely": 4, "gáztűzhely": 4,
        "suto": 3, "sütő": 3, "fozolap": 3, "főzőlap": 3, "micro": 3,
        "mikrohullamu": 3, "mikrohullámú": 3,
        "porszivo": 4, "porszívó": 4, "robotporszivo": 4, "robotporszívó": 4,
        "gőztisztító": 3, "goztisztito": 3,
        "kavefozo": 4, "kávéfőző": 4, "espresszo": 3, "espresso": 3,
        "vizforralo": 3, "vízforraló": 3, "kenyerpirito": 3, "kenyérpirító": 3,
        "airfryer": 3, "forro levegosuto": 3, "forrólevegős sütő": 3,
        "turmix": 3, "botmixer": 3, "konyhai robotgep": 3, "konyhai robotgép": 3,
        "vasalo": 3, "vasaló": 3, "gőzállomás": 3,
        "varrogep": 3, "varrógép": 3,
        "klima": 3, "klíma": 3, "legkondi": 3, "légkondicionáló": 3,
        "ventilator": 2, "ventilátor": 2,
        "legtisztito": 3, "légtisztító": 3, "parasitó": 3, "parásító": 3,
        "haztartasi gep": 2, "háztartási gép": 2,

        # +++ KONYHAI KISGÉPEK +++
        "konyhai kisgep": 4, "konyhai kisgép": 4,
        "konyhai kisgepek": 4, "konyhai kisgépek": 4,
        "robotgep": 4, "robotgép": 4,
        "szeletelogep": 4, "szeletelőgép": 4,
        "husdaralo": 4, "húsdaráló": 4,
        "kavedaralo": 4, "kávédaráló": 4,
        "kaveorlo": 4, "kávéőrlő": 4,
        "jegkocka keszito": 4, "jégkocka készítő": 4, "jegkockakeszito": 4,
        "jégkockakészítő": 4,
        "gyumolcscentrifuga": 3, "gyümölcscentrifuga": 3,
        "aszaló": 3, "aszalo": 3,
        "multifunkcios elektromos fozoedeny": 4,
        "multifunkcionális elektromos főzőedény": 4,
        "multicook": 3, "multicooker": 3,
        "lassu fozoedeny": 4, "lassú főzőedény": 4,
        "slow cook": 3, "slowcooker": 3,

        # +++ TAKARÍTÓGÉP, KÁRPITTISZTÍTÓ, CENTRIFUGA +++
        "takaritogep": 4, "takarítógép": 4,
        "takaritogepek": 4, "takarítógépek": 4,
        "karpittisztito": 4, "kárpittisztító": 4,
        "karpittisztitogep": 4, "kárpittisztítógép": 4,
        "vizszuro": 2, "vízszűrős": 2, "vízszűrős takarítógép": 4,
        "vizszuros takaritogep": 4,
        "centrifuga": 4, "mosocentrifuga": 4, "mosócentrifuga": 4,

        # +++ PÁRAELSZÍVÓK +++
        "paraelszivo": 4, "páraelszívó": 4,
        "páraelszívók": 4, "paraelszivok": 4,
        "fali páraelszívó": 4, "beépíthető páraelszívó": 4,
        "kihúzható páraelszívó": 4, "kihuzhato paraelszivo": 4,
        "aláépíthető páraelszívó": 4, "alaepitheto paraelszivo": 4,
        "sziget páraelszívó": 4, "sziget paraelszivo": 4,
        "mennyezetbe építhető páraelszívó": 4,
        "mennyezetbe epithető paraelszivo": 4,
        "pultba építhető páraelszívó": 4, "pultba epithető paraelszivo": 4,
        "sarok páraelszívó": 4, "sarok paraelszivo": 4,
        "standard páraelszívó": 4, "standard paraelszivo": 4,
        "elszívó": 3, "elszivo": 3, "szagelszívó": 3, "szagelszivo": 3,

        # +++ VÍZMELEGÍTŐ, HŐSZIVATTYÚ +++
        "elektromos vizmelegito": 4, "elektromos vízmelegítő": 4,
        "vizmelegito": 3, "vízmelegítő": 3,
        "bojler": 3,
        "hoszivattyu": 4, "hőszivattyú": 4,
        "levego viz hoszivattyu": 4, "levegő - víz hőszivattyú": 4,

        # +++ MELEGENTARTÓ FIÓK +++
        "melegentarto fiok": 4, "melegentartó fiók": 4,
        "melegentarto": 3, "melegentartó": 3,

        # +++ FŰTÉSTECHNIKA, KANDALLÓ, HŐSUGÁRZÓ +++
        "futestechnika": 3, "fűtéstechnika": 3,
        "kandallo": 3, "kandalló": 3,
        "elektromos kandallo": 4, "elektromos kandalló": 4,
        "hosugarzo": 3, "hősugárzó": 3,
        "olaj radiator": 3, "olajradiator": 3, "olajradiátor": 3,
        "konvektor": 3, "hősugárzó ventilátor": 3,

        # +++ MÁRKA, AMI TIPIKUSAN IDE TARTOZIK +++
        "falmec": 3,
    },

    "otthon": {
        "butor": 4, "bútor": 4, "kanape": 4, "kanapé": 4, "fotel": 3,
        "agyracs": 3, "agy": 3, "ágy": 3, "matrac": 4,
        "asztal": 3, "szek": 3, "szék": 3, "eteto szek": 3, "etetőszék": 3,
        "szekreny": 3, "szekrény": 3, "gardrob": 3, "gardrób": 3, "komod": 3, "komód": 3,
        "polc": 3, "polcrendszer": 3, "tarolodoboz": 2, "tárolódoboz": 2,
        "fuggony": 4, "függöny": 4, "sotetoito": 3, "sötétítő": 3, "karnis": 3,
        "szonyeg": 3, "szőnyeg": 3, "parketta": 2,
        "parna": 3, "párna": 3, "diszparna": 3, "díszpárna": 3,
        "paplan": 3, "lepedo": 3, "lepedő": 3, "agy nemu": 3, "ágynemű": 3,
        "dekor": 2, "dekoracio": 2, "dekoráció": 2, "vaza": 2, "váza": 2,
        "kepkeret": 2, "képkeret": 2, "falikep": 2, "falikép": 2,
        "tanyer": 3, "tányér": 3, "pohar": 3, "pohár": 3, "bogre": 3, "bögre": 3,
        "evoszett": 3, "evőeszköz": 3, "villa": 2, "kanal": 2, "kanál": 2,
        "otthon": 2, "lakberendezes": 2, "lakberendezés": 2,

        # csaptelep / mosogató környék:
        "csaptelep": 4,
        "mosogatotalca": 3, "mosogatótálca": 3,
        "mosogatotal": 3, "mosogatótál": 3,
        "mosogatotalak": 3, "mosogatótálak": 3,

        # szelektív hulladék, szemetes
        "szemetes": 4, "szemeteslada": 4, "szemetesláda": 4,
        "hulladekgyujto": 4, "hulladékgyűjtő": 4,
        "szelektiv hulladekgyujto": 4, "szelektív hulladékgyűjtő": 4,
        "szelektiv": 2, "szelektív": 2,
        "hulladekkezelo": 2, "hulladékkezelő": 2,
        "kuk": 2, "kuka": 2,
        "tarolo": 2, "tároló": 2,

        # BLANCO kiegészítők, húzógomb stb.
        "huzogomb": 2, "húzógomb": 2,
        "blanco": 1,
    },

    "kert": {
        "kerti": 2, "kerteszeti": 2, "kertészeti": 2,
        "funyiro": 4, "fűnyíró": 4,
        "lancfuresz": 4, "láncfűrész": 4,
        "szegelynyiro": 3, "szegélynyíró": 3,
        "soevényvágó": 3, "sövényvágó": 3,
        "locsolo": 3, "locsoló": 3, "slag": 3, "tomlo": 3, "tömlő": 3,
        "permetező": 3, "permetezogep": 3, "permetezőgép": 3,
        "gereblye": 3, "lapat": 3, "lapát": 3, "aso": 3, "ásó": 3,
        "kapa": 3, "metszoollo": 3, "metszőolló": 3,
        "vetomag": 2, "vetőmag": 2, "viragfold": 2, "virágföld": 2,
        "kerti butor": 3, "kerti bútor": 3, "kerti grill": 3, "grill": 3,
        "napernyo": 3, "napernyő": 3,
        # barkács ide is
        "furógép": 4, "furogep": 4,
        "csavarozó": 3, "csavarhúzó": 3,
        "csiszoló": 3, "flex": 3, "sarokcsiszoló": 3,
        "szerszám": 2, "szerszamkeszlet": 3, "szerszámkészlet": 3,
        "fúrószár": 2,
        "ragaszto pisztoly": 2, "ragasztópisztoly": 2,
        "barkacs": 2, "barkács": 2,
    },

    "jatekok": {
        "lego": 4, "duplo": 4, "playmobil": 4,
        "gyerekjatek": 3, "gyerekjáték": 3,
        "babajatek": 3, "babajáték": 3,
        "tarsasjatek": 4, "társasjáték": 4, "tarsas": 3, "board game": 3,
        "puzzle": 3, "kirako": 3, "kirakó": 3,
        "pluss": 4, "plüss": 4, "plussfigura": 3, "plüssfigura": 3,
        "kisauto": 3, "kisautó": 3, "játékautó": 3, "jatekauto": 3,
        "jatekkonyha": 3, "játékkonyha": 3, "babahaz": 3, "babaház": 3,
        "hintalo": 3, "hintaló": 3,
        "gyurmaszett": 2, "gyurma": 2, "slime": 2,
        "gyerekhaz": 2, "játéksátor": 2, "jateksator": 2,
        "kartyajatek": 3, "kártyajáték": 3, "memoriajatek": 3, "memóriajáték": 3,
    },

    "divat": {
        "polo": 3, "póló": 3, "trikó": 2,
        "pulover": 3, "pulóver": 3, "szvetter": 3,
        "nadrag": 3, "nadrág": 3, "farmer": 3, "leggings": 2,
        "kabát": 3, "dzseki": 3,
        "ruha": 3, "szoknya": 3, "overál": 3, "overall": 3,
        "cipo": 3, "cipő": 3, "csizma": 3, "bakancs": 3,
        "szandál": 3, "papucs": 3,
        "fehernemu": 4, "fehérnemű": 4, "bugyi": 4,
        "melltarto": 4, "melltartó": 4,
        "zokni": 3, "harisnya": 3,
        "taska": 3, "táska": 3, "hátizsák": 3, "hátizsak": 3,
        "öv": 2,
        "sapka": 2, "sal": 2, "sál": 2, "kesztyű": 2, "kesztyu": 2,
        "ora": 3, "óra": 3, "karora": 3, "karóra": 3,
        "ekszer": 3, "ékszer": 3, "nyaklánc": 3, "nyaklanc": 3,
        "karkötő": 3, "karkoto": 3, "gyuru": 3, "gyűrű": 3,
        "divat": 2, "fashion": 2,
    },

    "szepseg": {
        "sampon": 3, "tusfurdo": 3, "tusfürdő": 3,
        "testapolo": 3, "testápoló": 3,
        "kezkrém": 3, "kezkrem": 3,
        "arckrem": 3, "arckrém": 3, "hidratalo": 2, "hidratáló": 2,
        "szérum": 3, "szerum": 3,
        "smink": 3, "alapozo": 3, "alapozó": 3,
        "koromlakk": 3, "körömlakk": 3,
        "szempillaspiral": 3, "szempillaspirál": 3,
        "ruzs": 3, "rúzs": 3,
        "dezodor": 3, "deo": 2,
        "parfum": 3, "parfüm": 3, "eau de toilette": 3,
        "borotva": 3, "borotvagep": 3, "epilator": 3, "epilátor": 3,
        "hajszarito": 3, "hajszárító": 3, "hajvasalo": 3, "hajvasaló": 3,
        "hajgöndörítő": 3, "hajgondorito": 3,
        "kozmetikum": 2, "kozmetika": 2, "wellness": 2,
    },

    "sport": {
        "futópad": 4, "futopad": 4,
        "szobabicikli": 4, "szobakerékpár": 4,
        "elliptikus": 3, "evezőpad": 3,
        "súlyzó": 3, "sulyzo": 3, "kettlebell": 3,
        "edzopad": 3, "edzőpad": 3, "fekvenyomó": 3,
        "fitnesz": 3, "fitness": 3, "trx": 3,
        "jogaszőnyeg": 3, "jogaszonyeg": 3, "yoga mat": 3,
        "labda": 2, "focilabda": 3, "kosarlabda": 3, "kosárlabda": 3,
        "pingpong": 3, "asztalitenisz": 3,
        "bicikli": 3, "kerekpar": 3, "kerékpár": 3,
        "roller": 3, "gördeszka": 3, "gordeszka": 3, "longboard": 3,
        "sátor": 3, "sator": 3,
        "halozsak": 3, "hálózsák": 3,
        "túrazsák": 3, "turazsak": 3, "trekking": 2,
        "turabol": 2, "turacipo": 2, "túracipő": 2,
        "sportszer": 2, "sportfelszereles": 2, "sporteszköz": 2,
    },

    "latas": {
        "kontaktlencse": 4, "lencse": 3,
        "lencsefolyadek": 4, "lencsefolyadék": 4,
        "szemcsepp": 4, "mukonny": 3, "műkönny": 3,
        "optika": 3, "optikai": 3,
        "szemuveg": 3, "szemüveg": 3,
        "napszemuveg": 3, "napszemüveg": 3,
        "dioptria": 3,
        "lencsetarto": 2, "lencsetartó": 2,
    },

    "allatok": {
        "kutyatap": 4, "kutyatáp": 4, "kutyaeledel": 4,
        "macskatáp": 4, "macskaeledel": 4,
        "jutalomfalat": 3,
        "poraz": 3, "póráz": 3, "nyakorv": 3, "nyakörv": 3, "ham": 3, "hám": 3,
        "fekhely": 3, "kutyafekhely": 3, "macskafekhely": 3,
        "kaparofa": 3, "kaparo fa": 3,
        "macskaalom": 4, "alomtálca": 3, "alomtalca": 3,
        "terrarium": 3, "terrárium": 3, "akvarium": 3, "akvárium": 3,
        "haleledel": 3, "haleleség": 3,
        "hörcsög": 2, "hörcsog": 2, "nyul": 2, "nyúl": 2,
        "madáreleség": 2, "madareleseg": 2,
        "allatelede": 2, "állateledel": 2, "allatfelszereles": 2,
    },

    "konyv": {
        "konyv": 4, "könyv": 4, "regeny": 3, "regény": 3,
        "krimi": 3, "roman": 3, "románc": 3,
        "mesekonyv": 3, "mesekönyv": 3, "gyerekkonyv": 3, "gyerekkönyv": 3,
        "szakkonyv": 3, "szakkönyv": 3, "tankonyv": 3, "tankönyv": 3,
        "munkafuzet": 3, "munkafüzet": 3,
        "album": 3, "enciklopedia": 3, "enciklopédia": 3,
        # írószer
        "fuzet": 3, "füzet": 3, "jegyzetfuzet": 3, "jegyzetfüzet": 3,
        "spiralfuzet": 3, "spirálfüzet": 3,
        "toll": 3, "ceruza": 3, "filctoll": 3,
        "stabilo": 2, "marker": 2, "tuzogep": 2, "tűzőgép": 2,
        "irattarto": 2, "irattartó": 2, "mappa": 2,
        "iro szer": 2, "irószer": 2,
    },

    "utazas": {
        "borond": 4, "bőrönd": 4,
        "utazotaska": 4, "utazótáska": 4,
        "trolley": 3, "kézipoggyász": 3, "kezipoggyasz": 3,
        "utazó párna": 3, "utazoparna": 3, "nyakparna": 3, "nyakpárna": 3,
        "utazokészlet": 3, "utazokeszlet": 3, "neszesszer": 3,
        "autós tartó": 3, "autos tarto": 3, "autós telefontartó": 3,
        "gps": 3, "navigacio": 3, "navigáció": 3,
        "csomagrögzítő": 3, "csomagrogzito": 3,
        "tetobox": 3, "tetőbox": 3,
        "utazasi": 2, "utazas": 2, "travel": 2,
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
    """Az TEXT_TAG_KEYS mezőket összefűzi egy nagy szöveggé."""
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
