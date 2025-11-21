import re

# ===== Findora kategória ID-k =====
KAT_ELEK = "kat-elektronika"
KAT_GEPEK = "kat-gepek"
KAT_OTTHON = "kat-otthon"
KAT_KERT = "kat-kert"
KAT_JATEK = "kat-jatekok"
KAT_DIVAT = "kat-divat"
KAT_SZEPSEG = "kat-szepseg"
KAT_SPORT = "kat-sport"
KAT_KONYV = "kat-konyv"
KAT_ALLAT = "kat-allatok"
KAT_LATAS = "kat-latas"
KAT_UTAZAS = "kat-utazas"
KAT_MULTI = "kat-multi"


def _norm(text: str) -> str:
    return (text or "").lower()


def _root_from_path(cat_path: str) -> str:
    """Alza/Tchibo product_type első szintje (| vagy > előtt)."""
    if not cat_path:
        return ""
    # vegyük az első szegmenst | vagy > szerint
    root = cat_path.split("|")[0].split(">")[0]
    return root.strip().lower()


def _second_from_path(cat_path: str) -> str:
    """Második szint, ha van (Alza: 'root | second | ...')."""
    if not cat_path:
        return ""
    # először | szerint bontunk, ha az nincs, próbáljuk >
    parts = cat_path.split("|")
    if len(parts) < 2:
        parts = cat_path.split(">")
    if len(parts) < 2:
        return ""
    return parts[1].strip().lower()


def assign_category(*args) -> str:
    """
    Egységes belépési pont.

    Elfogadja:
      - assign_category(partner, cat_path, title, desc)
      - assign_category(cat_path, title, desc)   # régi hívások miatt
    """
    partner = ""
    cat_path = ""
    title = ""
    desc = ""

    if len(args) == 4:
        partner, cat_path, title, desc = args
    elif len(args) == 3:
        cat_path, title, desc = args
    else:
        # váratlan hívás – esünk a legbiztonságosabb default-ra
        return KAT_MULTI

    partner = _norm(partner)
    cat_path = cat_path or ""
    title = title or ""
    desc = desc or ""

    text = _norm(f"{cat_path} {title} {desc}")
    root = _root_from_path(cat_path)
    second = _second_from_path(cat_path)

    # ===================== GLOBÁLIS OVERRIDE: KERT =====================
    if any(w in text for w in [
        " kert", "kerti", "locsoló", "locsolo", "slag",
        "fűnyíró", "funyiro", "metsző", "metszo",
        "kerti bútor", "kerti butor"
    ]):
        return KAT_KERT

    # ===================== GLOBÁLIS OVERRIDE: UTAZÁS =====================
    if any(w in text for w in [
        "utazás", "utazas", "travel", "bőrönd", "borond",
        "koffer", "utazótáska", "utazotáska", "utazotaska",
        "repülőút", "repulot", "vakáció", "nyaralás", "nyaralas"
    ]):
        return KAT_UTAZAS

    # ===================== PARTNER-SPECIFIKUS: ALZA =====================
    if partner == "alza":
        r = root
        s = second

        # --- ELEKTRONIKA gyökerek ---
        if r in (
            "pc és laptop",
            "pc es laptop",
            "počítače a notebooky",
            "pocitace a notebooky",
            "telefon, tablet, okosóra",
            "telefon, tablet, okosora",
            "mobily, chytré hodinky, tablety",
            "tv, fotó, audió, videó",
            "tv, foto, audio-video",
            "gaming és szórakozás",
            "gaming es szorakozas",
            "gaming, hry a zábava",
            "okosotthon",
            "chytrá domácnost",
            "tv, foto, audio-video",
        ):
            return KAT_ELEK

        # --- HÁZTARTÁSI GÉPEK gyökerek ---
        if r in (
            "háztartási kisgép",
            "haztartasi kisgep",
            "háztartási nagygép",
            "haztartasi nagygép",
            "konyha, háztartás",
            "konyha, haztartas",
            "domácí a osobní spotřebiče",
            "domaci a osobni spotrebice",
            "velké spotřebiče",
            "velke spotrebice",
        ):
            # ha kifejezetten konyhai NEM gép (tartozék), akkor OTTHON
            if any(w in s for w in [
                "konyhai eszközök",
                "konyhai tartozékok",
                "stolování",
                "stolovani",
                "tálalás",
                "talalas",
            ]):
                return KAT_OTTHON
            return KAT_GEPEK

        # --- OTTHON / KERT / IRODA ---
        if r in ("otthon, barkács, kert", "otthon, barkacs, kert",
                 "dům, dílna a zahrada", "dum, dilna a zahrada"):
            # Alapértelmezésben OTTHON, de néhány second = KERT
            if any(w in s for w in [
                "kert",
                "kerti",
                "világítástechnika",
                "vilagitastechnika",
                "szerszámok",
                "szerszamok",
                "műhely",
                "muhely",
                "építőipar",
                "epitoipar",
                "évszakok szerint",
                "evszakok szerint",
                "grillek, füstölők",
                "grillek, fustolok",
                "otthoni medencék",
                "otthoni medencek",
                "szaunák",
                "szaunak",
                "ültetés",
                "ultetes",
                "zahrada",
                "dílna",
                "dilna",
            ]):
                return KAT_KERT
            return KAT_OTTHON

        if r in ("konyha, háztartás", "konyha, haztartas",
                 "kuchyňské a domácí potřeby", "kuchynske a domaci potreby"):
            return KAT_OTTHON

        if r in ("irodai felszerelés", "irodai felszereles",
                 "kancelář a papírnictví", "kancelar a papirnictvi"):
            # irodaszerek, iskolaszerek → KÖNYV
            if any(w in s for w in [
                "irodaszerek",
                "iskolaszerek",
                "papír",
                "papir",
                "papírnictví",
                "papirnictvi",
                "školní potřeby",
                "skolni potreby",
            ]):
                return KAT_KONYV
            # irodabútor, művészkellék stb. → OTTHON
            if any(w in s for w in [
                "irodabútorok",
                "irodabutorok",
                "kancelářský nábytek",
                "kancelarsky nabytek",
                "művészkellékek",
                "muveszkellekek",
            ]):
                return KAT_OTTHON
            return KAT_OTTHON

        # --- JÁTÉKOK ---
        if r in (
            "játék, baba-mama",
            "jatek, baba-mama",
            "hračky, pro děti a miminka",
            "hracky, pro deti a miminka",
        ):
            return KAT_JATEK

        # --- ILLATSZER / SZÉPSÉG / DIVAT ---
        if r in ("illatszer, ékszer", "illatszer, ekszer",
                 "kosmetika, parfémy a krása", "kosmetika, parfémy a krasa"):
            if any(w in s for w in [
                "ékszerek",
                "ekszerek",
                "karórák",
                "karorak",
                "hodinky",
                "šperky",
                "sperky",
            ]):
                return KAT_DIVAT
            return KAT_SZEPSEG

        # --- DROGÉRIA / HEALTH ---
        if r in ("drogéria", "drogerie"):
            if any(w in s for w in [
                "mosószerek",
                "mososzerek",
                "gépi mosogatószerek",
                "gepi mosogatoszerek",
                "prací prostředky",
                "praci prostredky",
                "přípravky do myčky",
                "pripravky do mycky",
            ]):
                return KAT_OTTHON
            return KAT_SZEPSEG

        if r in ("egészségmegőrzés", "egeszsegmegorzes",
                 "lékárna a zdraví", "lekarna a zdravi"):
            if any(w in s for w in [
                "szemüvegek",
                "szemuvegek",
                "brýle",
                "bryle",
                "kontaktlencsék",
                "kontaktlencsek",
            ]):
                return KAT_LATAS
            if any(w in s for w in [
                "étrendkiegészítők",
                "etrendkiegeszitok",
                "doplňky stravy",
                "doplnky stravy",
            ]):
                return KAT_SZEPSEG
            return KAT_SZEPSEG

        # --- SPORT / OUTDOOR / UTAZÁS ---
        if r in ("sport, szabadidő", "sport, szabadido", "sport a outdoor"):
            if any(w in s for w in [
                "hátizsák - táska",
                "hatizsak - taska",
                "batohy a zavazadla",
            ]):
                return KAT_UTAZAS
            return KAT_SPORT

        # --- ÉLELMISZER ---
        if r in ("élelmiszer", "elelmiszer"):
            return KAT_OTTHON

        # --- AUTÓ-MOTOR ---
        if r in ("autó-motor", "auto-moto"):
            if any(w in s for w in [
                "szerszámok",
                "szerszamok",
                "nářadí do auta",
                "naradi do auta",
                "autóizzók",
                "autoizzok",
            ]):
                return KAT_KERT
            if any(w in s for w in [
                "csomagtartók és boxok",
                "csomagtartok es boxok",
                "kamionos felszerelés",
                "kamionos felszereles",
                "autógumi tartozékok",
                "autogumi tartozekok",
                "autós hűtő",
                "autos huto",
                "akku és töltés",
                "akku es toltes",
                "elektromos járművek",
                "elektromos jarmuvek",
                "folyadékok",
                "folyadekok",
            ]):
                return KAT_UTAZAS
            return KAT_MULTI

        # ha az alza-specifikus nem döntött, lejjebb esünk a generikus szabályokra

    # ===================== PARTNER-SPECIFIKUS: TCHIBO =====================
    if partner == "tchibo":
        p = text  # ebben benne van cat_path + title + desc

        # Divat
        if any(kw in p for kw in (
            "női divat",
            "noi divat",
            "férfi divat",
            "ferfi divat",
            "fehérnemű",
            "fehernemu",
            "ruházat",
            "ruhazat",
            "póló",
            "polo",
            "pulóver",
            "pulover",
            "kabát",
            "kabat",
            "farmer",
        )):
            return KAT_DIVAT

        # Gyerek / játék
        if any(kw in p for kw in ("gyerek", "gyermek", "baba", "játék", "jatekok")):
            return KAT_JATEK

        # Otthon, konyha, dekor
        if any(kw in p for kw in (
            "otthon",
            "lakberendezés",
            "lakberendezes",
            "konyha",
            "háztartás",
            "haztartas",
            "ágynemű",
            "agynemu",
            "törölköző",
            "torolkozo",
            "fürdőszoba",
            "furdoszoba",
            "dekoráció",
            "dekoracio",
            "tárolás",
            "tarolas",
        )):
            return KAT_OTTHON

        # Sport
        if "sport" in p or "fitness" in p:
            return KAT_SPORT

        # Kávé
        if "kávé" in p or "kave" in p:
            return KAT_OTTHON

    # ===================== GENERIKUS KULCSSZAVAK =====================

    # Elektronika
    if re.search(
        r"\b(tv|monitor|laptop|notebook|konzol|ps4|ps5|xbox|nintendo|"
        r"okostelefon|telefon|tablet|fejhallgató|headset|hangfal|"
        r"bluetooth|cd|dvd|bluray|játékszoftver|jatek szoftver)\b",
        text,
    ):
        return KAT_ELEK

    # Háztartási gépek
    if re.search(
        r"\b(mosógép|mosogep|hűtő|huto|porszívó|porszivo|robotporszívó|"
        r"mosogatógép|sütő|suto|mikrohullámú|mikrohullamu|"
        r"kávéfőző|kavefozo|vízforraló|vizforralo)\b",
        text,
    ):
        return KAT_GEPEK

    # Otthon (nem elektromos)
    if any(w in text for w in [
        "tányér", "tanyer", "pohár", "pohar", "bögre", "bogre",
        "kanál", "kanal", "villa", "kés", "kes", "evőeszköz", "evoeszkoz",
        "tál", "tal", "textil", "törölköző", "torolkozo",
        "ágynemű", "agynemu", "párna", "parna", "paplan",
        "dekor", "váza", "vaza", "gyertya", "illatosító", "illat",
        "fürdőszoba", "furdoszoba", "konyhai eszköz", "konyhai keszlet",
        "tároló", "tarolo", "doboz",
    ]):
        return KAT_OTTHON

    # Játékok
    if re.search(
        r"\b(lego|duplo|játék|jatekok|társasjáték|tarsasjatek|plüss|"
        r"pluss|babakocsi|baba|puzzle|kirakó|kirako)\b",
        text,
    ):
        return KAT_JATEK

    # Divat
    if re.search(
        r"\b(ruha|póló|polo|kabát|kabat|nadrág|nadrag|cipő|cipo|"
        r"csizma|bugyi|tanga|melltartó|melltarto|pulóver|pulover)\b",
        text,
    ):
        return KAT_DIVAT

    # Szépség / drogéria
    if re.search(
        r"\b(parfüm|parfum|smink|krém|krem|sampon|dezodor|"
        r"kozmetikum|ápoló|apolo)\b",
        text,
    ):
        return KAT_SZEPSEG

    # Sport
    if re.search(
        r"\b(sport|fitness|futópad|futopad|kerékpár|kerekpar|roller|labda)\b",
        text,
    ):
        return KAT_SPORT

    # Könyv
    if re.search(
        r"\b(könyv|konyv|regény|regeny|szakkönyv|szakkonyv)\b",
        text,
    ):
        return KAT_KONYV

    # Állatok
    if re.search(
        r"\b(kutya|macska|állateledel|allateledel|kutyatáp|kutyatap|"
        r"macskatáp|macskatap)\b",
        text,
    ):
        return KAT_ALLAT

    # Látás
    if re.search(
        r"\b(szemüveg|szemuveg|kontaktlencse|napszemüveg|napszemuveg)\b",
        text,
    ):
        return KAT_LATAS

    # Fallback
    return KAT_MULTI
