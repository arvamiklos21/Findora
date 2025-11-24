# category_assign.py
"""
Speciális ALZA kategorizáló Findora számára.

Három rétegű logika:
1) Kiemelt prefix- / path-override szabályok (legmagasabb prioritás).
2) Felső + második szint (category_path részek) -> Findora fő kategória (slug).
3) Kulcsszó-alapú finomhangolás a category_path + title + desc szövegeken.

Kimenet: Findora kategória SLUG (pl. "elektronika", "haztartasi_gepek", "szerszam_barkacs", "auto_motor", ...).
Ha nem tud dönteni, "multi" kategóriát ad vissza (konfigurálható).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Tuple, Optional


# ====== FINDORA FŐ KATEGÓRIA SLUGOK (referencia) ======
# Elektronika                  -> elektronika
# Háztartási gépek             -> haztartasi_gepek
# Számítástechnika             -> szamitastechnika
# Mobil & kiegészítők          -> mobil
# Gaming                       -> gaming
# Smart Home                   -> smart_home
# Otthon                       -> otthon
# Lakberendezés                -> lakberendezes
# Konyha & főzés               -> konyha_fozes
# Kert                         -> kert
# Játékok                      -> jatekok
# Divat                        -> divat
# Szépség                      -> szepseg
# Drogéria                     -> drogeria
# Baba                         -> baba
# Sport                        -> sport
# Egészség                     -> egeszseg
# Látás                        -> latas
# Állatok                      -> allatok
# Könyv                        -> konyv
# Utazás                       -> utazas
# Iroda & iskola               -> iroda_iskola
# Szerszám & barkács           -> szerszam_barkacs
# Autó/Motor & autóápolás      -> auto_motor
# Multi                        -> multi


DEFAULT_FALLBACK_CATEGORY = "multi"  # ha semmit nem találunk, ide essen


def normalize_text(text: str) -> str:
    """
    Egyszerű normalizáló: kisbetű, ékezetek leszedése, nem alfanumerikus -> szóköz.
    """
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ====== 1. RÉTEG – SPECIFIKUS PATH OVERRIDES ======
# Ha egy category_path ezzel a prefixszel kezdődik, akkor fix kategóriát kap.

PATH_OVERRIDES: Dict[str, str] = {
    # Ékszer -> divat, ne szépség
    "Illatszer, ékszer|Ékszerek": "divat",
    "Illatszer, ékszer|Karórák": "divat",

    # Babaszoba, bababútor -> baba
    "Játék, baba-mama|Babaszoba gyerekszoba": "baba",

    # Drogéria|Baba-mama teljes ág -> baba (baba cuccok)
    "Drogéria|Baba-mama": "baba",

    # Sport, szabadidő|Egészséges ételek -> Egészség (ne sport)
    "Sport, szabadidő|Egészséges ételek": "egeszseg",

    # KERÉKPÁROS KENŐANYAGOK / TISZTÍTÓSZEREK – menjenek sportba, ne drogeriába
    "Sport, szabadidő|Kerékpározás|Kenőanyagok és tisztítószerek": "sport",

    # Lakberendezés – külön fülre
    "Otthon, barkács, kert|Bútorok és lakberendezés": "lakberendezes",
    "Otthon, barkács, kert|Lakberendezési kellékek": "lakberendezes",
    "Otthon, barkács, kert|Lakberendezési kiegészítők": "lakberendezes",

    # Állatos path – ha így jön (bővíthető)
    "Otthon, barkács, kert|Állateledel és felszerelés": "allatok",
    "Állateledel és felszerelés": "allatok",
    # Állatfigurák: menjen baba (gyerekjáték, nem állatok fül)
    "Játék, baba-mama|Állatfigurák": "baba",

    # MAKETTEK / MODELLEZÉS TARTOZÉKOK – JÁTÉK, NE AUTÓ
    "Játék, baba-mama|Autók, vonatok és makettek|Modellezés": "jatekok",

    # Szerszám & barkács – biztosan barkács
    "Otthon, barkács, kert|Szerszámok": "szerszam_barkacs",
    "Otthon, barkács, kert|Kéziszerszámok": "szerszam_barkacs",
    "Otthon, barkács, kert|Műhely felszerelés": "szerszam_barkacs",
    "Otthon, barkács, kert|Festés, tapétázás": "szerszam_barkacs",
    "Otthon, barkács, kert|Építőipar": "szerszam_barkacs",

    # Autós kategóriák biztosan autóba menjenek
    "Autó-motor|Autókozmetika": "auto_motor",
    "Autó-motor|Autó felszerelések": "auto_motor",
    "Autó-motor|Motor felszerelések": "auto_motor",
}


# ====== 2. RÉTEG – FELSŐ SZINT (ELSŐ SEGMENTUM) MAPPING ======

FIRST_LEVEL_MAP: Dict[str, str] = {
    # HU fő prefexek
    "Telefon, tablet, okosóra": "mobil",
    "TV, fotó, audió, videó": "elektronika",
    "PC és laptop": "szamitastechnika",
    "Gaming és szórakozás": "gaming",
    "Játék, baba-mama": "jatekok",
    "Háztartási kisgép": "haztartasi_gepek",
    "Háztartási nagygép": "haztartasi_gepek",
    "Otthon, barkács, kert": "otthon",  # később finomítjuk második szinttel
    "Illatszer, ékszer": "szepseg",
    "Sport, szabadidő": "sport",
    "Autó-motor": "auto_motor",
    "Irodai felszerelés": "iroda_iskola",
    "Drogéria": "drogeria",
    "Egészségmegőrzés": "egeszseg",
    "Élelmiszer": "egeszseg",
    "Konyha, háztartás": "konyha_fozes",
    "Okosotthon": "smart_home",

    # CZ prefexek – alap becslés
    "Kancelář a papírnictví": "iroda_iskola",
    "Mobily, chytré hodinky, tablety": "mobil",
    "Dům, dílna a zahrada": "otthon",
    "Domácí a osobní spotřebiče": "haztartasi_gepek",
    "Počítače a notebooky": "szamitastechnika",
    "TV, foto, audio-video": "elektronika",
    "Auto-moto": "auto_motor",
    "Drogerie": "drogeria",
    "Kosmetika, parfémy a krása": "szepseg",
    "Sport a outdoor": "sport",
    "Lékárna a zdraví": "egeszseg",
    "Velké spotřebiče": "haztartasi_gepek",
    "Kuchyňské a domácí potřeby": "konyha_fozes",
    "Hračky, pro děti a miminka": "jatekok",
}


# ====== 2/B RÉTEG – (FELSŐ + MÁSODIK SZINT) FINOMÍTÁS ======
# (first, second) -> Findora kategória

SECOND_LEVEL_MAP: Dict[Tuple[str, str], str] = {
    # Otthon, barkács, kert szétbontása
    ("Otthon, barkács, kert", "Világítástechnika"): "otthon",

    # Kert ágak
    ("Otthon, barkács, kert", "Kert"): "kert",
    ("Otthon, barkács, kert", "Kerti gépek"): "kert",
    ("Otthon, barkács, kert", "Kert dekoráció"): "kert",
    ("Otthon, barkács, kert", "Kerti bútor"): "kert",
    ("Otthon, barkács, kert", "Kerti bútorok"): "kert",
    ("Otthon, barkács, kert", "Kerttechnika"): "kert",
    ("Otthon, barkács, kert", "Öntözéstechnika"): "kert",
    ("Otthon, barkács, kert", "Ültetés"): "kert",

    # Barkács / szerszám ágak
    ("Otthon, barkács, kert", "Barkács"): "szerszam_barkacs",
    ("Otthon, barkács, kert", "Szerszámok"): "szerszam_barkacs",
    ("Otthon, barkács, kert", "Kéziszerszámok"): "szerszam_barkacs",
    ("Otthon, barkács, kert", "Fúrógépek"): "szerszam_barkacs",
    ("Otthon, barkács, kert", "Csiszolók"): "szerszam_barkacs",
    ("Otthon, barkács, kert", "Műhely felszerelés"): "szerszam_barkacs",
    ("Otthon, barkács, kert", "Építőipar"): "szerszam_barkacs",

    # Lakberendezés ágak
    ("Otthon, barkács, kert", "Lakberendezési kellékek"): "lakberendezes",
    ("Otthon, barkács, kert", "Lakberendezési kiegészítők"): "lakberendezes",
    ("Otthon, barkács, kert", "Bútorok és lakberendezés"): "lakberendezes",

    # Konyhai / háztartási kategóriák
    ("Háztartási kisgép", "Konyhai kisgépek"): "haztartasi_gepek",
    ("Háztartási kisgép", "Robotgépek és mixerek"): "haztartasi_gepek",
    ("Háztartási kisgép", "Varró- és hímzőgépek"): "haztartasi_gepek",
    ("Konyha, háztartás", "Konyhai eszközök"): "konyha_fozes",
    ("Konyha, háztartás", "Élelmiszer tárolás"): "konyha_fozes",

    # Játék / baba finomítás
    ("Játék, baba-mama", "Építő- és kirakós játékok"): "jatekok",
    ("Játék, baba-mama", "Bébijátékok"): "baba",
    ("Játék, baba-mama", "Pelenkázás"): "baba",

    # Drogéria + Baba-mama – teljes ág baba (plusz a PATH_OVERRIDE is)
    ("Drogéria", "Baba-mama"): "baba",

    # Iroda finomítás
    ("Irodai felszerelés", "Irodaszerek"): "iroda_iskola",
    ("Irodai felszerelés", "Irodabútorok"): "iroda_iskola",

    # Autós finomítás
    ("Autó-motor", "Autókozmetika"): "auto_motor",
    ("Autó-motor", "Autó felszerelések"): "auto_motor",
    ("Autó-motor", "Motor felszerelések"): "auto_motor",
}


# ====== 3. RÉTEG – KULCSSZÓS FELÜLÍRÓ SZABÁLYOK ======
# (kulcsszó lista, cél kategória)

KEYWORD_RULES: List[Tuple[List[str], str]] = [
    # Állatok
    (["kutya", "kutyatap", "kutyajatek", "poraz", "nyakorv", "pet"], "allatok"),
    (["macska", "macskatap", "cicatap", "cicajatek"], "allatok"),
    (["akvarium", "akvarisztika", "terrarium"], "allatok"),

    # Baba – extra erősítés baba cuccokra
    ([
        "pelenka", "pelenkatarto", "babakocsi", "bundazsak",
        "babaagy", "baba agy", "cumisuveg", "etetoszek",
        "bebi or", "babaor", "babatakaro", "babaszoba"
    ], "baba"),

    # Szerszám & barkács
    ([
        "csavarhuzo", "csavarhuzo keszlet", "furogep", "furo",
        "furesz", "csiszolo", "kalapacs", "szerszamkoffer",
        "ragasztopisztoly", "forrasztopaka", "multiszerszam",
        "multitool", "szereloszerszam", "krova", "krovakeszlet",
        "szeg", "csavar", "fogok", "reszelo"
    ], "szerszam_barkacs"),

    # Autó/motor
    ([
        "auto", "autos", "motoros", "autokozmetika",
        "autoolaj", "motorolaj", "szelvedo", "felni"
    ], "auto_motor"),

    # Utazás
    (["utazotaska", "borond", "utazo taska", "utazoparna"], "utazas"),

    # Kert
    (["kerti", "kerti szerszam", "locsolo", "ontozes", "fukaszalo", "lombszivo"], "kert"),

    # Lakberendezés
    ([
        "diszparna", "fali dekoracio", "faldekor", "kepkeret",
        "poszter", "fenyo", "karacsonyfa", "vaza", "lakastextil"
    ], "lakberendezes"),

    # Könyv
    (["konyv", "regeny", "szakkonyv"], "konyv"),

    # Drogéria – extra biztosítás
    (["tisztitoszer", "folttisztito", "mososzer"], "drogeria"),
]


def apply_keyword_rules(norm_text: str) -> Optional[str]:
    """
    Végigmegy a kulcsszó-szabályokon, és ha bármelyik kulcsszó-lista bármely eleme
    szerepel a norm_text-ben, visszaadja a cél kategóriát.
    """
    if not norm_text:
        return None

    for keywords, target_cat in KEYWORD_RULES:
        for kw in keywords:
            if kw in norm_text:
                return target_cat
    return None


def split_category_path(category_path: str) -> Tuple[str, str, str]:
    """
    Visszaadja az első három szintet (ha kevesebb van, üres stringgel tölti ki).
    """
    if not category_path:
        return "", "", ""
    parts = [p.strip() for p in str(category_path).split("|")]
    p1 = parts[0] if len(parts) > 0 else ""
    p2 = parts[1] if len(parts) > 1 else ""
    p3 = parts[2] if len(parts) > 2 else ""
    return p1, p2, p3


def assign_alza_category(category_path: str, title: str = "", desc: str = "") -> str:
    """
    Fő belépési pont: ALZA termék -> Findora kategória SLUG.

    Bemenet:
        category_path: pl. "Otthon, barkács, kert|Világítástechnika|..."
        title:         termék címe
        desc:          termék leírása (opcionális)

    Lépések:
        1) PATH_OVERRIDES – legspecifikusabb prefix szabályok
        2) SECOND_LEVEL_MAP – (first, second) alapján pontosított kategória
        3) FIRST_LEVEL_MAP – csak felső szint alapján
        4) KEYWORD_RULES – cím + path + leírás kulcsszavak alapján felülír
        5) fallback: DEFAULT_FALLBACK_CATEGORY ("multi")
    """
    category_path = category_path or ""
    title = title or ""
    desc = desc or ""

    # 1) PATH_OVERRIDES – prefix-illesztés
    for prefix, cat in PATH_OVERRIDES.items():
        if category_path.startswith(prefix):
            return cat

    # 2) Felső + második szint
    first, second, third = split_category_path(category_path)
    if first and second:
        key = (first, second)
        if key in SECOND_LEVEL_MAP:
            base_cat = SECOND_LEVEL_MAP[key]
        else:
            # 3) csak felső szint
            base_cat = FIRST_LEVEL_MAP.get(first)
    else:
        base_cat = FIRST_LEVEL_MAP.get(first) if first else None

    # 4) Kulcsszavas felülírás
    norm_text = normalize_text(" ".join([category_path, title, desc]))
    kw_cat = apply_keyword_rules(norm_text)
    if kw_cat:
        return kw_cat

    # Ha nincs kulcsszavas felülírás, de van alap kategória, azt adjuk
    if base_cat:
        return base_cat

    # fallback
    return DEFAULT_FALLBACK_CATEGORY


if __name__ == "__main__":
    # Egyszerű kézi teszt – VS Code-ból futtatva megnézheted, mit dob.
    samples = [
        ("Autó-motor|Autókozmetika|Autó külső|Polírozás, mosás", "Autó sampon Turtle Wax", ""),
        ("Otthon, barkács, kert|Szerszámok|Csavarhúzók", "Bosch csavarhúzó készlet", ""),
        ("Otthon, barkács, kert|Műhely felszerelés|Bakok", "Hajtható acél bak", ""),
        ("Otthon, barkács, kert|Lakberendezési kellékek|Fali dekorációk", "Vászon falikép", ""),
        ("Otthon, barkács, kert|Kert|Ültetés", "Ültető lapát", ""),
        ("Játék, baba-mama|Építő- és kirakós játékok|LEGO®", "LEGO City Rendőrkapitányság", ""),
        ("Játék, baba-mama|Autók, vonatok és makettek|Modellezés|Tartozékok", "RC modell kiegészítő", ""),
        ("Játék, baba-mama|Állatfigurák", "Plüss kutyafigura", ""),
        ("Illatszer, ékszer|Ékszerek|Nyakláncok", "Arany nyaklánc", ""),
        ("Drogéria|Gyertyák és illatpálcák|Gyertyák", "Illatgyertya levendula", ""),
        ("PC és laptop|Kiegészítők|PC-hez|Egerek", "Gaming egér RGB", ""),
        ("Telefon, tablet, okosóra|Mobiltelefon tartozékok|Tokok", "Tok iPhone 15 Pro-hoz", ""),
        ("Sport, szabadidő|Kerékpározás|Kenőanyagok és tisztítószerek|Szettek", "Bicikli tisztító szett", ""),
        ("Sport, szabadidő|Egészséges ételek|Diófélék", "Dió mix egészséges snack", ""),
        ("Drogéria|Baba-mama|Babakocsik|Kiegészítők|Esővédők", "Babakocsi esővédő", ""),
        ("Otthon, barkács, kert|Bútorok és lakberendezés|Lakástextil|Törölközők", "Frottír törölköző szett", ""),
    ]
    for cp, t, d in samples:
        print(cp, "=>", assign_alza_category(cp, t, d))
