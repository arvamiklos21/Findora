# scripts/category_assign.py
#
# Findora – egyszerű, stabil ALZA kategorizáló
#
# Bemenet:  assign_category(fields: dict)
#   fields["category"] / ["categorytext"] / ["product_type"] / ["g:product_type"]
#   fields["title"] (opcionális)
#   fields["description"] vagy ["desc"] (opcionális)
#
# Kimenet:  25-ös Findora főkategória ID:
#   "elektronika", "haztartasi_gepek", "szamitastechnika",
#   "mobiltelefon", "gaming", "smart_home", "otthon",
#   "lakberendezes", "konyha_fozes", "kert", "jatekok",
#   "divat", "szepseg", "drogeria", "baba", "sport",
#   "egeszseg", "latas", "allatok", "konyv", "utazas",
#   "iroda_iskola", "szerszam_barkacs", "auto_motor_autoapolas",
#   vagy "kat-multi" (ha nem tudjuk biztosan).


import unicodedata


def _norm(s) -> str:
    """Ékezetmentes, kisbetűs, normalizált string."""
    if not s:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("\u00a0", " ")
    s = " ".join(s.split())
    return s.lower()


def _pick_category_path(fields: dict) -> str:
    """Visszaad egy category_path jellegű mezőt a dict-ből."""
    for key in (
        "category_path",
        "categorytext",
        "product_type",
        "g:product_type",
        "category",
    ):
        v = fields.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _base_from_root(root_norm: str) -> str | None:
    """Gyökérszint (product_type első tag) → alap Findora főkategória."""
    if not root_norm:
        return None

    # PC / laptop / IT
    if root_norm.startswith("pc es laptop") or root_norm.startswith("pocitace a notebooky"):
        return "szamitastechnika"

    # Telefon, tablet, okosóra
    if root_norm.startswith("telefon, tablet, okosora") or root_norm.startswith(
        "mobily, chytre hodinky, tablety"
    ):
        return "mobiltelefon"

    # TV / foto / audio / video
    if root_norm.startswith("tv, foto, audio") or root_norm.startswith(
        "tv, foto, audio-video"
    ):
        return "elektronika"

    # Gaming
    if root_norm.startswith("gaming es szorakozas") or root_norm.startswith(
        "gaming, hry a zabava"
    ):
        return "gaming"

    # Smart home
    if root_norm.startswith("okosotthon") or "smart home" in root_norm:
        return "smart_home"

    # Konyha & háztartás
    if root_norm.startswith("konyha, haztartas") or root_norm.startswith(
        "kuchynske a domaci potreby"
    ):
        return "konyha_fozes"

    # Háztartási gépek
    if root_norm.startswith("haztartasi kisgep") or root_norm.startswith(
        "haztartasi nagyg"
    ) or root_norm.startswith("domaci a osobni spotrebice"):
        return "haztartasi_gepek"

    # Sport
    if root_norm.startswith("sport, szabadido") or root_norm.startswith("sport a outdoor"):
        return "sport"

    # Játék / baba-mama – alap: játék
    if root_norm.startswith("jatek, baba-mama") or root_norm.startswith(
        "hracky, pro deti a miminka"
    ):
        return "jatekok"

    # Drogéria
    if root_norm.startswith("drogeria") or root_norm.startswith("drogerie"):
        return "drogeria"

    # Iroda & iskola
    if root_norm.startswith("irodai felszereles") or root_norm.startswith(
        "kancelar a papirnictvi"
    ):
        return "iroda_iskola"

    # Egészség
    if root_norm.startswith("egeszsegmegorzes") or root_norm.startswith("lekarn") or "lekarna a zdravi" in root_norm:
        return "egeszseg"

    # Szépség / illatszer
    if root_norm.startswith("illatszer, ekszer") or root_norm.startswith(
        "kosmetika, parfemy a krasa"
    ):
        return "szepseg"

    # Autó/motor
    if root_norm.startswith("auto-motor") or root_norm.startswith("auto-moto") or "auto-motor" in root_norm:
        return "auto_motor_autoapolas"

    # Állattartás
    if root_norm.startswith("allattartas"):
        return "allatok"

    # Otthon, barkács, kert – alap: otthon (majd finomítunk)
    if root_norm.startswith("otthon, barkacs, kert") or root_norm.startswith(
        "dum, dilna a zahrada"
    ):
        return "otthon"

    # Élelmiszer – nálunk egészség
    if root_norm.startswith("elelmiszer"):
        return "egeszseg"

    # Könyv
    if root_norm.startswith("konyv") or root_norm.startswith("konyv, ujsag") or "knihy" in root_norm:
        return "konyv"

    # Utazás
    if "utazas" in root_norm or "cestovani" in root_norm:
        return "utazás"

    return None


def _refine(base_cat: str | None, parts_norm: list[str], full_norm: str) -> str | None:
    """Finomhangolás ALZA-specifikus szabályokkal.
    Itt NEM megyünk át más teljesen idegen kategóriába, csak a rokonok között váltunk.
    """
    if not base_cat:
        return None

    root = parts_norm[0] if parts_norm else ""

    # Otthon, barkács, kert → szétbontás otthon / kert / szerszám / lakber
    if root.startswith("otthon, barkacs, kert") or root.startswith("dum, dilna a zahrada"):
        second = parts_norm[1] if len(parts_norm) > 1 else ""
        if "kert" in second or "zahrad" in second:
            return "kert"
        if "szerszam" in second or "naradi" in second:
            return "szerszam_barkacs"
        if "butor" in second or "lakberendezes" in second or "dekoracio" in second:
            return "lakberendezes"
        return "otthon"

    # Játék vs. Baba – csak ezen belül váltunk
    if base_cat == "jatekok":
        # path-szöveg és teljes szöveg
        tail = parts_norm[1:] if len(parts_norm) > 1 else []
        tail_text = " ".join(tail)

        baby_path_markers = [
            "jatekok babaknak",
            "jatek babaknak",
            "hracky pro nejmensi",
            "hracky pro miminka",
            "babaszoba",
            "babaszoba gyerekszoba",
        ]
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
            "csorgo",
            "ragoka",
            "babafeszek",
            "pihenoszek",
            "ringato",
            "babatornazas",
            "utazoagy",
            "utazo agy",
        ]

        if any(m in tail_text for m in baby_path_markers) or any(
            kw in full_norm for kw in baby_keywords
        ):
            return "baba"
        return "jatekok"

    # Egészség vs. Látás – csak ezen belül váltunk
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
            ]
        ):
            return "latas"
        return "egeszseg"

    # Szépség vs. Divat – ékszer/óra/táska → divat, egyéb marad szépség
    if base_cat == "szepseg":
        tail = parts_norm[1:] if len(parts_norm) > 1 else []
        tail_text = " ".join(tail)
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
                "penztarca",
                "ov",
                "ruhazat",
                "polo",
                "pulover",
                "sapka",
            ]
        ):
            return "divat"
        return "szepseg"

    # Gamer szék bárhonnan → gaming (ez közelebb áll a valós használathoz)
    if "gamer szek" in full_norm or "gamer chair" in full_norm:
        return "gaming"

    # Sport: nem váltunk át konyhára, elektronikára stb.
    if base_cat == "sport":
        return "sport"

    return base_cat


def assign_category(fields: dict) -> str:
    """
    Fő belépési pont ALZA-hoz.

    :param fields: dict, amit a build_alza.py ad át (title, description, category_path stb.)
    :return: Findora főkategória ID vagy "kat-multi"
    """
    cat_path = _pick_category_path(fields)
    title = fields.get("title") or ""
    desc = fields.get("description") or fields.get("desc") or ""

    if not cat_path:
        # ha nincs path, akkor inkább multi, mint rossz hely
        return "kat-multi"

    parts = [p for p in (cat_path.split("|") if isinstance(cat_path, str) else []) if p.strip()]
    parts_norm = [_norm(p) for p in parts]
    root_norm = parts_norm[0] if parts_norm else ""

    full_text = " ".join([cat_path, str(title), str(desc)])
    full_norm = _norm(full_text)

    # 1) gyökérszint → alap kategória
    base = _base_from_root(root_norm)

    # 2) finomhangolás ALZA-specifikus szabályokkal
    refined = _refine(base, parts_norm, full_norm)
    if refined:
        return refined

    # 3) ha nincs base (ismeretlen root), ne találgassunk – inkább multi
    if not base:
        return "kat-multi"

    return base
