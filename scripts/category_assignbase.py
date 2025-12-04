# scripts/category_assignbase.py
#
# Központi, nagyon alap szabály-alapú kategorizáló.
# Minden partner ezt használhatja.
#
# Két fő belépési pont:
#   - assign_category(...)
#   - assign_category_from_fields(fields, partner, partner_default)
#

import re
import unicodedata

# ===== Findora fő kategória SLUG-ok (25) =====
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


# ===== Normalizáló =====

def _normalize_text(s: str) -> str:
    if not s:
        return ""
    s = str(s)
    # ékezetek levétele
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    # kisbetű, whitespace tisztítás
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# ===== Nagyon alap kulcsszó-szabályok =====
#
# Ezek CSAK durva irányt mutatnak; cél:
#   - minél kevesebb multi
#   - de mégse teljes káosz
#
# Ha nem talál semmit, akkor partner_default → ha az sincs, akkor multi.

CATEGORY_KEYWORD_RULES = [
    # elektronika
    (
        "elektronika",
        [
            "televizio", "tv ", " tv", "hangfal", "hangszoro", "hifi",
            "projektor", "erősito", "erosito", "bluetooth hangszoro",
            "radio", "drón", "dron",
        ],
    ),
    # haztartasi_gepek
    (
        "haztartasi_gepek",
        [
            "mosogep", "moso gep", "hutoszekreny", "hutogep",
            "porszivo", "porszívó", "mikrohullamu", "mikrohullamu suto",
            "konyhai robotgep", "piritos", "toaster",
        ],
    ),
    # szamitastechnika
    (
        "szamitastechnika",
        [
            "laptop", "notebook", "monitor", "asztali gep",
            "szamitogep", "videokartya", "alaplap", "processzor",
            "ram memoria", "ssd ", " ssd", "hdd", "egér", "eger", "billentyuzet",
        ],
    ),
    # mobil
    (
        "mobil",
        [
            "okostelefon", "okos telefon", "mobiltelefon", "mobil telefon",
            "iphone", "galaxy s", "xiaomi", "redmi", "oneplus",
            "tok iphone", "telefon tok", "screen protector", "kijelzovedo",
        ],
    ),
    # gaming
    (
        "gaming",
        [
            "gaming", "jatek konzol", "jatek konzol", "playstation",
            "xbox", "nintendo switch", "gamer egér", "gamer eger",
            "gamer billentyuzet", "gamer fejhallgato",
        ],
    ),
    # smart_home
    (
        "smart_home",
        [
            "okosizzó", "okosizzo", "okos otthon", "okos dugalj",
            "wifi izzo", "wi-fi izzo", "smart plug", "smart bulb",
            "kamera rendszer", "biztonsagi kamera",
        ],
    ),
    # otthon
    (
        "otthon",
        [
            "porszivo szuro", "hepa szuro", "parnav", "pléd", "pl ed",
            "matrac", "fuggony", "fuggöny", "agynemu", "takaró", "takaro",
            "szonyeg", "szőnyeg", "roló", "rolo",
        ],
    ),
    # lakberendezes
    (
        "lakberendezes",
        [
            "dekoracio", "dekoráci", "fali dekor", "kepkeret", "kep keret",
            "vaza", "gyertya", "karacsonyi disz", "karacsonyi dekor",
        ],
    ),
    # konyha_fozes
    (
        "konyha_fozes",
        [
            "fazek", "serpenyo", "konyhakés", "konyhakes", "edeny",
            "sutőforma", "suto forma", "kanal", "villa", "kavefozo", "kávéfőző",
        ],
    ),
    # kert
    (
        "kert",
        [
            "kerti szek", "kerti asztal", "kerti butor", "locsolo",
            "fuvvago", "fuvnyiro", "trimmer", "kertiszerszam", "kerti szerszam",
        ],
    ),
    # jatekok
    (
        "jatekok",
        [
            "lego", "playmobil", "barbie", "tarsasjatek", "társasjáték",
            "plussjatek", "plüssjáték", "jatek", "játékszett", "babakocsi jatek",
        ],
    ),
    # divat
    (
        "divat",
        [
            "polo", "póló", "nadrag", "dzseki", "kabát", "kabat",
            "szoknya", "ruha", "cipo", "cipő", "csizma", "pulover", "pulóver",
        ],
    ),
    # szepseg
    (
        "szepseg",
        [
            "parfum", "parfüm", "smink", "alapozó", "szempillaspiral",
            "körömlakk", "koremlakk", "kozmetikum", "borapolo", "bőrápoló",
        ],
    ),
    # drogeria
    (
        "drogeria",
        [
            "mososzer", "mosószer", "oblito", "öblítö", "fertoetlenito",
            "tisztitoszer", "tisztítószer", "wc tisztito",
        ],
    ),
    # baba
    (
        "baba",
        [
            "pelenka", "babakocsi", "járóka", "jároka", "baba etetőszék",
            "baba etetoszek", "babatakaro", "cumisüveg", "cumisuveg",
        ],
    ),
    # sport
    (
        "sport",
        [
            "futócipő", "futocipo", "edzokabat", "futokabat",
            "fitness", "fitnesz", "jóga", "joga", "edzopad", "sulyzo", "súlyzó",
            "labda", "foci labda", "kosarlabda",
        ],
    ),
    # egeszseg
    (
        "egeszseg",
        [
            "vitamin", "taplalekkiegeszito", "taplalkozas kiegeszito",
            "masszazs", "masszírozó", "lazmero", "lázmérő", "vernyomasmero",
        ],
    ),
    # latas
    (
        "latas",
        [
            "kontaktlencse", "kontakt lencse", "napszemuveg", "latasvizsgalat",
        ],
    ),
    # allatok
    (
        "allatok",
        [
            "kutyaeledel", "macskaeledel", "cicatap", "kutyatap",
            "kaparofa", "macskaalom", "kutyafekhely",
        ],
    ),
    # konyv
    (
        "konyv",
        [
            "regeny", "regény", "kepeskonyv", "kepes konyv",
            "gyerekkonyv", "gyerek konyv", "szotar", "szótár",
        ],
    ),
    # utazas
    (
        "utazas",
        [
            "bőrönd", "borond", "utazotaska", "utazótáska",
            "hátizsák", "hatizsak", "nyakpárna utazashoz",
        ],
    ),
    # iroda_iskola
    (
        "iroda_iskola",
        [
            "fuzet", "spiralfuzet", "toll", "ceruza", "filctoll",
            "jegyzettomb", "irattarto", "hatizsak iskolas", "iskolataska",
        ],
    ),
    # szerszam_barkacs
    (
        "szerszam_barkacs",
        [
            "furogep", "fúró", "csavarbehajto", "csavarhúzó", "csavarhuzo",
            "készlet szerszám", "keszlet szerszam", "kulcskeszlet",
        ],
    ),
    # auto_motor
    (
        "auto_motor",
        [
            "autós töltő", "autostolto", "motorolaj", "autoolaj", "szélvédőmosó",
            "szelvedomoso", "autószivargyújtó", "szivargyujto",
        ],
    ),
]


def _match_category_by_keywords(text_norm: str) -> str | None:
    if not text_norm:
        return None

    for cat_slug, keywords in CATEGORY_KEYWORD_RULES:
        for kw in keywords:
            if kw in text_norm:
                return cat_slug
    return None


# ===== FŐ FÜGGVÉNY – KÖZVETLEN PARAMÉTEREK =====

def assign_category(
    title: str = "",
    desc: str = "",
    category_path: str = "",
    brand: str = "",
    partner: str = "",
    partner_default: str = "multi",
) -> str:
    """
    Általános Findora-kategorizáló.
    Ha nem talál semmilyen szabályt, partner_default-ot ad vissza (nem multi-t).
    """

    # szöveg összeépítése
    parts = []
    for v in (category_path, title, desc, brand):
        if v:
            parts.append(str(v))
    full_text_norm = _normalize_text(" | ".join(parts))

    # 1) kulcsszó alapú meccselés
    cat = _match_category_by_keywords(full_text_norm)

    # 2) ha semmi nincs → partner_default (ha az is üres, akkor multi)
    if not cat:
        cat = partner_default or "multi"

    # 3) biztonság kedvéért: ha valami fura slug jött ki
    if cat not in FINDORA_CATS:
        cat = partner_default or "multi"

    return cat


# ===== KÉNYELMI FÜGGVÉNY – fields dict esetén =====

def assign_category_from_fields(
    fields: dict,
    partner: str,
    partner_default: str = "multi",
) -> str:
    """
    Olyan feedekhez, ahol egyetlen dict-ben kapjuk a mezőket, pl.:

      fields = {
        "product_type": "...",
        "category": "...",
        "categorytext": "...",
        "title": "...",
        "description": "...",
        "brand": "...",
      }

    Minden partner (Tchibo, Pepita, stb.) használhatja.
    """

    fields = fields or {}

    # category_path: első nem üres a megszokott kulcsok közül
    category_path = (
        fields.get("product_type")
        or fields.get("category")
        or fields.get("categorytext")
        or ""
    )

    title = (
        fields.get("title")
        or fields.get("name")
        or fields.get("productname")
        or ""
    )

    desc = (
        fields.get("description")
        or fields.get("desc")
        or ""
    )

    brand = fields.get("brand") or ""

    return assign_category(
        title=title,
        desc=desc,
        category_path=category_path,
        brand=brand,
        partner=partner,
        partner_default=partner_default,
    )
