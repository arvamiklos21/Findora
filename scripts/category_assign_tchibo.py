# scripts/category_assign_tchibo.py
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


def _norm(t: str) -> str:
    return (t or "").strip().lower()


def _split_gpath(cat_path: str):
    """
    Google product_type / CATEGORYTEXT jellegű útvonal:
    'Apparel & Accessories > Clothing > Shirts & Tops'
    """
    if not cat_path:
        return []
    return [p.strip().lower() for p in str(cat_path).split(">") if p.strip()]


def _assign_generic(text: str) -> str:
    """Biztonsági nettó fallback Tchibohoz is – ha a főág nem dönt."""
    t = _norm(text)

    if not t:
        return KAT_MULTI

    # --- KERT / GARDEN ---
    if any(w in t for w in [
        " kert", "kerti", "lawn & garden", "gardening", "greenhouse",
        "plant ", "plants ", "pots & planters", "outdoor living"
    ]):
        return KAT_KERT

    # --- UTAZÁS / LUGGAGE ---
    if any(w in t for w in [
        "bőrönd", "borond", "utazótáska", "utazotáska",
        "luggage", "suitcase", "backpack", "travel bag", "garment bag",
        "fanny pack"
    ]):
        return KAT_UTAZAS

    # --- ELEKTRONIKA ---
    if re.search(
        r"\b(tv|televízió|televizio|monitor|laptop|notebook|konzol|ps4|ps5|xbox|nintendo|"
        r"okostelefon|telefon|tablet|headphones?|headset|speaker|hangfal|"
        r"radio|rádió|camera|fényképező|foto)\b",
        t,
    ):
        return KAT_ELEK

    if "electronics >" in t or "computers >" in t:
        return KAT_ELEK

    # --- HÁZTARTÁSI GÉPEK ---
    if re.search(
        r"\b(mosógép|mosogep|szárítógép|szaritogep|hűtő|huto|hűtőszekrény|mosogatógép|"
        r"mosogatogep|porszívó|porszivo|robotporszívó|vasaló|vasalo|"
        r"mikrohullámú|mikrohullamu|sütő|suto|főzőlap|fozolap)\b",
        t,
    ):
        return KAT_GEPEK

    if "kitchen appliances" in t or "laundry appliances" in t or "vacuums" in t:
        return KAT_GEPEK

    # --- JÁTÉKOK / BABY TOYS ---
    if re.search(
        r"\b(játék|jatekok|lego|társasjáték|tarsasjatek|plüss|pluss|babakocsi|baba|"
        r"puzzle|kirakó|kirako)\b",
        t,
    ):
        return KAT_JATEK

    if "baby toys" in t or ("toy" in t and "baby & toddler" in t):
        return KAT_JATEK

    # --- DIVAT ---
    if re.search(
        r"\b(ruha|póló|polo|ing|shirt|top|nadrág|nadrag|pants|jeans|farmer|"
        r"szoknya|skirt|kabát|kabat|coat|jacket|dzseki|"
        r"alsónemű|alsonemu|underwear|bra|melltartó|melltarto|"
        r"bugyi|tanga|socks|zokni|cipő|cipo|shoes|boots|csizma|"
        r"pizsama|pajamas|sleepwear|loungewear|pulóver|pulover|sweater)\b",
        t,
    ):
        return KAT_DIVAT

    if "apparel & accessories" in t:
        return KAT_DIVAT

    # --- SZÉPSÉG / DROGÉRIA ---
    if re.search(
        r"\b(parfüm|parfum|smink|makeup|make-up|rúzs|ruzs|lipstick|"
        r"krém|krem|cream|lotion|sampon|shampoo|dezodor|deodorant|"
        r"kozmetikum|cosmetics?|ápoló|apolo|skin care)\b",
        t,
    ):
        return KAT_SZEPSEG

    if "health & beauty" in t or "personal care" in t:
        return KAT_SZEPSEG

    # --- SPORT ---
    if re.search(
        r"\b(sport|fitness|fitnesz|edzés|edzes|futás|futas|"
        r"kerékpár|kerekpar|cycling|bicycle|roller|korcsolya|"
        r"ski|snowboard|hiking|camping)\b",
        t,
    ):
        return KAT_SPORT

    if "sporting goods" in t:
        return KAT_SPORT

    # --- KÖNYV / ÍRÓSZER / IRODASZER ---
    if re.search(
        r"\b(könyv|konyv|regény|regeny|szakkönyv|szakkonyv)\b",
        t,
    ):
        return KAT_KONYV

    if "office supplies" in t or "paper products" in t:
        return KAT_KONYV

    # --- ÁLLATOK ---
    if re.search(
        r"\b(kutya|macska|háziállat|haziallat|állateledel|allateledel|"
        r"kutyatáp|kutyatap|macskatáp|macskatap)\b",
        t,
    ):
        return KAT_ALLAT

    if "animals & pet supplies" in t or "pet supplies" in t:
        return KAT_ALLAT

    # --- LÁTÁS / OPTIKA ---
    if re.search(
        r"\b(szemüveg|szemuveg|napszemüveg|kontaktlencse|kontaktlencsék)\b",
        t,
    ):
        return KAT_LATAS

    if "contact lenses" in t or "eyeglasses" in t:
        return KAT_LATAS

    # --- OTTHON / BÚTOR / DEKOR / KONYHA ---
    if any(w in t for w in [
        "home & garden", "furniture", "bedding", "bed sheets", "blankets", "pillows",
        "towels", "bathroom accessories", "kitchen & dining", "cookware", "bakeware",
        "tableware", "serveware", "decor", "vases", "lighting", "lamp", "light bulb",
        "mirror", "curtains", "drapes", "rug", "mat", "storage & organization"
    ]):
        return KAT_OTTHON

    # Ha idáig sem találtunk semmit → vegyes
    return KAT_MULTI


def assign_category(cat_path: str, title: str, desc: str) -> str:
    """
    Tchibo-specifikus kategória hozzárendelés.
    Hívás: assign_category(cat_path, title, desc)
    """
    cat_path = cat_path or ""
    title = title or ""
    desc = desc or ""

    parts = _split_gpath(cat_path)
    main = parts[0] if parts else ""
    second = parts[1] if len(parts) > 1 else ""

    # 1) Főkategória alapú mapping (Google Product Taxonomy)
    if main.startswith("apparel & accessories"):
        # ruházat, cipő, ékszer, táskák → divat
        return KAT_DIVAT

    if main == "home & garden":
        # kert / növények → kat-kert, minden más → otthon
        if second.startswith("lawn & garden") or second.startswith("plants"):
            return KAT_KERT
        return KAT_OTTHON

    if main == "sporting goods":
        return KAT_SPORT

    if main == "animals & pet supplies":
        return KAT_ALLAT

    if main == "baby & toddler":
        # babaruhák, babajátékok → játék fülre tesszük
        return KAT_JATEK

    if main == "furniture":
        return KAT_OTTHON

    if main == "health & beauty":
        return KAT_SZEPSEG

    if main in ("food, beverages & tobacco", "food, beverages & tabacco"):
        # kávé, italok → otthon/konyha
        return KAT_OTTHON

    if main in ("electronics", "computers"):
        return KAT_ELEK

    if main == "office supplies":
        # irodaszer, papír, stb. → könyv/írószer blokk
        return KAT_KONYV

    if main == "arts & entertainment":
        # kreatív hobby, crafts → könyv/írószer blokk
        return KAT_KONYV

    if main in ("luggage & bags", "vehicles & parts"):
        # bőrönd, hátizsák, utazós kiegészítők → utazás
        return KAT_UTAZAS

    # 2) Ha a főág nem döntött → kulcsszavas fallback
    text = _norm(f"{cat_path} {title} {desc}")
    return _assign_generic(text)
