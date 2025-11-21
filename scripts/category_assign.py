# scripts/category_assign.py
import re

# ===== Findora kategória ID-k =====
KAT_ELEK = "kat-elektronika"
KAT_GEPEK = "kat-gepek"
KAT_OTTHON = "kat-otthon"
KAT_JATEK = "kat-jatekok"
KAT_DIVAT = "kat-divat"
KAT_SZEPSEG = "kat-szepseg"
KAT_SPORT = "kat-sport"
KAT_KONYV = "kat-konyv"
KAT_ALLAT = "kat-allatok"
KAT_LATAS = "kat-latas"
KAT_EGYEB = "kat-egyeb"


def _normalize(text: str) -> str:
    return (text or "").lower()


def _root_from_path(cat_path: str) -> str:
    """Alza/Tchibo product_type első szintje (| vagy > előtt)."""
    if not cat_path:
        return ""
    root = cat_path.split("|")[0].split(">")[0]
    return root.strip().lower()


def assign_category(*args) -> str:
    """
    Egységes belépési pont.

    Elfogadja:
      - assign_category(partner, cat_path, title, desc)
      - assign_category(cat_path, title, desc)   # régi hívások miatt
    """

    if len(args) == 4:
        partner, cat_path, title, desc = args
    elif len(args) == 3:
        partner = ""
        cat_path, title, desc = args
    else:
        partner = ""
        cat_path = title = desc = ""

    partner = _normalize(partner)
    cat_path = cat_path or ""
    title = title or ""
    desc = desc or ""

    text = _normalize(f"{cat_path} {title} {desc}")
    root = _root_from_path(cat_path)

    # ===================== ALZA SPECIFIKUS =====================
    if partner == "alza":
        # főkategória alapján – ez lefedi a feedek nagy részét
        if root in (
            "pc és laptop",
            "pc es laptop",
            "telefon, tablet, okosóra",
            "telefon, tablet, okosora",
            "tv, fotó, audió, videó",
            "tv, foto, audio, video",
            "gaming és szórakozás",
            "gaming es szorakozas",
        ):
            return KAT_ELEK

        if root in (
            "háztartási kisgép",
            "haztartasi kisgep",
            "háztartási nagygép",
            "haztartasi nagygép",
            "háztartási nagygép",
            "haztartasi nagygép",
            "konyha, háztartás",
            "konyha, haztartas",
            "okosotthon",
        ):
            return KAT_GEPEK

        if root in (
            "otthon, barkács, kert",
            "otthon, barkacs, kert",
            "irodai felszerelés",
            "irodai felszereles",
        ):
            return KAT_OTTHON

        if root in (
            "játék, baba-mama",
            "jatek, baba-mama",
            "hračky, pro děti a miminka",
            "hracky, pro deti a miminka",
        ):
            return KAT_JATEK

        if root in (
            "illatszer, ékszer",
            "illatszer, ekszer",
            "drogéria",
            "drogerie",
            "egészségmegőrzés",
            "lékárna a zdraví",
            "lekarna a zdravi",
        ):
            return KAT_SZEPSEG

        if root in ("sport, szabadidő", "sport, szabadido", "sport a outdoor"):
            return KAT_SPORT

        if root in ("élelmiszer", "elelmiszer"):
            return KAT_OTTHON

        if root in ("autó-motor", "auto-moto"):
            return KAT_EGYEB
        # ha a root nem dönt, esünk le az általános kulcsszavakra

    # ===================== TCHIBO SPECIFIKUS =====================
    if partner == "tchibo":
        p = text  # ebben benne van cat_path + title + desc

        # Divat
        if any(
            kw in p
            for kw in (
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
            )
        ):
            return KAT_DIVAT

        # Gyerek / játék
        if any(kw in p for kw in ("gyerek", "gyermek", "baba", "játék", "jatekok")):
            return KAT_JATEK

        # Otthon, konyha, dekor
        if any(
            kw in p
            for kw in (
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
            )
        ):
            return KAT_OTTHON

        # Sport
        if "sport" in p or "fitness" in p:
            return KAT_SPORT

        # Kávé
        if "kávé" in p or "kave" in p:
            return KAT_OTTHON

        # ha semmi nem talált, esünk a generikus szabályokra

    # ===================== GENERIKUS KULCSSZAVAK =====================

    # Elektronika
    if re.search(
        r"\b(tv|televízió|televizio|monitor|laptop|notebook|konzol|ps4|ps5|xbox|nintendo|"
        r"fejhallgató|fejhallgato|headset|mikrofon|okostelefon|okosóra|okosora)\b",
        text,
    ):
        return KAT_ELEK

    # Háztartási gépek
    if re.search(
        r"\b(porszívó|porszivo|mosógép|mosogep|hűtő|huto|mosogatógép|mosogatogep|"
        r"sütő|suto|főzőlap|fozolap|mikrohullámú|mikrohullamu|légtisztító|legtisztito)\b",
        text,
    ):
        return KAT_GEPEK

    # Játékok
    if re.search(
        r"\b(játék|jatekok|lego|társasjáték|tarsasjatek|baba|babakocsi|plüss|"
        r"pluss|kirakó|kirako|puzzle)\b",
        text,
    ):
        return KAT_JATEK

    # Divat
    if re.search(
        r"\b(ruha|póló|polo|nadrág|nadrag|kabát|kabat|cipő|cipo|csizma|bugyi|melltartó|"
        r"melltarto|szoknya|pulóver|pulover|sapka|kendő|kendo)\b",
        text,
    ):
        return KAT_DIVAT

    # Szépség / drogéria
    if re.search(
        r"\b(parfüm|parfum|smink|rúzs|ruzs|krém|krem|sampon|dezodor|kozmetikum|"
        r"ápoló|apolo|hajbalzsam|tusfürdő|tusfurdo)\b",
        text,
    ):
        return KAT_SZEPSEG

    # Sport
    if re.search(
        r"\b(futócipő|futocipo|edzőcipő|edzocipo|sportszár|edzőpad|edzopad|edzés|edzes|"
        r"kerékpár|kerekpar|foci|labda|roller|sátor|sator|horgász|horgasz|"
        r"fitnesz|fitness)\b",
        text,
    ):
        return KAT_SPORT

    # Könyv
    if re.search(r"\b(könyv|konyv|regény|regeny|szakkönyv|szakkonyv)\b", text):
        return KAT_KONYV

    # Állatok
    if re.search(
        r"\b(kutya|macska|háziállat|haziallat|állateledel|allateledel|"
        r"kutyatáp|kutyatap|macskatáp|macskatap)\b",
        text,
    ):
        return KAT_ALLAT

    # Látás
    if re.search(
        r"\b(szemüveg|szemuveg|kontaktlencse|napszemüveg|napszemuveg)\b", text
    ):
        return KAT_LATAS

    # Fallback
    return KAT_MULTI
