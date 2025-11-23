# category_assign_alza.py
#
# Findora – ALZA-specifikus kategorizáló
# Bemenet:  category_path (Alza product_type),
#           title (opcionális),
#           description (opcionális)
# Kimenet:  25-ös Findora főkategória ID
#
# Visszaadott értékek pl.:
#   "elektronika", "haztartasi_gepek", "szamitastechnika",
#   "mobiltelefon", "gaming", "smart_home", "otthon",
#   "lakberendezes", "konyha_fozes", "kert", "jatekok",
#   "divat", "szepseg", "drogeria", "baba", "sport",
#   "egeszseg", "latas", "allatok", "konyv", "utazas",
#   "iroda_iskola", "szerszam_barkacs", "auto_motor",
#   vagy "kat-multi" (ha nem egyértelmű).


import unicodedata


def _norm(s: str) -> str:
    """Normalizált, ékezetmentes, kisbetűs string."""
    if not s:
        return ""
    s = s.strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("\u00a0", " ")
    s = " ".join(s.split())
    return s.lower()


def _base_category_from_root(root: str):
    """
    Alap főkategória a ROOT (product_type első szint) alapján.
    root: már _norm()-ozott string.
    """

    # PC / laptop / IT
    if root.startswith("pc es laptop") or root.startswith("pocitace a notebooky"):
        return "szamitastechnika"

    # Telefon, tablet, okosóra
    if root.startswith("telefon, tablet, okosora") or root.startswith(
        "mobily, chytre hodinky, tablety"
    ):
        return "mobiltelefon"

    # TV / audio / video / foto
    if root.startswith("tv, foto, audio") or root.startswith("tv, foto, audio-video") or "audio, video" in root or "audio-video" in root:
        return "elektronika"

    # Gaming
    if root.startswith("gaming es szorakozas") or root.startswith(
        "gaming, hry a zabava"
    ):
        return "gaming"

    # Smart home
    if root.startswith("okosotthon") or "smart home" in root:
        return "smart_home"

    # Konyha & háztartás (edények, mérlegek, konyhai cuccok)
    if root.startswith("konyha, haztartas") or root.startswith(
        "kuchynske a domaci potreby"
    ):
        return "konyha_fozes"

    # Háztartási gépek (mosógép, porszívó stb.)
    if root.startswith("haztartasi kisgep") or root.startswith(
        "haztartasi nagyg"
    ) or root.startswith("domaci a osobni spotrebice"):
        return "haztartasi_gepek"

    # Sport
    if root.startswith("sport, szabadido") or root.startswith("sport a outdoor"):
        return "sport"

    # Játék / baba-mama
    if root.startswith("jatek, baba-mama") or root.startswith(
        "hracky, pro deti a miminka"
    ):
        return "jatekok"

    # Drogéria
    if root.startswith("drogeria") or root.startswith("drogerie"):
        return "drogeria"

    # Iroda & iskola
    if root.startswith("irodai felszereles") or root.startswith(
        "kancelar a papirnictvi"
    ):
        return "iroda_iskola"

    # Egészség
    if root.startswith("egeszsegmegorzes") or root.startswith("lekarn") or "lekarna a zdravi" in root:
        return "egeszseg"

    # Szépség / illatszer
    if root.startswith("illatszer, ekszer") or root.startswith(
        "kosmetika, parfemy a krasa"
    ):
        return "szepseg"

    # Autó/motor
    if root.startswith("auto-motor") or root.startswith("auto-moto") or "auto-motor" in root:
        return "auto_motor"

    # Állattartás
    if root.startswith("allattartas"):
        return "allatok"

    # Otthon, barkács, kert
    if root.startswith("otthon, barkacs, kert") or root.startswith(
        "dum, dilna a zahrada"
    ):
        return "otthon"

    # Élelmiszer – nálunk közelebb áll az „egészség”-hez
    if root.startswith("elelmiszer"):
        return "egeszseg"

    # Könyv
    if root.startswith("konyv") or root.startswith("konyv, ujsag") or "knihy" in root:
        return "konyv"

    # Utazás
    if "utazas" in root or "cestovani" in root:
        return "utazas"

    return None


def _refine_for_special_roots(base_cat, root, parts_norm, full_norm):
    """
    Finomhangolás root + path + teljes szöveg alapján.
    base_cat: az alap főkategória (_base_category_from_root eredménye)
    root: normált root
    parts_norm: a category_path részei normálva
    full_norm: category_path + title + desc egybemásolva, normálva
    """
if not base_cat:
    return None

    # ===== Konyha, háztartás → Konyha & főzés =====
    if root.startswith("konyha, haztartas") or root.startswith("kuchynske a domaci potreby"):
        return "konyha_fozes"
        
    # ===== Otthon, barkács, kert – szétbontás otthon / kert / szerszám / lakber =====
    if "otthon, barkacs, kert" in root or "dum, dilna a zahrada" in root:
        second = parts_norm[1] if len(parts_norm) > 1 else ""

        if "kert" in second or "zahrad" in second:
            return "kert"
        if "szerszam" in second or "naradi" in second:
            return "szerszam_barkacs"
        if "butor" in second or "lakberendezes" in second or "dekoracio" in second:
            return "lakberendezes"

        return "otthon"

    # ===== Sport root – kivétel: Egészséges ételek / italok → Egészség =====
    if base_cat == "sport":
        if any(
            kw in full_norm
            for kw in [
                "egeszseges etelek",
                "egeszseges italok",
                "diofelek",
                "aszalt gyumolcs",
                "magvak",
                "superfood",
                "protein",
                "elelmiszer",
                "taplalek",
            ]
        ):
            # Fitness food, egészséges nasik → Egészség
            return "egeszseg"

        return "sport"

    # ===== Játék vs. Baba – finomhangolás =====
    if base_cat == "jatekok":
        tail = parts_norm[1:] if len(parts_norm) > 1 else []
        tail_text = " ".join(tail)

        # Egyértelműen baba-jellegű alútvonalak
        baby_path_markers = [
            "jatekok babaknak",
            "jatek babaknak",
            "hracky pro nejmensi",  # cseh
            "hracky pro miminka",
            "babaszoba gyerekszoba",
            "babaszoba",
        ]

        # Baba-specifikus kulcsszavak a teljes szövegben (title+desc+path)
        baby_keywords = [
            "pelenka",
            "pelenk",
            "cumisuveg",
            "cumi",
            "eteto szek",
            "etetoszek",
            "babakocsi",
            "hordozo",
            "jatekbaba",
            "jaroka",
            "babaagy",
            "szundikendo",
            "szundikendok",
            "csorgo",
            "csorgok",
            "ragoka",
            "ragokak",
            "babafeszek",
            "babafeszkek",
            "pihenoszek",
            "ringato",
            "babatornazas",
            "babatornaztato",
            "utazoagy",
            "utazo agy",
            "utazo-agy",
        ]

        # Ha a path vagy a szöveg erősen baba-fókuszú → "baba"
        if any(m in tail_text for m in baby_path_markers) or any(
            kw in full_norm for kw in baby_keywords
        ):
            return "baba"

        # Minden más Játék, baba-mama → "jatekok"
        return "jatekok"

    # ===== Egészség vs. Látás =====
    if base_cat == "egeszseg":
        if any(
            kw in full_norm
            for kw in [
                "kontaktlencse",
                "kontaktlencsek",
                "szemuveg",
                "szemuvegek",
                "optika",
                "szemcsepp",
                "szemcseppek",
            ]
        ):
            return "latas"
        return "egeszseg"

    # ===== Szépség vs. Divat – csak a tail alapján döntünk =====
    if base_cat == "szepseg":
        tail = parts_norm[1:] if len(parts_norm) > 1 else []
        tail_text = " ".join(tail)

        # Ha a root alatti ág ékszer/óra/táska/ruha → divat
        if any(
            kw in tail_text
            for kw in [
                "ekszer",
                "ekszerek",
                "nyaklanc",
                "fulbevalo",
                "gyuru",
                "karora",
                "ora",
                "taska",
                "hatizsak",
                "hatizsakok",
                "penztarca",
                "ov",
                "ruhazat",
                "polo",
                "pulover",
                "sapka",
                "sapkas",
                "baseball sapkak",
            ]
        ):
            return "divat"

        # Minden más Illatszer, ékszer ág → szépség
        return "szepseg"

    # ===== Gamer szék override – akárhonnan jöhet =====
    if "gamer szek" in full_norm or "gamer chair" in full_norm:
        return "gaming"

    return base_cat


def _keyword_fallback(full_norm: str):
    """
    Ha a root alapján nem tudtunk dönteni, kulcsszavas fallback.
    Csak akkor fut, ha a base_cat None.
    """
    # Elektronika
    if any(
        kw in full_norm
        for kw in [
            "televizio",
            "televizor",
            " tv ",
            "hangfal",
            "hangszoro",
            "erosit",
            "bluetooth",
            "projektor",
            "kamer",
            "dron",
        ]
    ):
        return "elektronika"

    # Számítástechnika
    if any(
        kw in full_norm
        for kw in [
            "laptop",
            "notebook",
            "szamitogep",
            " pc ",
            "pc-",
            "monitor",
            "videokartya",
            "alaplap",
            "ssd",
            "hdd",
            "router",
        ]
    ):
        return "szamitastechnika"

    # Mobil
    if any(
        kw in full_norm
        for kw in [
            "okostelefon",
            "okos telefon",
            "mobiltelefon",
            "telefonhoz",
            "tok telefon",
            "tok iphone",
            "tok samsung",
        ]
    ):
        return "mobiltelefon"

    # Gaming
    if any(
        kw in full_norm
        for kw in ["ps4", "ps5", "xbox", "nintendo", "gaming", "gamer", "konzoljatek", "pc jatek"]
    ):
        return "gaming"

    # Konyha & főzés
    if any(
        kw in full_norm
        for kw in [
            "serpenyo",
            "fazek",
            "sutotal",
            "vagodeszka",
            "edeny",
            "konyhai",
            "konyha",
        ]
    ):
        return "konyha_fozes"

    # Kert
    if any(
        kw in full_norm
        for kw in [
            "kerti",
            "locsolo",
            "slag",
            "fukasza",
            "trambulin",
            "medence",
            "kerti grill",
            "ontozestechnika",
        ]
    ):
        return "kert"

    # Szerszám & barkács
    if any(
        kw in full_norm
        for kw in [
            "csavarhuzo",
            "furogep",
            "kalapacs",
            "bitkeszlet",
            "furesz",
            "sarokcsiszolo",
        ]
    ):
        return "szerszam_barkacs"

    # Divat
    if any(
        kw in full_norm
        for kw in [
            "nadrag",
            "polo",
            "pulover",
            "tunika",
            "szoknya",
            "ing",
            "kabat",
            "ruha",
            "melltarto",
            "bugyi",
            "zokni",
            "cipo",
            "csizma",
        ]
    ):
        return "divat"

    # Játékok
    if any(
        kw in full_norm
        for kw in [
            "lego",
            "tarsasjatek",
            "puzzle",
            "kirako",
            "jatekszett",
            "jatekfigura",
            "babahaz",
        ]
    ):
        return "jatekok"

    # Baba
    if any(
        kw in full_norm
        for kw in ["pelenka", "cumisuveg", "babaagy", "babakocsi", "jaroka", "babatakaro"]
    ):
        return "baba"

    # Drogéria
    if any(
        kw in full_norm
        for kw in [
            "mososzer",
            "mosogel",
            "mosopor",
            "oblito",
            "tisztitoszer",
            "fertotlenito",
            "wc papir",
            "zsebkendo",
        ]
    ):
        return "drogeria"

    # Szépség
    if any(
        kw in full_norm
        for kw in [
            "parfum",
            "dezodor",
            "deo ",
            "smink",
            "szempillaspiral",
            "alapozo",
            "puder",
        ]
    ):
        return "szepseg"

    # Egészség
    if any(
        kw in full_norm
        for kw in [
            "vernyomasmero",
            "oximeter",
            "lazmero",
            "gyogyszertar",
            "taplalekkiegeszito",
        ]
    ):
        return "egeszseg"

    # Állatok
    if any(
        kw in full_norm
        for kw in [
            "kutyatap",
            "macskatap",
            "ketrec",
            "kaparofa",
            "poraz",
            "nyakorv",
        ]
    ):
        return "allatok"

    # Könyv
    if any(
        kw in full_norm
        for kw in ["konyv", "regeny", "tankonyv", "kotta"]
    ):
        return "konyv"

    # Autó/motor
    if any(
        kw in full_norm
        for kw in [
            "motorolaj",
            "autoolaj",
            "felni",
            "gumiabroncs",
            "autokarpit",
            "autokozmetika",
            "parkoloradar",
            "dashcam",
        ]
    ):
        return "auto_motor"

    # Iroda & iskola
    if any(
        kw in full_norm
        for kw in [
            "tuzogep",
            "gemkapocs",
            "fuzet",
            "spiralfuzet",
            "toll",
            "ceruza",
            "irodaszer",
            "szamologep",
        ]
    ):
        return "iroda_iskola"

    return None


def assign_category(category_path: str, title: str | None = None, description: str | None = None) -> str:
    """
    Fő belépési pont.

    :param category_path: Alza product_type / kategóriaútvonal (pl. "Sport, szabadidő|Egészséges ételek|Diófélék")
    :param title: termék neve (opcionális)
    :param description: leírás (opcionális)
    :return: Findora főkategória ID (pl. "sport", "baba", "jatekok", vagy "kat-multi")
    """
    if not category_path:
        return "kat-multi"

    # Path szeletelése + normalizálás
    parts = [p.strip() for p in category_path.split("|") if p.strip()]
    root_raw = parts[0] if parts else ""
    root_norm = _norm(root_raw)
    parts_norm = [_norm(p) for p in parts]

    # Teljes szöveg (path + cím + leírás) – kulcsszavas fallbackhez, finomhangoláshoz
    full_text = " ".join(x for x in [category_path, title or "", description or ""] if x)
    full_norm = _norm(full_text)

    # 1) Root alapú főkategória
    base_cat = _base_category_from_root(root_norm)

    # 2) Speciális logika (otthon/barkács/kert, sport/egészséges ételek, játék vs. baba, szépség vs. divat, stb.)
    refined = _refine_for_special_roots(base_cat, root_norm, parts_norm, full_norm)
    if refined:
        return refined

    # 3) Ha nincs base_cat, próbáljunk kulcsszavakat
    if not base_cat:
        kw_cat = _keyword_fallback(full_norm)
        if kw_cat:
            return kw_cat
        return "kat-multi"

    # 4) Egyébként marad a root szerinti base_cat
    return base_cat
