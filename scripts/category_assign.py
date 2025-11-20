# category_assign.py
#
# Központi kategória-hozzárendelés partnerenként.
# Visszaadott érték: findora_main:
#   elektronika, otthon, divat, jatekok, sport, kert,
#   haztartasi_gepek, allatok, konyv, utazas, latas, multi

from typing import Optional
import unicodedata


def _norm(s: str) -> str:
    """
    Egyszerű normalizálás: kisbetű, ékezet le, extra szóközök kiszedve.
    """
    if not s:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower()
    s = " ".join(s.split())
    return s


# =======================================================
#   TCHIBO → FINDORA MAIN CATEGORY  (VÁLTOZATLAN LOGIKA)
# =======================================================

def _tchibo_findora_main(cat_path: str) -> str:
    """
    Tchibo kategória → Findora főkategória.
    A cat_path tipikusan:
      - CATEGORYTEXT
      - PARAM_CATEGORY
    pl:
      "Apparel & Accessories > Clothing > Outerwear > Coats & Jackets"
      "Home & Garden > Kitchen & Dining > Kitchen Appliances"
    """

    s = _norm(cat_path)

    # ===== DIVAT =====
    if any(k in s for k in [
        "apparel & accessories",
        "clothing",
        "outerwear",
        "bras",
        "underwear & socks",
        "underwear",
        "shoes",
        "sleepwear & loungewear",
        "sleepwear",
        "skirts",
        "pants",
        "dresses",
        "baby & toddler clothing",
        "toddler underwear",
        "socks & tights",
    ]):
        return "divat"

    # ===== OTTHON =====
    if any(k in s for k in [
        "home & garden",
        "furniture",
        "kitchen & dining",
        "decor",
        "bedding",
        "linens & bedding",
        "lighting",
        "household cleaning supplies",
        "household supplies",
        "cabinets & storage",
        "shelving",
        "bookcases",
    ]):
        return "otthon"

    # ===== JÁTÉKOK =====
    if any(k in s for k in [
        "baby toys & activity equipment",
        "baby toys",
        "toys",
        "board games",
        "puzzles",
    ]):
        return "jatekok"

    # ===== SPORT =====
    if any(k in s for k in [
        "sporting goods",
        "cycling",
        "bicycle accessories",
        "cycling apparel & accessories",
        "camping & hiking",
        "exercise & fitness",
        "outdoor recreation",
    ]):
        return "sport"

    # ===== KERT =====
    if any(k in s for k in [
        "outdoor furniture",
        "outdoor furniture accessories",
        "outdoor furniture sets",
        "outdoor furniture covers",
        "birdhouses",
        "bird & wildlife houses",
    ]):
        return "kert"

    # ===== HÁZTARTÁSI GÉPEK =====
    if any(k in s for k in [
        "kitchen appliances",
        "small appliances",
        "kitchen tools & utensils",
        "can openers",
        "colanders & strainers",
        "tableware",
        "flatware",
    ]):
        return "haztartasi_gepek"

    # ===== ALAPÉRTELMEZETT =====
    return "multi"


# =======================================================
#   ALZA → FINDORA MAIN CATEGORY (FIXÁLT SZABÁLYOK)
# =======================================================

def _alza_findora_main(cat_path: str, title: str, desc: str) -> str:
    """
    Alza category_path + cím + leírás → Findora főkategória.

    Végleges Findora kategóriák:
      - elektronika
      - otthon
      - divat
      - jatekok
      - sport
      - kert
      - haztartasi_gepek
      - allatok
      - konyv
      - utazas
      - latas
      - multi (fallback)
    """

    cp_raw = cat_path or ""
    txt = " | ".join(x for x in [cp_raw, title or "", desc or ""] if x)
    s = _norm(txt)
    root = _norm(cp_raw.split("|")[0]) if cp_raw else ""

    # Kis segéd: könnyebb substring check
    def has(*words: str) -> bool:
        return any(w in s for w in words)

    def has_root(*words: str) -> bool:
        return any(w in root for w in words)

    # ==============================
    # 1) LÁTÁS (szemüveg, kontaktlencse, tisztító)
    # ==============================
    if has("szemuveg", "szemüveg", "kontaktlencse", "contact lens", "kontakt lencse", "optika"):
        return "latas"
    if "egeszsegmegorzes" in root and "szemuveg" in s:
        return "latas"

    # ==============================
    # 2) ÁLLATOK (kaja, játék, alom, póráz, ketrec, fekhely stb.)
    # ==============================
    if has("allateledel", "allat", "kuty", "dog ", "macsk", "cat ", "terrarium", "akvarium", "pet "):
        return "allatok"
    if has("kutyaeledel", "macskaeledel", "jutalomfalat", "póráz", "poraz", "nyakörv", "nyakorv", "alom"):
        return "allatok"

    # ==============================
    # 3) KÖNYV
    # ==============================
    if has_root("konyv") or has(" konyv", "konyvek", "konyv "):
        return "konyv"

    # ==============================
    # 4) UTAZÁS (bőrönd, utazási kiegészítők stb.)
    # ==============================
    if has("borond", "borondok", "borondcimke", "borondcimkek", "packing cubes", "utazasi kiegeszitok"):
        return "utazas"
    if has_root("hatizsak - taska") and has("borond", "borondok"):
        return "utazas"

    # ==============================
    # 5) HÁZTARTÁSI GÉPEK
    # ==============================
    # Root: "Háztartási kisgép" → tiszta háztartási gép
    if has_root("haztartasi kisgep"):
        return "haztartasi_gepek"

    # Kulcsszavak: mosógép, mosogatógép, hűtő, sütő stb.
    if has(
        "mosogep", "mosogepek", "mosogatogep", "mosogato gep",
        "hutogep", "hutoszekreny", "fagyaszto",
        "suto", "sutom", "fozolap", "porszivo", "mososzarito",
        "klima", "legkondi", "mikrohullamu", "mikrohullamu suto",
        "kavefozo", "kavegep"
    ):
        return "haztartasi_gepek"

    # ==============================
    # 6) ELEKTRONIKA
    # ==============================

    # Telefon / tablet / okosóra
    if has_root("telefon, tablet, okosora") or has(
        "okosora", "okoskarkoto", "smartwatch", "iphone", "android",
        "mobiltelefon", "okostelefon", "tablet", "ipad"
    ):
        return "elektronika"

    # PC, laptop, perifériák
    if has_root("pc es laptop") or has(
        "notebook", "laptop", "pc ", "szamitogep", "videokartya",
        "ram", "ssd", "hdd", "monitor"
    ):
        return "elektronika"

    # TV, audio, hifi
    if has_root("tv, foto, audio, video") or has(
        "televizio", "tv ", "soundbar", "hangfal", "hangszoro",
        "fejhallgato", "fulhallgato", "projektor"
    ):
        return "elektronika"

    # Gaming – alapból elektronika, de játék szoftver külön → jatekok
    if has_root("gaming es szorakozas"):
        # PC és konzoljátékok → JÁTÉKOK
        if "pc es konzoljatekok" in s or "jatek " in s or " jatekok" in s:
            return "jatekok"
        # Kontrollerek / gamepad → ELEKTRONIKA
        if has("kontroller", "gamepad", "joystick"):
            return "elektronika"
        # Egyéb gaming hardver, Xbox, PlayStation, Nintendo
        if has("xbox", "playstation", "nintendo", "switch", "konzol"):
            return "elektronika"
        # Egyéb filmes/gamer ajándék (bögre, termosz stb.) → otthon
        if has("termosz", "pohar", "bögre", "bogre"):
            return "otthon"
        # Alap: elektronika
        return "elektronika"

    # Okosotthon / okos kütyük
    if has_root("okosotthon") or has("smart home", "wifi-s", "okos dugasz", "okos izzo"):
        return "elektronika"

    # Autó-motor – csak elektronikus / hűtő / GPS
    if has_root("auto-motor"):
        if has("gps", "dashcam", "kamera", "autoshuto", "autos huto", "hutolada"):
            return "elektronika"

    # ==============================
    # 7) SPORT
    # ==============================
    if has_root("sport, szabadido"):
        # Utazós dolgok itt is lehetnek, de azt már feljebb kezeltük (bőrönd stb.)
        # Állatos dolgokat feljebb kezeltük.

        # Sporttápszerek, protein, kreatin stb. maradhatnak sport alatt
        return "sport"

    # ==============================
    # 8) KERT
    # ==============================
    if has_root("otthon, barkacs, kert") and "kert" in s:
        return "kert"
    if has("kerti butor", "kerti szek", "nyugagy", "utcaifeny", "kerti"):
        return "kert"

    # ==============================
    # 9) OTTHON
    # ==============================
    # Konyha, háztartás
    if has_root("konyha, haztartas"):
        return "otthon"

    # Otthon, barkács, kert – ha nem gép/kert,
    # hanem bútor, lakberendezés, lakástextil
    if has_root("otthon, barkacs, kert"):
        if has("butor", "kanape", "agykeret", "szekreny", "polc", "asztal"):
            return "otthon"
        if has("lakastextil", "agynemu", "fuggony", "torolkozo", "furdolepedo", "szonyeg"):
            return "otthon"
        if has("medence", "otthoni medence"):
            return "otthon"

    # Drogéria, illatszer – ha nem kifejezetten látás / állat, akkor otthon
    if has_root("drogéria") or has_root("drogeria") or has_root("illatszer, ekszer"):
        if not has("szemuveg", "kontaktlencse"):
            return "otthon"

    # Baba-mama etetés, pelenka – otthon (nem játék)
    if has_root("jatek, baba-mama") and has("pelenka", "szoptatas", "baba etetes", "cumisuveg"):
        return "otthon"

    # ==============================
    # 10) DIVAT
    # ==============================
    if has("ruhazat", "divat", "pulover", "kabát", "kabát ", "cipő", "cipo", "nadrag", "szoknya", "polo", "ing"):
        return "divat"

    # ==============================
    # 11) JÁTÉKOK
    # ==============================
    if has_root("jatek, baba-mama"):
        return "jatekok"
    if "kulteri jatekok" in s or has("tarsasjatek", "lego", "babahaz", "jatekszett"):
        return "jatekok"
    if "pc es konzoljatekok" in s:
        return "jatekok"
    if "nintendo switch 2|jatekok" in s or "nintendo switch|jatek" in s:
        return "jatekok"

    # ==============================
    # ALAPÉRTELMEZETT
    # ==============================
    return "multi"


# =======================================================
#   KÖZPONTI assign_category()
# =======================================================

def assign_category(
    partner_id: str,
    cat_path: Optional[str],
    title: str = "",
    desc: str = "",
) -> str:
    """
    Központi kategória-hozzárendelés.
    - partner_id: 'tchibo', 'alza', később 'pepita', stb.
    - cat_path: eredeti feed kategória (Tchibo: CATEGORYTEXT / PARAM_CATEGORY, Alza: category_path)
    - title / desc: finomhangoláshoz (főleg Alza)
    """
    pid = (partner_id or "").lower()

    # ===== TCHIBO =====
    if pid == "tchibo":
        return _tchibo_findora_main(cat_path or "")

    # ===== ALZA =====
    if pid == "alza":
        return _alza_findora_main(cat_path or "", title or "", desc or "")

    # ===== további partnerek később =====
    # if pid == "pepita":
    #     ...

    # ===== alapértelmezett =====
    return "multi"
