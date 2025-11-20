# category_assign.py
# ==================
# Egyetlen belépési pont: assign_category(partner, cat_path, title, desc)
# Visszatérési érték: a Findora fő kategória kódja:
# elektronika, haztartasi-gepek, otthon, kert, jatekok, divat,
# szepseg, sport, latas, allatok, konyv, utazas, multi


def _norm(s):
    return (s or "").strip().lower()


def _has_any(text, words):
    t = _norm(text)
    return any(w in t for w in words)


def assign_category(partner, cat_path, title, desc):
    """
    partner : pl. 'alza', 'pepita', 'tchibo', ...
    cat_path: teljes partner kategóriaút pl.
              'Konyha, háztartás|Konyhai kisgépek|Elektromos grillek'
    title   : terméknév
    desc    : leírás
    """
    p = _norm(partner)
    cp = _norm(cat_path)
    ttl = _norm(title)
    dsc = _norm(desc)

    root = _norm(cat_path.split("|")[0] if cat_path else "")

    text_all = " | ".join(filter(None, [cp, ttl, dsc]))

    # ========= 1. ERŐS NYELVI / ROOT ALAPÚ SZABÁLYOK =========

    # --- ELEKTRONIKA ---
    if _has_any(
        root,
        [
            "tv, fotó, audió, videó",
            "tv, foto, audio-video",
            "telefon, tablet, okosóra",
            "pc és laptop",
            "pc es laptop",
            "počítače a notebooky",
            "okosotthon",
        ],
    ):
        return "elektronika"

    # --- HÁZTARTÁSI GÉPEK (KONYHAI GÉPEK) ---
    # Tipikus alza: "Konyha, háztartás|Konyhai kisgépek|..."
    # vagy: "Háztartási kisgép|Vízforralók és ital készítés|..."
    if root.startswith("konyha, háztartás") and _has_any(
        cp,
        ["konyhai kisgépek", "élelmiszer feldolgozás", "élelmiszer tárolás"],
    ):
        return "haztartasi-gepek"

    if root.startswith("háztartási kisgép") or _has_any(
        cp, ["konyhai kisgépek", "szódagépek", "vízforralók", "kávéfőzők", "grillek"]
    ):
        return "haztartasi-gepek"

    # --- OTTHON / BARKÁCS / KONYHA (NEM GÉP) ---
    if _has_any(
        root,
        [
            "otthon, barkács, kert",
            "konyha, háztartás",
            "konyha, haztartas",
            "konyha, háztartás|tálalás",
            "konyha, háztartás|takarítóeszközök",
        ],
    ):
        return "otthon"

    # --- KERT ---
    if _has_any(
        cp,
        [
            "kert|",
            "kerti bútorok",
            "kerti gépek",
            "grillek, füstölők",
            "otthoni medencék",
            "kerti medence",
        ],
    ):
        return "kert"

    # --- JÁTÉKOK ---
    if _has_any(
        root,
        [
            "játék, baba-mama",
            "gaming és szórakozás",
        ],
    ) or _has_any(cp, ["pc és konzoljátékok", "lego", "játékszett", "babajáték"]):
        return "jatekok"

    # --- DIVAT / RUHÁZAT ---
    if _has_any(
        cp,
        [
            "ruházat",
            "ruházat, divat",
            "ruhazat",
            "cipők",
            "cipok",
            "táskák",
            "taskak",
            "fehérnemű",
            "fehernemu",
        ],
    ):
        return "divat"

    # --- SZÉPSÉG / KOZMETIKA ---
    if _has_any(
        root,
        [
            "illatszer, ékszer",
        ],
    ) or _has_any(
        cp,
        [
            "kozmetikumok",
            "smink",
            "hajápolás",
            "borotválkozás",
            "parfüm",
        ],
    ):
        return "szepseg"

    # --- SPORT / SZABADIDŐ ---
    if root.startswith("sport, szabadidő") or root.startswith("sport a outdoor"):
        return "sport"

    # --- LÁTÁS (optika, szemüveg) ---
    if _has_any(
        cp,
        [
            "szemüveg",
            "lencse",
            "kontaktlencse",
            "dioptriás",
        ],
    ) or _has_any(ttl, ["szemüvegkeret", "szemuvegkeret"]):
        return "latas"

    # --- ÁLLATOK ---
    if _has_any(
        cp,
        [
            "állateledel",
            "allateledel",
            "állattartás",
            "allattartas",
            "kisállat",
            "kisallat",
            "terrárium",
            "terrarium",
            "kutyafelszerelés",
            "macskafelszerelés",
        ],
    ) or _has_any(ttl, ["kutya", "macska", "terrárium", "terrarium"]):
        return "allatok"

    # --- KÖNYV / MAGAZIN ---
    if _has_any(
        root,
        [
            "könyv",
            "konyv",
        ],
    ) or _has_any(cp, ["könyvek", "magazinok"]) or _has_any(
        ttl, ["könyv", "regény", "regeny", "szakkönyv"]
    ):
        return "konyv"

    # --- UTAZÁS ---
    # csak akkor, ha a kategória egyértelműen utazás/bőrönd/hotel tematikájú
    if _has_any(
        cp,
        [
            "utazás",
            "utazas",
            "bőrönd",
            "borond",
            "utazótáska",
            "utazotaska",
            "utazási kiegészítők",
            "utazasi kiegeszitok",
        ],
    ):
        return "utazas"

    # ========= 2. PARTNER-SPECIFIKUS FINOMHANGOLÁS =========

    # Alza extra: sok elektronika vegyes magyar/cseh elnevezéssel
    if p == "alza":
        if _has_any(
            cp,
            [
                "tv, fotó, audió, videó",
                "tv, foto, audio-video",
                "telefon, tablet, okosóra",
                "pc és laptop",
                "pc es laptop",
                "počítače a notebooky",
            ],
        ):
            return "elektronika"

        if _has_any(cp, ["konyhai kisgépek", "háztartási kisgép", "haztartasi kisgep"]):
            return "haztartasi-gepek"

        if _has_any(cp, ["játék, baba-mama", "gaming és szórakozás"]):
            return "jatekok"

    # Pepita extra – ne szórjunk mindent Utazásba,
    # csak ha tényleg utazás/bőrönd/stb. szerepel
    if p == "pepita":
        if _has_any(cp, ["bőrönd", "borond", "utazótáska", "utazotaska"]):
            return "utazas"
        # ha 'utazás' szerepel, de kozmetika/sport/jobban illeszkedik, akkor a fenti
        # általános szabályok már elvitték; ami megmarad, maradhat multi.

    # ========= 3. TITLE / LEÍRÁS SZERINTI GYENGE HEURISZTIKÁK =========

    # ha semmi nem fogta meg, de a szöveg nagyon elektronika jellegű
    if _has_any(text_all, ["laptop", "okostelefon", "konzol", "playstation", "xbox"]):
        return "elektronika"

    if _has_any(text_all, ["foci", "futball", "kosárlabda", "tenisz", "fitnesz", "fitness"]):
        return "sport"

    if _has_any(text_all, ["játék", "játékkonzol", "lego", "puzzle"]):
        return "jatekok"

    # ========= 4. ALAPÉRTELMEZETT =========

    return "multi"
