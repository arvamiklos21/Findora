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

    segments = [ _norm(p) for p in cp_raw.split("|") if p ]
    root = segments[0] if segments else ""

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
    # 3) UTAZÁS (bőrönd, utazási kiegészítők stb.)
    # ==============================
    if has("borond", "borondok", "borondcimke", "borondcimkek", "packing cubes", "utazasi kiegeszitok"):
        return "utazas"
    if has_root("hatizsak - taska") and has("borond", "borondok"):
        return "utazas"

    # ==============================
    # 4) HÁZTARTÁSI GÉPEK
    # ==============================
    if has_root("haztartasi kisgep"):
        return "haztartasi_gepek"

    if has(
        "mosogep", "mosogepek", "mosogatogep", "mosogato gep",
        "hutogep", "hutoszekreny", "fagyaszto",
        "suto", "sutom", "fozolap", "porszivo", "mososzarito",
        "klima", "legkondi", "mikrohullamu", "mikrohullamu suto",
        "kavefozo", "kavegep"
    ):
        return "haztartasi_gepek"

    # ==============================
    # 5) ELEKTRONIKA
    # ==============================
    if has_root("telefon, tablet, okosora") or has(
        "okosora", "okoskarkoto", "smartwatch", "iphone", "android",
        "mobiltelefon", "okostelefon", "tablet", "ipad"
    ):
        return "elektronika"

    if has_root("pc es laptop") or has(
        "notebook", "laptop", "pc ", "szamitogep", "videokartya",
        "ram", "ssd", "hdd", "monitor"
    ):
        return "elektronika"

    if has_root("tv, foto, audio, video") or has(
        "televizio", "tv ", "soundbar", "hangfal", "hangszoro",
        "fejhallgato", "fulhallgato", "projektor"
    ):
        return "elektronika"

    if has_root("gaming es szorakozas"):
        if "pc es konzoljatekok" in s or "jatek " in s or " jatekok" in s:
            return "jatekok"
        if has("kontroller", "gamepad", "joystick"):
            return "elektronika"
        if has("xbox", "playstation", "nintendo", "switch", "konzol"):
            return "elektronika"
        if has("termosz", "pohar", "bögre", "bogre"):
            return "otthon"
        return "elektronika"

    if has_root("okosotthon") or has("smart home", "wifi-s", "okos dugasz", "okos izzo"):
        return "elektronika"

    if has_root("auto-motor"):
        if has("gps", "dashcam", "kamera", "autoshuto", "autos huto", "hutolada"):
            return "elektronika"

    # ==============================
    # 6) SPORT
    # ==============================
    if has_root("sport, szabadido"):
        return "sport"

    # ==============================
    # 7) KERT
    # ==============================
    if has_root("otthon, barkacs, kert") and "kert" in s:
        return "kert"
    if has("kerti butor", "kerti szek", "nyugagy", "utcaifeny", "kerti"):
        return "kert"

    # ==============================
    # 8) OTTHON
    # ==============================
    if has_root("konyha, haztartas"):
        return "otthon"

    if has_root("otthon, barkacs, kert"):
        if has("butor", "kanape", "agykeret", "szekreny", "polc", "asztal"):
            return "otthon"
        if has("lakastextil", "agynemu", "fuggony", "torolkozo", "furdolepedo", "szonyeg"):
            return "otthon"
        if has("medence", "otthoni medence"):
            return "otthon"

    if has_root("drogéria") or has_root("drogeria") or has_root("illatszer, ekszer"):
        if not has("szemuveg", "kontaktlencse"):
            return "otthon"

    if has_root("jatek, baba-mama") and has("pelenka", "szoptatas", "baba etetes", "cumisuveg"):
        return "otthon"

    # ==============================
    # 9) DIVAT
    # ==============================
    if has("ruhazat", "divat", "pulover", "kabát", "kabát ", "cipő", "cipo", "nadrag", "szoknya", "polo", "ing"):
        return "divat"

    # ==============================
    # 10) JÁTÉKOK
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
    # 11) KÖNYV  – SZIGORÚBB SZABÁLY
    # ==============================
    is_book_category = any(
        "konyv" in seg or "ujsag" in seg or "ebook" in seg
        for seg in segments
    )

    is_book_like = any(
        w in s
        for w in [
            " konyv", "konyv ", "konyvek",
            "regeny", "mese", "mesekonyv", "novella",
            "kepregeny", "manga", "verseskotet",
            "szotar", "atlasz", "album", "tankonyv"
        ]
    )

    if is_book_category and is_book_like:
        return "konyv"

    # ==============================
    # 12) ALAPÉRTELMEZETT
    # ==============================
    return "multi"
