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


def _norm(t):
    return (t or "").lower()


def _root_from_path(path):
    if not path:
        return ""
    return path.split("|")[0].split(">")[0].strip().lower()


def assign_category(*args):
    if len(args) == 4:
        partner, cat_path, title, desc = args
    elif len(args) == 3:
        partner = ""
        cat_path, title, desc = args
    else:
        partner = ""
        cat_path = title = desc = ""

    partner = _norm(partner)
    text = _norm(f"{cat_path} {title} {desc}")
    root = _root_from_path(cat_path)

    # ========== 1. KERT ==========
    if any(w in text for w in [
        "kert", "kerti", "locsoló", "locsolo", "slag",
        "fűnyíró", "funyiro", "metsző", "metszo",
        "kerti bútor", "kerti butor"
    ]):
        return KAT_KERT

    # ========== 2. UTAZÁS ==========
    if any(w in text for w in [
        "utazás", "utazas", "travel", "bőrönd", "borond",
        "koffer", "utazótáska", "utazotáska"
    ]):
        return KAT_UTAZAS

    # ========== 3. ELEKTRONIKA ==========
    if re.search(r"\b(tv|monitor|laptop|notebook|konzol|ps4|ps5|xbox|nintendo|"
                 r"okostelefon|telefon|tablet|fejhallgató|headset|hangfal|"
                 r"bluetooth|cd|dvd|bluray|játékszoftver|jatek szoftver)\b", text):
        return KAT_ELEK

    # ========== 4. HÁZTARTÁSI GÉPEK ==========
    if re.search(r"\b(mosógép|mosogep|hűtő|huto|porszívó|porszivo|robotporszívó|"
                 r"mosogatógép|sütő|suto|mikrohullámú|mikrohullamu|"
                 r"kávéfőző|kavefozo|vízforraló|vizforralo)\b", text):
        return KAT_GEPEK

    # ========== 5. OTTHON (NEM elektromos) ==========
    if any(w in text for w in [
        "tányér", "tanyer", "pohár", "pohar", "bögre", "bogre",
        "kanál", "villa", "kés", "kes", "evőeszköz", "evoeszkoz",
        "tál", "tal", "textil", "törölköző", "torolkozo",
        "ágynemű", "agynemu", "párna", "parna", "paplan",
        "dekor", "váza", "vaza", "gyertya", "illatosító", "illat",
        "fürdőszoba", "furdoszoba", "konyhai eszköz", "konyhai keszlet",
        "tároló", "tarolo", "doboz"
    ]):
        return KAT_OTTHON

    # ========== 6. JÁTÉKOK ==========
    if re.search(r"\b(lego|duplo|játék|jatekok|társasjáték|tarsasjatek|plüss|"
                 r"pluss|babakocsi|baba|puzzle|kirakó|kirako)\b", text):
        return KAT_JATEK

    # ========== 7. DIVAT ==========
    if re.search(r"\b(ruha|póló|polo|kabát|kabat|nadrág|nadrag|cipő|cipo|"
                 r"csizma|bugyi|tanga|melltartó|melltarto|pulóver|pulover)\b", text):
        return KAT_DIVAT

    # ========== 8. SZÉPSÉG ==========
    if re.search(r"\b(parfüm|parfum|smink|krém|krem|sampon|dezodor|"
                 r"kozmetikum|ápoló|apolo)\b", text):
        return KAT_SZEPSEG

    # ========== 9. SPORT ==========
    if re.search(r"\b(sport|fitness|futópad|futopad|kerékpár|kerekpar|roller|labda)\b", text):
        return KAT_SPORT

    # ========== 10. KÖNYV ==========
    if re.search(r"\b(könyv|konyv|regény|regeny|szakkönyv)\b", text):
        return KAT_KONYV

    # ========== 11. ÁLLAT ==========
    if re.search(r"\b(kutya|macska|állateledel|allateledel|kutyatáp|macskatáp)\b", text):
        return KAT_ALLAT

    # ========== 12. LÁTÁS ==========
    if re.search(r"\b(szemüveg|szemuveg|kontaktlencse|napszemüveg)\b", text):
        return KAT_LATAS

    return KAT_MULTI
