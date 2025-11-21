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
KAT_MULTI = "kat-multi"


def _normalize(text: str) -> str:
    return (text or "").lower()


def _root_from_path(cat_path: str) -> str:
    """
    Google / ProductsUp product_type / CATEGORYTEXT első szintje
    (első '|' vagy '>' előtti rész).
    Példa:
      "Apparel & Accessories > Clothing > Shirts & Tops"
      -> "Apparel & Accessories"
    """
    if not cat_path:
        return ""
    root = cat_path.split("|")[0].split(">")[0]
    return root.strip().lower()


# ===== TCHIBO SPECIFIKUS KATEGÓRIA-LOGIKA =====
def _assign_tchibo(cat_path: str, title: str, desc: str) -> str:
    """
    Tchibo feed:
      - CATEGORYTEXT / PARAM_CATEGORY Google taxonomy angolul
      - leírás + cím magyarul
    Innen döntjük el a Findora fő kategóriát (findora_main).
    """
    cat_path = cat_path or ""
    title = title or ""
    desc = desc or ""

    text = _normalize(cat_path + " " + title + " " + desc)
    root = _root_from_path(cat_path)

    # --- 1) Root alapú mapping (Google taxonomy első szint) ---

    # Ruházat, cipő, ékszer → DIVAT
    if "apparel & accessories" in root:
        return KAT_DIVAT

    # Lakás, konyha, háztartás, bútor → OTTHON
    if "home & garden" in root:
        return KAT_OTTHON

    # Sportfelszerelés → SPORT
    if "sporting goods" in root:
        return KAT_SPORT

    # Babaruha / babajáték
    if "baby & toddler" in root:
        # ha kifejezetten játék
        if "toy" in text or "játék" in text:
            return KAT_JATEK
        # egyébként jellemzően ruha → DIVAT
        return KAT_DIVAT

    # Kisállat cuccok
    if "animals & pet supplies" in root:
        return KAT_ALLAT

    # Elektronika (ha lenne Tchibo-nál)
    if "electronics" in root:
        return KAT_ELEK

    # Szépség / egészség
    if "health & beauty" in root:
        return KAT_SZEPSEG

    # Bőrönd, táska → DIVAT
    if "luggage & bags" in root:
        return KAT_DIVAT

    # Bútor → OTTHON
    if "furniture" in root:
        return KAT_OTTHON

    # Étel/ital/kávé → OTTHON (konyha/életmód)
    if "food, beverages & tobacco" in root or "food, beverages" in root:
        return KAT_OTTHON

    # Iroda / eszközök → jellemzően otthoni cuccok Tchibo-nál
    if "office supplies" in root or "hardware" in root or "tools" in text:
        return KAT_OTTHON

    # --- 2) Kulcsszó alapú mentő szabályok, ha a root nem döntött egyértelműen ---

    # Tipikus ruhaszavak → DIVAT
    if re.search(
        r"\b(kabát|kabátja|dzseki|dzsek[ií]|ruha|pelerin|pulóver|pulcs[iy]|"
        r"póló|polo|ing|szoknya|nadrág|leggings|legging|farmer|short|"
        r"melltartó|melltarto|bugyi|alsó|alsónemű|fehérnemű|fehernemu|"
        r"pizsama|hálóing|harisnya|zokni|csizma|cipő|cipo|bakancs)\b",
        text,
    ):
        return KAT_DIVAT

    # Tipikus konyha / otthon szavak → OTTHON
    if re.search(
        r"\b(bögre|bogre|pohár|pohar|tal|tál|tányér|tanyer|tálka|"
        r"tepsi|sütőforma|sutoforma|tortaforma|sütőtál|sutotal|"
        r"edény|edeny|serpenyő|serpenyo|lábas|labas|fazék|fazek|"
        r"törölköző|torolkozo|ágynemű|agynemu|párna|parna|pléd|plaid|"
        r"díszpárna|diszparna|fuggony|függöny|szőnyeg|szonyeg|"
        r"konyha|konyhai|asztalterítő|asztalterito)\b",
        text,
    ):
        return KAT_OTTHON

    # Játék szavak → JÁTÉKOK
    if re.search(
        r"\b(játék|jatekok|játékok|plüss|lego|társasjáték|tarsasjatek|"
        r"puzzle|kirakó|kirako|babajáték|babajatek)\b",
        text,
    ):
        return KAT_JATEK

    # Sport / fitness szavak → SPORT
    if re.search(
        r"\b(fitness|fitnesz|edzés|edzo|edzés|joga|jóga|"
        r"futás|futas|bicikli|kerékpár|kerekpar|sport)\b",
        text,
    ):
        return KAT_SPORT

    # Szépség / kozmetika → SZÉPSÉG
    if re.search(
        r"\b(krém|krem|testápoló|testapolo|sampon|balzsam|"
        r"smink|rúzs|ruzs|körömlakk|koromlakk|kozmetikum|kozmetika)\b",
        text,
    ):
        return KAT_SZEPSEG

    # Állatos kulcsszavak → ÁLLAT
    if re.search(
        r"\b(kutya|macska|cica|kisállat|kisallat|hám|póráz|poraz|"
        r"állateledel|allateledel|kutyajáték|macskajáték)\b",
        text,
    ):
        return KAT_ALLAT

    # Ha semmi nem talált → MULTI
    return KAT_MULTI


# ===== ÁLTALÁNOS assign_category BELÉPÉSI PONT =====
def assign_category(partner: str, cat_path: str, title: str, desc: str) -> str:
    """
    Egységes belépési pont a Python build scripteknek.
    Használat:
        findora_main = assign_category("tchibo", cat_path, title, desc)
    """
    p = _normalize(partner)

    # Tchibo speciális logika
    if p == "tchibo":
        return _assign_tchibo(cat_path, title, desc)

    # Ha később lesz más partner-specifikus logika (pl. alza),
    # ide jöhet:
    # if p == "alza":
    #     return _assign_alza(...)

    # Alap fallback – nagyon egyszerű általános szabályok
    text = _normalize((cat_path or "") + " " + (title or "") + " " + (desc or ""))

    if "book" in text or "könyv" in text or "konyv" in text:
        return KAT_KONYV

    if "toy" in text or "játék" in text or "jatekok" in text:
        return KAT_JATEK

    if "pet " in text or "kutya" in text or "macska" in text:
        return KAT_ALLAT

    if "sport" in text or "fitness" in text:
        return KAT_SPORT

    if "glass" in text or "tv" in text or "monitor" in text or "laptop" in text:
        return KAT_ELEK

    if "sofa" in text or "kanapé" in text or "fotel" in text or "törölköző" in text:
        return KAT_OTTHON

    # végső fallback
    return KAT_MULTI
