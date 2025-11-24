# category_assign.py
"""
Speciális ALZA (és általános) kategorizáló Findora számára.

Fő elv: először KŐKEMÉNYEN a category_path első szintje ("category_root")
alapján döntünk, és csak a néhány valóban vitás rootnál (Játék/Baba, Drogéria,
Otthon–Barkács–Kert) finomítunk. Kulcsszavak csak ott lépnek be, ahol MUSZÁJ.

Kimenetek:

- assign_alza_category(...) -> egyetlen Findora fő kategória SLUG (pl. "sport")
- assign_category(partner, category_root, category_path, title, desc)
    -> (findora_main, cat) tuple – kompatibilis a régi build_*.py kódokkal

Ha nem tud dönteni, "multi" kategóriát ad vissza (DEFAULT_FALLBACK_CATEGORY).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Tuple, Optional


# ====== FINDORA FŐ KATEGÓRIA SLUGOK (referencia) ======
# elektronika
# haztartasi_gepek
# szamitastechnika
# mobil
# gaming
# smart_home
# otthon
# lakberendezes
# konyha_fozes
# kert
# jatekok
# divat
# szepseg
# drogeria
# baba
# sport
# egeszseg
# latas
# allatok
# konyv
# utazas
# iroda_iskola
# szerszam_barkacs
# auto_motor
# multi

DEFAULT_FALLBACK_CATEGORY = "multi"


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


# ====== 1. RÉTEG – SPECIFIKUS PATH-PREFIX OVERRIDES ======
# Itt mindent olyan cuccot lekezelünk, amire már konkrétan láttunk rossz
# kategóriát, és biztosan tudjuk, hova kell mennie.

PATH_OVERRIDES: List[Tuple[str, str]] = [
    # Utazás – bőrönd, bőrönd kiegészítők sport root alatt
    ("Sport, szabadidő|Hátizsák - táska|Bőröndök", "utazas"),

    # Látás – szemüvegek, védőszemüvegek
    ("Egészségmegőrzés|Szemüvegek", "latas"),
    (
        "Egészségmegőrzés|Gyógyászati segédeszközök|Reszpirátorok, maszkok és pajzsok|Szem védelme|Szemüvegek",
        "latas",
    ),

    # Lakberendezés
    ("Otthon, barkács, kert|Bútorok és lakberendezés", "lakberendezes"),
    ("Otthon, barkács, kert|Lakberendezési kellékek", "lakberendezes"),
    ("Otthon, barkács, kert|Lakberendezési kiegészítők", "lakberendezes"),

    # Állatok
    ("Otthon, barkács, kert|Állateledel és felszerelés", "allatok"),
    ("Állateledel és felszerelés", "allatok"),

    # Szerszám & barkács (biztosan barkács, ne „otthon”)
    ("Otthon, barkács, kert|Szerszámok", "szerszam_barkacs"),
    ("Otthon, barkács, kert|Kéziszerszámok", "szerszam_barkacs"),
    ("Otthon, barkács, kert|Műhely felszerelés", "szerszam_barkacs"),
    ("Otthon, barkács, kert|Építőipar", "szerszam_barkacs"),

    # Drogéria|Baba-mama – teljes ág baba
    ("Drogéria|Baba-mama", "baba"),

    # Állatfigurák – játék, ne „állatok”
    ("Játék, baba-mama|Állatfigurák", "baba"),

    # Kerékpár kenőanyagok – sport maradjon, ne drogeria
    ("Sport, szabadidő|Kerékpározás|Kenőanyagok és tisztítószerek", "sport"),
]


# ====== 2. RÉTEG – ROOT (ELSŐ SZINT) ALAPÚ MAPPING ======

ROOT_MAP: Dict[str, Optional[str]] = {
    # Magyar root-ok
    "pc es laptop": "szamitastechnika",
    "telefon, tablet, okosora": "mobil",
    "tv, foto, audio, video": "elektronika",
    "gaming es szorakozas": "gaming",

    "haztartasi kisgep": "haztartasi_gepek",
    "haztartasi nagygep": "haztartasi_gepek",

    "sport, szabadido": "sport",

    "illatszer, ekszer": "szepseg",
    "egeszsegmegorzes": "egeszseg",
    "elelmiszer": "egeszseg",  # teák, vitamin jellegű cuccok – egészség fülre

    "auto-motor": "auto_motor",
    "irodai felszereles": "iroda_iskola",
    "iroda es iskola": "iroda_iskola",

    "allateledel es allattartas": "allatok",

    "konyv, e-konyv": "konyv",

    "konyha, haztartas": "konyha_fozes",

    "okosotthon": "smart_home",

    # ezek szándékosan „None” → külön finomítjuk:
    "jatek, baba-mama": None,
    "jatekok, baba-mama": None,
    "drogeria": None,
    "otthon, barkacs, kert": None,

    # Cseh/angol variánsok – ha ilyen root jön
    "pocitace a notebooky": "szamitastechnika",
    "mobily, chytre hodinky, tablety": "mobil",
    "tv, foto, audio-video": "elektronika",
    "auto-moto": "auto_motor",
    "drogerie": None,
    "sport a outdoor": "sport",
    "lekarny a zdravi": "egeszseg",
    "kuchynske a domaci potreby": "konyha_fozes",
    "hracky, pro deti a miminka": None,  # játék/baba típus
    "dum, dilna a zahrada": None,        # otthon/barkács/kert
}


# ====== 3. RÉTEG – KULCSSZÓ CSOMAGOK, CSAK FINOMÍTÁSHOZ ======

BABY_KEYWORDS = [
    "pelenka",
    "popsitorlo",
    "baba ",
    "babat",
    "babaszoba",
    "babakocsi",
    "bundazsak",
    "cumisuveg",
    "cumi",
    "szoptatos",
    "kismama",
]

KERT_KEYWORDS = [
    "kert",
    "kerti",
    "locsolo",
    "ontozes",
    "onto berendezes",
    "fukaszalo",
    "lancfuresz",
    "fukasza",
    "sovenynyiro",
]

BARKACS_KEYWORDS = [
    "szerszam",
    "csavarhuzo",
    "csavarhuzo keszlet",
    "furogep",
    "furo",
    "furesz",
    "csiszolo",
    "kalapacs",
    "szerszamkoffer",
    "ragasztopisztoly",
    "forrasztopaka",
    "multiszerszam",
    "multitool",
    "krova",
    "krovakeszlet",
]

LAKBER_KEYWORDS = [
    "diszparna",
    "fali dekoracio",
    "faldekor",
    "kepkeret",
    "poszter",
    "falikep",
    "vaza",
    "lakastextil",
]

KONYV_KEYWORDS = [
    " konyv",
    " regeny",
    " szakkonyv",
]


def _has_any(text: str, keywords: List[str]) -> bool:
    return any(kw in text for kw in keywords)


def assign_alza_category(category_path: str, title: str = "", desc: str = "") -> str:
    """
    Alza-specifikus kategorizáló – VISSZAAD: 1 db Findora kategória SLUG.

    Bemenet:
        category_path: pl. "Otthon, barkács, kert|Világítástechnika|..."
        title:         termék címe
        desc:          termék leírása (opcionális)
    """
    category_path = category_path or ""
    title = title or ""
    desc = desc or ""

    # Normalizált szövegek
    first, second, third = split_category_path(category_path)
    root_raw = first or ""
    root_norm = normalize_text(root_raw)
    path_norm = normalize_text(category_path)
    text_norm = normalize_text(title + " " + desc)

    # 1) PATH_OVERRIDES – prefixek (eredeti, nem normalizált path-on)
    for prefix, cat in PATH_OVERRIDES:
        if category_path.startswith(prefix):
            return cat

    # 2) ROOT_MAP – első szint alapján
    base_cat = ROOT_MAP.get(root_norm)

    # 3) Speciális rootok finomítása

    # 3.1 Játék, baba-mama → jatekok / baba
    if base_cat is None and root_norm in ("jatek, baba-mama", "jatekok, baba-mama", "hracky, pro deti a miminka"):
        if _has_any(path_norm, BABY_KEYWORDS) or _has_any(text_norm, BABY_KEYWORDS):
            base_cat = "baba"
        else:
            base_cat = "jatekok"

    # 3.2 Drogéria → drogeria / baba
    if base_cat is None and root_norm in ("drogeria", "drogerie"):
        if _has_any(path_norm, BABY_KEYWORDS) or _has_any(text_norm, BABY_KEYWORDS):
            base_cat = "baba"
        else:
            base_cat = "drogeria"

    # 3.3 Otthon, barkács, kert → otthon / kert / szerszam_barkacs / lakberendezes
    if base_cat is None and root_norm in ("otthon, barkacs, kert", "dum, dilna a zahrada"):
        if _has_any(path_norm, KERT_KEYWORDS) or _has_any(text_norm, KERT_KEYWORDS):
            base_cat = "kert"
        elif _has_any(path_norm, BARKACS_KEYWORDS) or _has_any(text_norm, BARKACS_KEYWORDS):
            base_cat = "szerszam_barkacs"
        elif _has_any(path_norm, LAKBER_KEYWORDS) or _has_any(text_norm, LAKBER_KEYWORDS):
            base_cat = "lakberendezes"
        else:
            base_cat = "otthon"

    # 3.4 Konyha, háztartás – ha valamiért root_map nem fogta
    if base_cat is None and root_norm == "konyha, haztartas":
        base_cat = "konyha_fozes"

    # 3.5 Élelmiszer – ha ide jutott, menjen egészségre
    if base_cat is None and root_norm == "elelmiszer":
        base_cat = "egeszseg"

    # 4) Ha még mindig nincs kategória, óvatos fallback
    if base_cat is None:
        if _has_any(path_norm, KONYV_KEYWORDS) or _has_any(text_norm, KONYV_KEYWORDS):
            base_cat = "konyv"
        elif "allat" in path_norm or "allat" in text_norm or "pet" in text_norm:
            base_cat = "allatok"
        elif "sport" in path_norm or "fitness" in path_norm:
            base_cat = "sport"
        elif "okosora" in path_norm or "apple watch" in text_norm:
            base_cat = "mobil"
        else:
            base_cat = DEFAULT_FALLBACK_CATEGORY

    return base_cat or DEFAULT_FALLBACK_CATEGORY


# ====== KOMPATIBILITÁSI WRAPPER – RÉGI KÓDOKHOZ ======

def assign_category(
    partner: str,
    category_root: str,
    category_path: str,
    title: str,
    desc: str,
):
    """
    Régi interface a build_*.py scriptekhez.

    Visszatér:
        (findora_main, cat) – itt mindkettő ugyanaz a Findora fő kategória SLUG.

    Jelenleg:
        - ha partner == "alza" -> az ALZA-specifikus assign_alza_category-t használjuk
        - minden más partnernél is ugyanaz a logika fut, de ez később bővíthető
    """
    partner = (partner or "").lower().strip()

    # később ide lehet tenni partner-specifikus külön logikát:
    # if partner == "tchibo": ...
    # if partner == "pepita": ...

    slug = assign_alza_category(category_path, title, desc)
    return slug, slug


if __name__ == "__main__":
    # Egyszerű kézi teszt – VS Code-ból futtatva megnézheted, mit dob.
    samples = [
        ("Autó-motor|Autókozmetika|Autó külső|Polírozás, mosás", "Autó sampon Turtle Wax", ""),
        ("Otthon, barkács, kert|Szerszámok|Csavarhúzók", "Bosch csavarhúzó készlet", ""),
        ("Otthon, barkács, kert|Kert|Ültetés", "Ültető lapát", ""),
        ("Otthon, barkács, kert|Lakberendezési kellékek|Fali dekorációk", "Vászon falikép", ""),
        ("Sport, szabadidő|Hátizsák - táska|Bőröndök|Tartozékok|Mérlegek", "Bőröndmérleg Emos PT-506", ""),
        ("Egészségmegőrzés|Szemüvegek", "SPY HALE 58 Matte Black", ""),
        ("Drogéria|Baba-mama|Pelenkák", "Pelenka 0-3 kg", ""),
        ("Játék, baba-mama|Bébijátékok", "Rágóka újszülöttnek", ""),
        ("Játék, baba-mama|Társasjátékok", "Monopoly Gamer társasjáték", ""),
        ("Sport, szabadidő|Sporttápszerek|Proteinek", "Czech Virus Pure Elite CFM", ""),
    ]
    for cp, t, d in samples:
        print(cp, "=>", assign_alza_category(cp, t, d))
