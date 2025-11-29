# scripts/category_guard.py
#
# "Guard" réteg a model_alza.pkl (és később más modellek/szabályok) fölé.
# Cél: a túl tág / félrement kategóriákat finomítani vagy biztonságos helyre tenni.
#
# Első körben: ELEKTRONIKA-család (elektronika, szamitastechnika, mobiltelefon,
# gaming, smart_home, haztartasi_gepek, konyha_fozes).

import unicodedata
import re

# Ugyanaz a 25 kategória, mint a build_alza.py-ben
FINDORA_CATS = [
    "elektronika",
    "haztartasi_gepek",
    "szamitastechnika",
    "mobiltelefon",
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


def _norm_text(s: str) -> str:
    """
    Lowercase, ékezetmentesítés, whitespace normalizálás.
    Minden döntést ezen a normált szövegen hozunk.
    """
    if not s:
        return ""
    s = str(s)
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _has_any(text: str, keywords) -> bool:
    """
    Ellenőrzi, hogy a normált 'text'-ben szerepel-e bármelyik keyword.
    Kulcsszókat sima részszóként kezeljük, néhányat regex-szel.
    """
    if not text:
        return False
    for kw in keywords:
        if kw in text:
            return True
    return False


# ===== ELEKTRONIKA CSALÁD KULCSSZAVAK =====

# Tiszta "szórakoztató elektronika": TV, hangfal, hifi, stb.
ELEK_CORE = [
    " tv ",
    " televizio",
    " projektor",
    " soundbar",
    " hazimozi",
    " erosit",
    " dvd lejatszo",
    " blu ray",
    " hifi",
    " hangfalszett",
    " hangszoro",
]

# Számítástechnika (ide szeretnénk tenni a model által "elektronika" alá dobott PC-s cuccokat)
PC_CORE = [
    " laptop",
    " notebook",
    " ultrabook",
    " macbook",
    " asztali pc",
    " gamer pc",
    " pc haz",
    " alaplap",
    " videokartya",
    " grafikus kartya",
    " ssd ",
    " hdd ",
    " merevlemez",
    " ram ",
    " memoriakartya",
    " pendrive",
    " router",
    " switch ",
    " modem",
    " billentyuzet",
    " keyboard",
    " eger ",
    " mouse",
    " monitor",
    " kijelzo",
    " dokkolo",
    " docking station",
]

# Mobil & kiegészítők
MOBIL_CORE = [
    " okostelefon",
    " mobiltelefon",
    " smartphone",
    " iphone",
    " androidos telefon",
    " samsung galaxy",
    " xiaomi ",
    " oppo ",
    " oneplus",
    " telefon tok",
    " telefontok",
    " folia ",
    " kijelzovedo",
    " powerbank",
    " vezetek nelkuli tolto",
    " wireless charger",
    " fules ",
    " fulhallgato",
    " headset",
    " earbuds",
    " airpods",
]

# Gaming
GAMING_CORE = [
    " jatek konzol",
    " jatekkonzol",
    " playstation",
    " ps4 ",
    " ps5 ",
    " xbox",
    " nintendo switch",
    " gaming szek",
    " gamer szek",
    " gaming asztal",
    " gamer asztal",
    " gaming billentyuzet",
    " gamer billentyuzet",
    " gaming eger",
    " gamer eger",
    " gaming fejhallgato",
    " gamer fejhallgato",
    " gaming fulhallgato",
]

# Smart Home
SMART_HOME_CORE = [
    " okos otthon",
    " smart home",
    " okosizz",
    " smart bulb",
    " okos lampa",
    " okos dugasz",
    " smart plug",
    " okos konektor",
    " wifi kamera",
    " ip kamera",
    " biztonsagi kamera",
    " okos termosztat",
    " okos zar",
    " smart lock",
    " okos fust",
    " smart smoke",
]

# Háztartási gépek (nagy + kisebb gépek)
GEPEK_CORE = [
    " mosogep",
    " mosogatogep",
    " szaritogep",
    " hutogep",
    " hutolada",
    " fagyaszto",
    " főzől",
    " fozo lap",
    " sutő",
    " sutő ",
    " porszivo",
    " robotporszivo",
    " goztisztito",
    " gőztisztit",
    " vasalo",
    " parologtat",
]

# Konyhai kisgépek
KONYHA_CORE = [
    " botmixer",
    " turmixgep",
    " turmix gep",
    " konyhai robot",
    " konyhai robotgep",
    " kavefozo",
    " eszpresszo gep",
    " kapszulas kavefozo",
    " kenyérpirit",
    " kenyersuto",
    " goffrisuto",
    " gofrisuto",
    " vizforralo",
    " konyhai merleg",
]


def _guard_elek_family(predicted: str, text_norm: str) -> str:
    """
    ELEKTRONIKA család felügyelője.
    Csak akkor piszkál bele, ha a predicted a "közeli" kategóriák egyike.
    """
    p = (predicted or "").strip()

    # Csak ezekre reagálunk első körben
    related = {
        "elektronika",
        "szamitastechnika",
        "mobiltelefon",
        "gaming",
        "smart_home",
        "haztartasi_gepek",
        "konyha_fozes",
    }
    if p not in related:
        return p

    # 1) Ha nagyon nyilvánvaló PC / IT → szamitastechnika
    if _has_any(text_norm, PC_CORE):
        return "szamitastechnika"

    # 2) Ha nagyon nyilvánvaló mobil / headset / powerbank → mobiltelefon
    if _has_any(text_norm, MOBIL_CORE):
        return "mobiltelefon"

    # 3) Ha tipikus gaming cucc → gaming
    if _has_any(text_norm, GAMING_CORE):
        return "gaming"

    # 4) Ha tipikus smart home → smart_home
    if _has_any(text_norm, SMART_HOME_CORE):
        return "smart_home"

    # 5) Ha klasszikus háztartási gép → haztartasi_gepek
    if _has_any(text_norm, GEPEK_CORE):
        return "haztartasi_gepek"

    # 6) Ha konyhai kisgép → konyha_fozes
    if _has_any(text_norm, KONYHA_CORE):
        return "konyha_fozes"

    # 7) Ha tényleg "elektronika" (TV, hifi, stb.), akkor maradhat
    if _has_any(text_norm, ELEK_CORE):
        return "elektronika"

    # 8) Ha ide estünk be, de semmi nem bizonyítható, NE erőltessük:
    # marad az eredeti predicted (vagy ha az eleve hülyeség lenne, a hívó kód teheti multi-ba).
    return p


def finalize_category_for_alza(predicted: str, title: str, desc: str, category_path: str) -> str:
    """
    Alza-specifikus végső kategória választás:
    - 'predicted' jön a model_alza.pkl-ből
    - title + desc + category_path → guard logika (első körben elektronika-család)

    VISSZAAD:
      - egy FINDORA_CATS slugot
    """
    text_norm = _norm_text(" ".join([title or "", desc or "", category_path or ""]))
    p = (predicted or "").strip()

    # Elektronika-család guard
    p2 = _guard_elek_family(p, text_norm)

    # Biztonsági háló: ha valami ismeretlen jön ki, menjen 'multi'-ba
    if p2 not in FINDORA_CATS:
        p2 = "multi"

    return p2
