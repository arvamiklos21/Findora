def assign_category(partner, category_path, title, desc):
    """
    partner: pl. 'alza', 'tchibo', 'pepita' ...
    category_path: az Alza/Pepita kategória-útvonal (pl. 'Háztartási kisgép|Konyhai kisgépek|...')
    title, desc: termék neve / leírás
    Visszatér: findora top kategória ID:
      'elektronika', 'haztartasi', 'otthon', 'kert', 'jatekok',
      'divat', 'szepseg', 'sport', 'latas', 'allatok', 'konyv',
      'utazas', 'multi'
    """
    p = (partner or "").lower().strip()
    cp = (category_path or "").lower()
    text = " ".join([category_path or "", title or "", desc or ""]).lower()

    # ===== 0. PARTNER-SPECIFIKUS – Tchibo minden OTTHON =====
    if p == "tchibo":
        return "otthon"

    # ===== 1. ELŐSZÖR: CATEGORY_PATH ALAPÚ SZABÁLYOK =====
    # --- Háztartási gépek (mosógép, hűtő, konyhai kisgépek stb.) ---
    if any(key in cp for key in [
        "háztartási kisgép",
        "háztartási gép",
        "konyhai kisgépek",
        "mosógép",
        "szárítógép",
        "mosogatógép",
        "porszívó",
        "hűtőszekrény",
        "fagyasztó",
        "sütő és tűzhely",
    ]):
        return "haztartasi"

    # --- Kert (kerti bútor, medence, grill, kert kategóriák) ---
    if any(key in cp for key in [
        "otthon, barkács, kert|kert",
        "kerti bútorok",
        "otthoni medencék",
        "grillek, füstölők",
    ]):
        return "kert"

    # --- Állatok ---
    if any(key in cp for key in [
        "állat",
        "állateledel",
        "állatfelszerelés",
        "smartpet",
        "terrárium",
        "akvárium",
    ]):
        return "allatok"

    # --- Könyv / magazin ---
    if any(key in cp for key in [
        "könyv", "könyvek", "magazin", "book"
    ]):
        return "konyv"

    # --- Utazás: bőröndök, utazási kiegészítők, travel cuccok ---
    if any(key in cp for key in [
        "hátizsák - táska|bőröndök",
        "utazási kiegészítők",
        "travel accessories",
    ]):
        return "utazas"

    # ===== 2. SZÖVEG ALAPÚ SZABÁLYOK (title + desc) =====

    # --- ELEKTRONIKA / GAMING CUCC – kontroller, konzol, headset stb. ---
    electronics_keywords = [
        "gamepad", "controller", "kontroller", "joystick",
        "xbox", "playstation", "ps4", "ps5",
        "nintendo", "switch",
        "konzol", "gaming", "gamer",
        "headset", "fülhallgató", "fejhallgató",
        "monitor", "laptop", "notebook", "tablet",
        "okostelefon", "okosóra",
        "tv ", " tv,", " televízió",
        "soundbar", "hangfal", "hangszóró",
        "projektor", "kamera", "webkamera",
        "bluetooth", "usb-c", "usb c", "usb kábel",
        "power bank", "router", "wifi", "wi-fi",
    ]
    if any(k in text for k in electronics_keywords):
        return "elektronika"

    # --- JÁTÉKOK – CSAK valódi játék: LEGO, társas, baba, RC, puzzle, játékfigura stb. ---
    toys_keywords = [
        "lego", "puzzle", "jenga", " társasjáték", " társas ",
        "társas játék", "társasjátékok",
        "baba", "babakocsi", "plüss", "figurája", "figura",
        "játékfigura", "matchbox", "kisautó",
        "építőjáték", "építőkocka",
        "rc autó", "távirányítós autó", "távirányítós helikopter", "drón",
        "strandjáték", "homokozó készlet",
        "játék, baba-mama",
    ]
    if any(k in text for k in toys_keywords):
        return "jatekok"

    # --- HÁZTARTÁSI GÉPEK – szöveg alapján (ha category_path nem fogta meg) ---
    haztartasi_text = [
        "mosógép", "mosogatógép", "szárítógép",
        "fagyasztó", "kombinált hűtő", "hűtőszekrény",
        "porszívó", "robotporszívó", "gőztisztító",
        "mikrohullámú sütő", "mikró",
        "konyhai robotgép", "konyhai robot",
        "botmixer", "turmixgép", "smoothie maker",
        "kávéfőző", "espresszó gép", "kapszulás kávéfőző",
        "légtisztító", "párátlanító", "légkondi", "klíma",
        "szárítógép",
    ]
    if any(k in text for k in haztartasi_text):
        return "haztartasi"

    # --- KERT – szöveg alapján (napernyő, nyugágy, medence, grill stb.) ---
    kert_text = [
        "kerti", "kerti szék", "kerti asztal",
        "napernyő", "nyugágy", "kerti bútor",
        "grill", "grillsütő", "bogrács", "faszenes grill",
        "medence", "porszívó medencéhez",
        "slag", "locsoló", "öntöző", "kerti tömlő",
        "kertészeti", "fűrész lombhoz", "metszőolló",
    ]
    if any(k in text for k in kert_text):
        return "kert"

    # --- SZÉPSÉG / KOZMETIKA ---
    beauty_keywords = [
        "kozmetikai táska", "kozmetikai neszesszer",
        "kozmetikum", "smink", "rúzs", "szempillaspirál",
        "hajszérum", "hajápoló", "bőrápoló", "testápoló",
        "parfüm", "eau de parfum", "eau de toilette",
        "manikűr készlet", "pedikűr készlet",
    ]
    if any(k in text for k in beauty_keywords):
        return "szepseg"

    # --- SPORT ---
    if "sport, szabadidő" in cp or any(k in text for k in [
        "fitness", "futball", "kosárlabda", "röplabda",
        "jóga", "edzőpad", "súlyzó", "kettlebell",
        "kerékpár", "bringás", "bicikli",
        "korcsolya", "rollerek", "trambulin",
        "síelés", "snowboard",
    ]):
        return "sport"

    # --- ÁLLATOK – ha textben derül ki (kutya, macska stb.) ---
    animals_text = [
        "kutya", "kutyának", "kutyafekhely", "kutyatáp",
        "macska", "cica", "macskaalom", "macskajáték",
        "terrárium", "akvárium", "hüllő", "rágcsáló",
        "háziállat", "pet ",
    ]
    if any(k in text for k in animals_text):
        return "allatok"

    # --- KÖNYV – ha textben derül ki ---
    books_text = [
        "könyv", "regény", "képregény", "szakkönyv",
        "mesekönyv", "fogalmazás füzet", "coloring book",
    ]
    if any(k in text for k in books_text):
        return "konyv"

    # --- UTAZÁS – ha textben derül ki (bőrönd, utazótáska stb.) ---
    travel_text = [
        "bőrönd", "bőrönd szett", "utazótáska", "utazó táska",
        "trolley", "travel bag", "poggyász", "carry-on",
        "nyakpárna utazáshoz",
    ]
    if any(k in text for k in travel_text):
        return "utazas"

    # --- DIVAT – ruhák, táskák, kiegészítők (ha nem sport vagy kozmetika) ---
    fashion_text = [
        "kabát", "dzseki", "pulóver", "nadrág", "szoknya",
        "póló", "ing", "blúz", "ruha", "tunika", "kardigán",
        "cipő", "csizma", "szandál", "papucs",
        "táska", "hátizsák", "övtáska", "pénztárca",
        "sapka", "sál", "kesztyű", "kalap",
    ]
    if any(k in text for k in fashion_text):
        return "divat"

    # --- LÁTÁS (optika) ---
    if any(k in text for k in [
        "szemüvegkeret", "kontaktlencse", "optika",
        "napszemüveg", "dioptriás", "keret",
    ]):
        return "latas"

    # --- OTTHON – ami még ide illik (törölköző, ágynemű, konyhai eszköz, dekor) ---
    home_text = [
        "törölköző", "fürdőlepedő", "ágynemű", "párna", "paplan",
        "lakástextil", "pléd", "ágytakaró", "függöny",
        "konyhai mérleg", "konyhai kés", "késkészlet",
        "vágódeszka", "edénykészlet", "serpenyő", "lábas",
        "tepsi", "sütőforma",
        "dekor", "díszpárna", "gyertya", "váza",
    ]
    if any(k in text for k in home_text):
        return "otthon"

    # ===== 3. ALAPÉRTELMEZETT =====
    return "multi"
