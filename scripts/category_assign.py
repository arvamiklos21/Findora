# scripts/category_assign.py

import re


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _text_blob(cat_path: str, title: str, desc: str) -> str:
    return " ".join(
        part
        for part in [
            _norm(cat_path),
            _norm(title),
            _norm(desc),
        ]
        if part
    )


# ===== TCHIBO – elég „laza” szabályok, fő fókusz: divat / otthon / játék =====
def _assign_tchibo(cat_path: str, title: str, desc: str) -> str:
    cp = _norm(cat_path)
    t = _norm(title)
    d = _norm(desc)
    txt = " ".join([cp, t, d])

    # Játékok
    if any(w in txt for w in ["játék", "játékok", "plüss", "lego", "puzzle", "társasjáték"]):
        return "jatek"

    # Gyerek / baba dolgok
    if any(w in txt for w in ["baba", "gyerek", "gyermek", "kisfiú", "kislány"]):
        # ha kifejezetten játék, akkor már az előző ág elvitte
        return "otthon"

    # Ruházat, divat
    if any(
        w in txt
        for w in [
            "póló",
            "polo",
            "pulóver",
            "pulover",
            "nadrág",
            "nadrag",
            "farmer",
            "kabát",
            "kabat",
            "dzseki",
            "ruha",
            "szoknya",
            "ing",
            "cipő",
            "cipo",
            "melltartó",
            "fehérnemű",
            "fehernemu",
            "harisnya",
            "leggings",
            "szandál",
            "szandal",
            "sneaker",
            "tunika",
            "kardigán",
            "kardigan",
        ]
    ):
        return "divat"

    # Sport / fitness
    if any(
        w in txt
        for w in [
            "sport",
            "fitness",
            "jóga",
            "joga",
            "futó",
            "futo",
            "kerékpár",
            "kerekpar",
            "úszás",
            "uszas",
            "edző",
            "edzo",
        ]
    ):
        return "sport"

    # Szépség, kozmetika
    if any(
        w in txt
        for w in [
            "kozmetika",
            "kozmetikai",
            "arcápolás",
            "arcapolas",
            "bőr",
            "borápolás",
            "borapolas",
            "smink",
            "illatszer",
            "parfüm",
            "parfum",
        ]
    ):
        return "szepseg"

    # Konyha / háztartási dolgok
    if any(
        w in txt
        for w in [
            "konyha",
            "sütőforma",
            "sutoforma",
            "serpenyő",
            "serpenyo",
            "fazék",
            "fazek",
            "késkészlet",
            "keskeszlet",
            "sütés",
            "sutes",
            "tárolódoboz",
            "tarolodoboz",
            "tároló",
            "tarolo",
            "pohár",
            "pohar",
            "bögre",
            "bogre",
        ]
    ):
        return "haztartasi-gepek"

    # Lakás / dekor / ágynemű, törölköző stb. → Otthon
    if any(
        w in txt
        for w in [
            "lakás",
            "lakas",
            "dekor",
            "dísz",
            "disz",
            "díszpárna",
            "diszparna",
            "függöny",
            "fuggony",
            "szőnyeg",
            "szonyeg",
            "ágynemű",
            "agynemu",
            "törölköző",
            "torolkozo",
            "takaró",
            "takaro",
            "tároló",
            "tarolo",
            "lámpa",
            "lampa",
        ]
    ):
        return "otthon"

    # Default: otthon
    return "otthon"


# ===== ALZA – itt fontos, hogy a „Háztartási gépek” végre megteljen =====
def _assign_alza(cat_path: str, title: str, desc: str) -> str:
    cp = _norm(cat_path)
    t = _norm(title)
    d = _norm(desc)
    txt = _text_blob(cat_path, title, desc)

    # 1) Háztartási kisgép → globális „Háztartási gépek” kategória
    #    (mosógép, hűtő, konyhai kisgépek, termoszok, vákuumozók, fritőzök stb.)
    if "háztartási kisgép" in cp:
        return "haztartasi-gepek"

    # 2) Tipikus elektronika
    if any(
        key in cp
        for key in [
            "tv, fotó, audió, videó",
            "telefon, tablet",
            "pc és laptop",
            "pc es laptop",
            "játék, konzol",
            "jatek, konzol",
            "okosóra",
            "okosora",
        ]
    ):
        return "elektronika"

    # 3) Otthon / barkács / kert
    if "otthon, barkács, kert" in cp:
        # ha kifejezetten kert / kerti, akkor menjen „Kert”-be
        if any(w in cp for w in ["kert", "kerti", "kültéri", "kulteri"]):
            return "kert"
        return "otthon"

    # 4) Sport, szabadidő – itt szétválogatjuk:
    if "sport, szabadidő" in cp or "sport, szabadido" in cp:
        # Látás (távcső, szemüveg, maszk stb.)
        if any(
            w in txt
            for w in [
                "távcső",
                "tavcso",
                "binokulár",
                "binokular",
                "monokulár",
                "monokular",
                "szemüveg",
                "szemuveg",
                "snorkel maszk",
                "búvármaszk",
                "buvarmaszk",
            ]
        ):
            return "latas"

        # Állatok – állateledel, kutya/macska felszerelés stb.
        if any(
            w in txt
            for w in [
                "kutya",
                "macska",
                "kutyatáp",
                "kutyatap",
                "macskatáp",
                "macskatap",
                "kutyakiképző",
                "kutyakikepzo",
                "póráz",
                "poraz",
                "állat",
                "allat",
            ]
        ):
            return "allatok"

        # Szépség / egészség – masszírozó, kozmetikai eszközök stb.
        if any(
            w in txt
            for w in [
                "kozmetika",
                "kozmetikai",
                "masszázs",
                "masszazs",
                "masszírozó",
                "masszirozo",
                "beautyrelax",
                "wellness",
                "aromaterápia",
                "aromaterapia",
            ]
        ):
            return "szepseg"

        # Egyéb sportcucc → Sport
        return "sport"

    # 5) Egészség / szépség külön kategóriák
    if any(
        w in cp
        for w in [
            "egészség",
            "egeszseg",
            "szépség",
            "szepseg",
        ]
    ) or any(
        w in txt
        for w in [
            "kozmetika",
            "kozmetikai",
            "parfüm",
            "parfum",
            "masszázs",
            "masszazs",
            "masszírozó",
            "masszirozo",
        ]
    ):
        return "szepseg"

    # 6) Könyv
    if "könyv" in cp or "konyv" in cp or "kotta" in cp:
        return "konyv"

    # 7) Állatok – ha nem a sport-blokk alatt jött
    if any(
        w in txt
        for w in [
            "kutya",
            "macska",
            "kutyatáp",
            "kutyatap",
            "macskatáp",
            "macskatap",
            "állateledel",
            "allateledel",
        ]
    ):
        return "allatok"

    # 8) Kert
    if any(w in cp for w in ["kert", "kerti", "kültéri", "kulteri"]):
        return "kert"

    # 9) Utazás – bőrönd, hátizsák, táska, sátor, kemping stb.
    if any(
        w in txt
        for w in [
            "bőrönd",
            "borond",
            "hátizsák",
            "hatizsak",
            "utazótáska",
            "utazotaska",
            "sátor",
            "sator",
            "kemping",
            "trekking",
        ]
    ):
        return "utazas"

    # 10) Default: otthon
    return "otthon"


# ===== Publikus belépési pont =====
def assign_category(partner: str, cat_path: str, title: str, desc: str) -> str:
    """
    partner: 'tchibo', 'alza', stb.
    cat_path: partner feed kategória path (pl. g:product_type)
    title: termék neve
    desc: hosszabb leírás
    Visszatérés: findora_main kategória string (otthon / haztartasi-gepek / sport / stb.)
    """
    p = _norm(partner)

    if p == "tchibo":
        return _assign_tchibo(cat_path, title, desc)

    if p == "alza":
        return _assign_alza(cat_path, title, desc)

    # ismeretlen partner → minimál fallback
    blob = _text_blob(cat_path, title, desc)

    if any(w in blob for w in ["tv", "telefon", "laptop", "konzol", "monitor"]):
        return "elektronika"
    if any(w in blob for w in ["játék", "jatek", "lego", "puzzle"]):
        return "jatek"
    if any(w in blob for w in ["sport", "futó", "futo", "kerékpár", "kerekpar"]):
        return "sport"
    if any(w in blob for w in ["baba", "gyerek", "gyermek"]):
        return "otthon"

    return "otthon"
