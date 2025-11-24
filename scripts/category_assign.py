# category_assign_alza.py
"""
ALZA termékkategória besorolás a 25 végső Findora kategóriába.

A szabályrendszer dokumentált és könnyen követhető, hogy minden termék a megfelelő
főkategóriába kerüljön, elkerülve a félrekategorizálást. A besorolás elsősorban 
a termék `category_path` (kategória-útvonal) alapján történik.

Fő kategóriák (slug formában referenciaként):
- elektronika
- haztartasi_gepek
- szamitastechnika
- mobil
- gaming
- smart_home
- otthon
- lakberendezes
- konyha_fozes
- kert
- jatekok
- divat
- szepseg
- drogeria
- baba
- sport
- egeszseg
- latas
- allatok
- konyv
- utazas
- iroda_iskola
- szerszam_barkacs
- auto_motor
- multi

A logika rétegekre bontva:
1. **Specifikus útvonal előtag felülbírálatok (PATH_OVERRIDES):** 
   Előre ismert, problémás kategória-útvonalak egyedi kezelése.
2. **Első szintű kategória (category_root) alapú besorolás (ROOT_MAP):** 
   A fő kategória-gyökér alapján tipikusan eldönthető a besorolás.
   Néhány többértelmű esetben ideiglenesen `None`, ezeket a 3. lépés finomítja.
3. **Kulcsszavas finomítás a többértelmű root-oknál:** 
   Bizonyos gyökérkategóriák (pl. "Játék, baba-mama", "Drogéria", "Otthon, barkács, kert", "Illatszer, ékszer") 
   esetén a `category_path` és termékszöveg alapján döntjük el a pontos besorolást 
   (pl. baba vs. játékok, otthon vs. kert vs. barkács, stb.).
4. **Végső visszafogott fallback:** 
   Ha az előzőek egyike sem adott kategóriát, néhány kulcsszó alapján 
   (pl. "könyv", "allat", "sport", "okosora") még megpróbáljuk besorolni. 
   Ennek hiányában a termék a "multi" (általános/vegyes) kategóriába kerül.
"""

from __future__ import annotations
import re
import unicodedata
from typing import Dict, List, Tuple, Optional

# ====== ALAPÉRTELMEZETT KATEGÓRIA, ha semmi más nem illik ======
DEFAULT_FALLBACK_CATEGORY = "multi"

def normalize_text(text: str) -> str:
    """
    Egyszerű szöveg-normalizáló függvény:
    - Kisbetűssé alakít
    - Eltávolítja az ékezeteket
    - Nem alfanumerikus karaktereket szóközzel helyettesít
    - Többszörös szóközöket egy szóközre szűkít
    """
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)  # ékezetek lebontása
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")  # ékezetek elhagyása
    text = re.sub(r"[^a-z0-9]+", " ", text)    # nem betű vagy szám -> szóköz
    text = re.sub(r"\s+", " ", text).strip()
    return text

def split_category_path(category_path: str) -> Tuple[str, str, str]:
    """
    Visszaadja a kategória-útvonal első három szintjét (ha van).
    Ha kevesebb szint van, a hiányzókat üres stringgel tölti ki.
    Példa: 
        "Otthon, barkács, kert|Világítástechnika|Asztali lámpák" -> 
        ("Otthon, barkács, kert", "Világítástechnika", "Asztali lámpák")
    """
    if not category_path:
        return "", "", ""
    parts = [p.strip() for p in str(category_path).split("|")]
    p1 = parts[0] if len(parts) > 0 else ""
    p2 = parts[1] if len(parts) > 1 else ""
    p3 = parts[2] if len(parts) > 2 else ""
    return p1, p2, p3

# ====== 1. RÉTEG – SPECIFIKUS PATH-PREFIX OVERRIDES ======
# Olyan kategória útvonal előtagok listája, amelyekhez előre meghatározunk egyértelmű besorolást.
# Ezek tipikusan olyan esetek, ahol az általános logika félrekategorizált volna.
PATH_OVERRIDES: List[Tuple[str, str]] = [
    # Utazás – bőröndök a Sport alatt (szabadidőhöz sorolt bőröndök valójában utazási kellékek)
    ("Sport, szabadidő|Hátizsák - táska|Bőröndök", "utazas"),
    # Látás – szemüvegek az Egészségmegőrzés alatt
    ("Egészségmegőrzés|Szemüvegek", "latas"),
    ("Egészségmegőrzés|Gyógyászati segédeszközök|Reszpirátorok, maszkok és pajzsok|Szem védelme|Szemüvegek", "latas"),
    # Lakberendezés – bútoros és lakber kategóriák az Otthon gyökér alatt
    ("Otthon, barkács, kert|Bútorok és lakberendezés", "lakberendezes"),
    ("Otthon, barkács, kert|Lakberendezési kellékek", "lakberendezes"),
    ("Otthon, barkács, kert|Lakberendezési kiegészítők", "lakberendezes"),
    # Állatok – állateledel és felszerelés mindig allatok kategória
    ("Otthon, barkács, kert|Állateledel és felszerelés", "allatok"),
    ("Állateledel és felszerelés", "allatok"),  # ha esetleg önmagában jelenne meg
    # Szerszám & barkács – barkács eszközök ne menjenek általános otthon kategóriába
    ("Otthon, barkács, kert|Szerszámok", "szerszam_barkacs"),
    ("Otthon, barkács, kert|Kéziszerszámok", "szerszam_barkacs"),
    ("Otthon, barkács, kert|Műhely felszerelés", "szerszam_barkacs"),
    ("Otthon, barkács, kert|Építőipar", "szerszam_barkacs"),
    # Drogéria|Baba-mama – drogéria alatt lévő baba-mama kategóriák teljes ágát a baba fő kategóriába soroljuk
    ("Drogéria|Baba-mama", "baba"),
    # Játék, baba-mama|Állatfigurák – ez játék kategória (gyerekjáték figurák), ne kerüljön az állatok közé
    ("Játék, baba-mama|Állatfigurák", "jatekok"),
    # Kerékpár kenőanyagok – sport maradjon (ne sorolja drogeria alá a tisztítószerek miatt)
    ("Sport, szabadidő|Kerékpározás|Kenőanyagok és tisztítószerek", "sport"),
    # Divat – Illatszer, ékszer alatt az ékszerek és órák alkategóriákat a divat kategóriába soroljuk
    ("Illatszer, ékszer|Ékszer", "divat"),
    ("Illatszer, ékszer|Óra", "divat"),
]

# ====== 2. RÉTEG – ROOT (ELSŐ SZINT) ALAPÚ MAPPING ======
# A category_root (felső szintű kategória) normalizált neve alapján történő alap besorolás.
# Az érték None, ha az adott gyökérkategória többféle végső kategóriára bontható – ezekhez a 3. lépés ad logikát.
ROOT_MAP: Dict[str, Optional[str]] = {
    # Magyar nyelvű gyökér kategóriák
    "pc es laptop": "szamitastechnika",
    "telefon tablet okosora": "mobil",
    "tv foto audio video": "elektronika",
    "gaming es szorakozas": "gaming",
    "haztartasi kisgep": "haztartasi_gepek",
    "haztartasi nagygep": "haztartasi_gepek",
    "sport szabadido": "sport",
    "illatszer ekszer": None,         # tovább bontjuk (szépség vs divat) a 3. lépésben
    "egeszsegmegorzes": "egeszseg",
    "elelmiszer": "egeszseg",        # pl. teák, vitaminok mehetnek az egészség kategóriába
    "auto motor": "auto_motor",
    "irodai felszereles": "iroda_iskola",
    "iroda es iskola": "iroda_iskola",
    "allateledel es allattartas": "allatok",
    "konyv e konyv": "konyv",
    "konyha haztartas": "konyha_fozes",
    "okosotthon": "smart_home",
    # Többértelmű gyökerek, finomításuk lentebb:
    "jatek baba mama": None,    # Játék, baba-mama (gyerekjáték vs. baba termékek)
    "jatekok baba mama": None,  # (néha így is előfordulhat szóköz/ékezet eltérés miatt)
    "drogeria": None,          # Drogéria (általános drogéria vs. baba alág)
    "sport a outdoor": "sport", # (angol/cseh "sport a outdoor" -> sport)
    "dum dilna a zahrada": None, # (cseh "ház, műhely és kert" -> bontjuk)
    "hracky pro deti a miminka": None, # (cseh "játékok és babák" -> bontjuk)
    # Idegen nyelvű (cseh/angol) gyökerek lefordítása
    "pocitace a notebooky": "szamitastechnika",
    "mobily chytre hodinky tablety": "mobil",
    "tv foto audio video (idegen)": "elektronika",  # esetleges nyelvi variáns "audio-video" normálva ugyanaz lesz
    "auto moto": "auto_motor",
    "drogerie": None,
    "lekarny a zdravi": "egeszseg",
    "kuchynske a domaci potreby": "konyha_fozes",
}

# Megjegyzés: A fenti kulcsok mind normalizált (kisbetűs, ékezet- és írásjelmentes) formában vannak.

# ====== 3. RÉTEG – KULCSSZÓ CSOMAGOK A FINOMÍTÁSHOZ ======
# Az alábbi listák kulcsszavai segítenek eldönteni a többértelmű gyökérkategóriák pontos besorolását.
BABY_KEYWORDS = [
    "pelenka", "popsitorlo", "baba ", "babat", "babaszoba", 
    "babakocsi", "bundazsak", "cumisuveg", "cumi", 
    "szoptatos", "kismama"
]
KERT_KEYWORDS = [
    "kert", "kerti", "locsolo", "ontozes", "onto berendezes", 
    "fukaszalo", "lancfuresz", "fukasza", "sovenynyiro"
]
BARKACS_KEYWORDS = [
    "szerszam", "csavarhuzo", "csavarhuzo keszlet", "furogep", "furo", 
    "furesz", "csiszolo", "kalapacs", "szerszamkoffer", "ragasztopisztoly", 
    "forrasztopaka", "multiszerszam", "multitool", "krova", "krovakeszlet"
]
LAKBER_KEYWORDS = [
    "diszparna", "fali dekoracio", "faldekor", "kepkeret", "poszter", 
    "falikep", "vaza", "lakastextil", "parna", "agynemu"
]
KONYV_KEYWORDS = [
    " konyv", " regeny", " szakkonyv", "novella", "mesekonyv"
]
DIVAT_KEYWORDS = [
    "ora", "karora", "ekszer", "nyaklanc", "fulbevalo", "karkoto", "gyuru", "ora "
]

def _has_any(text: str, keywords: List[str]) -> bool:
    """Igazat ad vissza, ha a normalizált szöveg bármelyik kulcsszót tartalmazza."""
    return any(kw in text for kw in keywords)

def assign_alza_category(category_path: str, title: str = "", desc: str = "") -> str:
    """
    ALZA-specifikus kategorizáló függvény – visszaad egy Findora fő kategória slugot.
    
    Paraméterek:
        category_path: pl. "Otthon, barkács, kert|Világítástechnika|Asztali lámpák"
        title:         a termék neve/címe (opcionális, kontextusnak)
        desc:          a termék leírása (opcionális, kontextusnak)
    """
    category_path = category_path or ""
    title = title or ""
    desc = desc or ""
    # Normalizált szövegváltozatok előállítása
    first, second, third = split_category_path(category_path)
    root_raw = first or ""
    root_norm = normalize_text(root_raw)
    path_norm = normalize_text(category_path)
    text_norm = normalize_text(title + " " + desc)
    
    # 1) Specifikus útvonal felülbírálatok (pontos prefix egyezéssel, nem normalizált path alapján)
    for prefix, cat_slug in PATH_OVERRIDES:
        if category_path.startswith(prefix):
            return cat_slug
    
    # 2) Root alapú besorolás (gyors döntés az első szint alapján)
    base_cat = ROOT_MAP.get(root_norm)
    
    # 3) Többértelmű gyökerek finomítása kulcsszavakkal
    # 3.1 Játék, baba-mama -> 'jatekok' vagy 'baba'
    if base_cat is None and root_norm in ("jatek baba mama", "jatekok baba mama", "hracky pro deti a miminka"):
        if _has_any(path_norm, BABY_KEYWORDS) or _has_any(text_norm, BABY_KEYWORDS):
            base_cat = "baba"
        else:
            base_cat = "jatekok"
    # 3.2 Drogéria -> 'drogeria' vagy (ha baba kulcsszó van) 'baba'
    if base_cat is None and root_norm in ("drogeria", "drogerie"):
        if _has_any(path_norm, BABY_KEYWORDS) or _has_any(text_norm, BABY_KEYWORDS):
            base_cat = "baba"
        else:
            base_cat = "drogeria"
    # 3.3 Otthon, barkács, kert -> 'kert' / 'szerszam_barkacs' / 'lakberendezes' / egyéb esetben 'otthon'
    if base_cat is None and root_norm in ("otthon barkacs kert", "dum dilna a zahrada"):
        if _has_any(path_norm, KERT_KEYWORDS) or _has_any(text_norm, KERT_KEYWORDS):
            base_cat = "kert"
        elif _has_any(path_norm, BARKACS_KEYWORDS) or _has_any(text_norm, BARKACS_KEYWORDS):
            base_cat = "szerszam_barkacs"
        elif _has_any(path_norm, LAKBER_KEYWORDS) or _has_any(text_norm, LAKBER_KEYWORDS):
            base_cat = "lakberendezes"
        else:
            base_cat = "otthon"
    # 3.4 Illatszer, ékszer -> 'szepseg' vagy (ha ékszer/óra kulcsszó van) 'divat'
    if base_cat is None and root_norm == "illatszer ekszer":
        if _has_any(path_norm, DIVAT_KEYWORDS) or _has_any(text_norm, DIVAT_KEYWORDS):
            base_cat = "divat"
        else:
            base_cat = "szepseg"
    # 3.5 (Biztonság kedvéért) Konyha, háztartás -> alapértelmezetten 'konyha_fozes'
    if base_cat is None and root_norm == "konyha haztartas":
        base_cat = "konyha_fozes"
    # 3.6 Élelmiszer -> ha valamiért nem került egeszseg-re fent, itt ráállítjuk
    if base_cat is None and root_norm == "elelmiszer":
        base_cat = "egeszseg"
    
    # 4) Végső fallback: ha még mindig nincs kategória, néhány kulcsszó alapján megpróbáljuk besorolni
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

# ====== KOMPATIBILITÁSI WRAPPER – RÉGI KÓDHOZ INTEGRÁLÁS ======
def assign_category(partner: str, category_root: str, category_path: str, title: str, desc: str) -> Tuple[str, str]:
    """
    Általános kategória hozzárendelő interfész a build_* scriptjeink számára.
    Visszatérési érték: (findora_main, cat) – jelenleg mindkettő ugyanaz a slug string.
    Jelen implementációban, ha a partner "alza", az ALZA-specifikus logika fut.
    Egyéb partner esetén is jelenleg ugyanez fut, de a későbbiekben bővíthető.
    """
    partner = (partner or "").lower().strip()
    # Partner-specifikus logika (jelenleg csak alza speciális, más esetben is ezt használjuk)
    slug = assign_alza_category(category_path, title, desc)
    return slug, slug

# Példa manuális tesztesetek (futtatható, ha a fájlt önállóan futtatjuk)
if __name__ == "__main__":
    test_samples = [
        ("Autó-motor|Autókozmetika|Autó külső|Polírozás, mosás", "Autó sampon Turtle Wax", ""),
        ("Otthon, barkács, kert|Szerszámok|Csavarhúzók", "Bosch csavarhúzó készlet", ""),
        ("Otthon, barkács, kert|Kert|Ültetés", "Ültető lapát", ""),
        ("Otthon, barkács, kert|Lakberendezési kellékek|Fali dekorációk", "Vászon falikép", ""),
        ("Sport, szabadidő|Hátizsák - táska|Bőröndök|Tartozékok|Mérlegek", "Bőröndmérleg Emos PT-506", ""),
        ("Egészségmegőrzés|Szemüvegek", "SPY HALE 58 Matte Black", ""),
        ("Drogéria|Baba-mama|Pelenkák", "Pelenka 0-3 kg", ""),
        ("Játék, baba-mama|Bébijátékok", "Rágóka újszülöttnek", ""),
        ("Játék, baba-mama|Társasjátékok", "Monopoly Gamer társasjáték", ""),
        ("Illatszer, ékszer|Ékszerek|Nyakláncok", "Arany nyaklánc 14k", ""),
    ]
    for cp, title, desc in test_samples:
        print(f"{cp} => {assign_alza_category(cp, title, desc)}")
