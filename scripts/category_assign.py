# scripts/category_assign.py
# ==========================
# Központi kategória-hozzárendelés Findorához
#
# interface:
#   assign_category(partner_id, cat_path, title, desc) -> slug
#
# Visszatérési értékek (Findora fő kategória slugok):
#   "elektronika", "haztartasi", "otthon", "kert",
#   "jatekok", "divat", "szepseg", "sport",
#   "latas", "allatok", "konyv", "multi"
# ==========================

import re
import unicodedata

FALLBACK = "multi"


# ---- Segédfüggvények -----------------------------------

def normalize_text(s: str) -> str:
    """Kisbetű, ékezet nélkül, extra szóközök kiszedve."""
    if not s:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def any_kw(haystack: str, keywords) -> bool:
    """True, ha bármely kulcsszó benne van a szövegben."""
    return any(k in haystack for k in keywords)


# ========================================================
#   TCHIBO SZABÁLYOK – marad „light”, hogy ne boruljon
# ========================================================

def assign_tchibo(cat_path: str, title: str, desc: str) -> str:
    t = normalize_text(" ".join(x for x in [cat_path, title, desc] if x))
    c = normalize_text(cat_path)

    # JÁTÉKOK
    if any_kw(t, ["gyerek jatek", "jatek", "pluss", "lego", "kirako", "babajatek"]):
        return "jatekok"

    # DIVAT – ruhák, cipők, kiegészítők
    if any_kw(
        t,
        [
            "noi", "ferfi", "gyerek",
            "ruha", "polo", "bluz", "ing", "nadrag",
            "szoknya", "pulover", "kabat", "kabát",
            "farmer", "leggings", "fehernemu",
            "melltarto", "bugyi", "furdoruha", "bikini",
            "cipo", "csizma", "szandál", "papucs", "taska",
        ],
    ):
        return "divat"

    # SPORT
    if any_kw(t, ["sport", "futas", "fitness", "edzes", "joga", "outdoor"]):
        return "sport"

    # HÁZTARTÁSI GÉPEK
    if any_kw(
        t,
        [
            "porszivo", "porszívó", "robotporszivo",
            "kavefozo", "kavegep", "espresso",
            "mikrohullamu", "mikrohullámú",
            "turmix", "botmixer", "sutitálca", "kenyersuto", "szenzoros kuka",
        ],
    ):
        return "haztartasi"

    # OTTHON
    if any_kw(
        c,
        [
            "otthon", "nappali", "haloszoba", "konyha",
            "furdoszoba", "lakberendezes", "textil", "butor",
        ],
    ):
        return "otthon"

    # Ha semmi nem illik, tegye „multi”-ba
    return FALLBACK


# ========================================================
#   ALZA SZABÁLYOK – itt javítjuk a HÁZTARTÁSI GÉPEK-et
# ========================================================

# Kulcsszó-csomagok

ALZA_HAZTARTASI_ROOTS = {
    "haztartasi kisgep",
    "nagy haztartasi gepek",
}

ALZA_HAZTARTASI_KW = [
    # nagy gépek
    "mosogep", "mosogatogep", "mosogatogep", "mososzarito",
    "szaritogep", "hutogep", "hutoszekreny", "fagyaszto",
    "suto", "sutofelulet", "fozolap",
    # kisgépek, konyha
    "mikrohullamu", "mikrohullamu suto", "konyhai robotgep",
    "robotgep", "kavefozo", "kavegep", "espresszo", "espresso",
    "kenyersuto", "rizsfozo", "gofrisuto", "fritoz", "fritőz",
    "melegszendvicssuto", "tojasfozo",
    "botmixer", "turmix", "smoothie maker", "daralo", "szeletelo",
    "kontakt grill", "raclette", "konyhai merleg",
    # takarítás
    "porszivo", "porszivó", "robotporszivo", "robotporszivo",
    "gőztisztito", "goztisztito", "felmoso", "paratlanito", "légmoso",
    # vasalás
    "vasalo", "gőzállomás", "gozallomas",
]

ALZA_ELEKTRONIKA_ROOTS = {
    "tv, foto, audio, video",
    "tv, fotó, audió, videó",
    "telefon, tablet, okosora",
    "telefon, tablet, okosóra",
    "pc es laptop",
    "pc és laptop",
    "gaming es szorakozas",
    "gaming és szórakozás",
    "okosotthon",
}

ALZA_ELEKTRONIKA_KW = [
    "tv ", "televizio", "monitor",
    "laptop", "notebook", "ultrabook",
    "szamítogep", "szamitogep", "pc haz",
    "jatek konzol", "xbox", "playstation", "ps5", "nintendo",
    "fejhallgato", "headset", "hangszoro", "soundbar",
    "ssd", "hdd", "memoriakartya",
    "wifi router", "router", "switch",
]

ALZA_SPORT_ROOTS = {
    "sport, szabadido",
    "sport, szabadidő",
}

ALZA_SPORT_KW = [
    "kerekpar", "bicikli", "gorkori", "gorkorcsolya",
    "futopad", "orbitrek", "szobabicikli",
    "sator", "hatrizsak", "turabakancs",
    "focilabda", "kosarlabda", "teniszuto",
    "fitnesz", "fitness", "sulyzo", "suly",
    "yoga", "joga",
]

ALZA_JATEK_ROOTS = {
    "jatek, baba-mama",
    "játék, baba-mama",
}

ALZA_JATEK_KW = [
    "lego", "pluss", "tarsasjatek", "tarsasjatekok",
    "jatek", "babakocsi", "babajatek",
    "jatekkonyha", "jatekautó", "jatekauto",
]

ALZA_SZEPSEG_ROOTS = {
    "egeszsegmegorzes",
    "egészségmegőrzés",
    "illatszer, ekszer",
    "illatszer, ékszer",
    "drogeria",
    "drogéria",
}

ALZA_SZEPSEG_KW = [
    "parfum", "parfüm", "smink", "ruzs", "alapozó",
    "borapolas", "bőrápolás",
    "masszazs keszulek", "masszazskeszulek",
    "hajszarito", "hajsuto", "hajvasalo", "hajvago",
    "fogkefe", "szonikus fogkefe",
]

ALZA_OTTHON_ROOTS = {
    "otthon, barkacs, kert",
    "otthon, barkács, kert",
}

ALZA_OTTHON_KW = [
    "fuggony", "parna", "paplan", "agy nemu", "agynemu",
    "szonyeg", "szonyeg", "torolkozo", "lakastextil",
    "polc", "szekreny", "asztal", "szek",
    "dekoracio", "diszparna", "disztargy",
]

ALZA_KERT_KW = [
    "kerti", "kerteshaz", "locsolo", "ontozorendszer",
    "fukaszalo", "fukis gep", "lombszivo", "lombfuvó",
    "magasnyomasu mosó", "magasnyomasu mosó", "magasnyomasu mosó",
    "gazvago", "husvago ollo", "hosszabbito kabel kulteri",
]

ALZA_ALLAT_KW = [
    "macska", "kutya", "allateledel", "allateleség",
    "kaparofa", "nyakorv", "póráz", "allatfekhely",
]

ALZA_LATAS_KW = [
    "tavcso", "binokularis", "binokular",
    "tavcső", "binokulár",
    "szemegyseg", "szemcsepp", "kontaktlencse",
    "szemuveg", "szemüveg",
    "snorkel maszk", "buvarkodó maszk",
]

ALZA_KONYV_KW = [
    "konyv", "regeny", "novella", "szakkonyv", "album",
]


def assign_alza(cat_path: str, title: str, desc: str) -> str:
    raw_cat = cat_path or ""
    raw_text = " ".join(x for x in [cat_path, title, desc] if x)

    cat = normalize_text(raw_cat)
    text = normalize_text(raw_text)

    # root: az első „|” előtti rész
    root = normalize_text(raw_cat.split("|", 1)[0]) if raw_cat else ""

    # ----- 1. HÁZTARTÁSI GÉPEK – EZT FIXÁLJUK -----
    if root in ALZA_HAZTARTASI_ROOTS or any_kw(cat, ALZA_HAZTARTASI_ROOTS):
        return "haztartasi"
    if any_kw(text, ALZA_HAZTARTASI_KW):
        return "haztartasi"

    # ----- 2. ELEKTRONIKA -----
    if root in ALZA_ELEKTRONIKA_ROOTS:
        return "elektronika"
    if any_kw(text, ALZA_ELEKTRONIKA_KW):
        return "elektronika"

    # ----- 3. SPORT -----
    if root in ALZA_SPORT_ROOTS:
        return "sport"
    if any_kw(text, ALZA_SPORT_KW):
        return "sport"

    # ----- 4. JÁTÉKOK -----
    if root in ALZA_JATEK_ROOTS:
        return "jatekok"
    if "jatek" in cat or any_kw(text, ALZA_JATEK_KW):
        return "jatekok"

    # ----- 5. SZÉPSÉG / EGÉSZSÉG -----
    if root in ALZA_SZEPSEG_ROOTS or any_kw(cat, ALZA_SZEPSEG_ROOTS):
        return "szepseg"
    if any_kw(text, ALZA_SZEPSEG_KW):
        return "szepseg"

    # ----- 6. OTTHON -----
    if root in ALZA_OTTHON_ROOTS:
        # Kerti al-kategóriák külön mehetnek „kert”-be
        if any_kw(text, ALZA_KERT_KW):
            return "kert"
        return "otthon"
    if any_kw(text, ALZA_OTTHON_KW):
        return "otthon"

    # ----- 7. KERT (ha máshonnan jön, de tipikusan kerti cucc) -----
    if any_kw(text, ALZA_KERT_KW):
        return "kert"

    # ----- 8. ÁLLATOK -----
    if any_kw(text, ALZA_ALLAT_KW):
        return "allatok"

    # ----- 9. LÁTÁS -----
    if any_kw(text, ALZA_LATAS_KW):
        return "latas"

    # ----- 10. KÖNYV -----
    if any_kw(text, ALZA_KONYV_KW):
        return "konyv"

    # ----- 11. ha semmi nem illik → többnyire „multi” -----
    return FALLBACK


# ========================================================
#   KÖZPONTI BELÉPŐ FÜGGVÉNY
# ========================================================

def assign_category(partner_id: str, cat_path: str, title: str, desc: str) -> str:
    """
    Fő belépő: partner alapján hívja a megfelelő szabályrendszert.
    partner_id: pl. "tchibo", "alza", ...
    """
    pid = (partner_id or "").strip().lower()

    if pid == "tchibo":
        return assign_tchibo(cat_path or "", title or "", desc or "")

    if pid == "alza":
        return assign_alza(cat_path or "", title or "", desc or "")

    # ismeretlen partner – mindent multi-ba dobunk
    return FALLBACK
