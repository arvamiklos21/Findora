import re

# ===== Segédfüggvények =====

def _norm(s):
    return (s or "").strip().lower()

def _contains_any(text, keywords):
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in keywords)

# ===== Alza-specifikus kategória hozzárendelés =====

def _assign_alza(category_path: str, text: str) -> str:
    """
    Alza category_path + szöveg alapján Findora fő kategória.
    Visszatérési érték: egyik az alábbiak közül:
      elektronika, haztartasi-gepek, otthon, kert, jatekok,
      divat, szepseg, sport, latas, allatok, konyv, utazas, multi
    """
    cat = _norm(category_path)
    txt = text.lower()

    if not cat or cat == "(nincs category_path)":
        # Fallback csak szöveg alapján
        if _contains_any(txt, ["xbox", "playstation", "ps4", "ps5", "nintendo",
                               "switch", "steam key", "pc játék", "pc game"]):
            return "jatekok"
        if _contains_any(txt, ["bicikli", "kerékpár", "kemping", "túra", "trekking",
                               "foci", "labda", "edző", "fitness", "sportmelltartó"]):
            return "sport"
        if _contains_any(txt, ["kutya", "macska", "pet ", "pet-", "állateledel"]):
            return "allatok"
        if _contains_any(txt, ["könyv", "regény", "képregény"]):
            return "konyv"
        return "multi"

    # --- 1. Gaming – játék vs elektronika szétválasztás ---
    if cat.startswith("gaming és szórakozás|pc és konzoljátékok"):
        return "jatekok"
    if cat.startswith("gaming és szórakozás|nintendo switch"):
        return "jatekok"
    if cat.startswith("gaming és szórakozás|tartozékok|kontrollerek"):
        # Kontroller, gamepad → nálad elektronika
        return "elektronika"
    if cat.startswith("gaming és szórakozás|filmes és gamer ajándékok"):
        return "jatekok"
    if cat.startswith("gaming és szórakozás"):
        # Általános gaming cucc
        return "jatekok"

    # --- 2. Sport, szabadidő csoport ---
    if cat.startswith("sport, szabadidő") or cat.startswith("sport a outdoor"):
        return "sport"

    # --- 3. Klasszikus elektronika csoportok ---
    if cat.startswith("tv, fotó, audió, videó") or cat.startswith("tv, foto, audio-video"):
        return "elektronika"

    if cat.startswith("pc és laptop") or cat.startswith("počítače a notebooky"):
        return "elektronika"

    if cat.startswith("telefon, tablet, okosóra"):
        return "elektronika"

    if cat.startswith("autó-motor|audió, videó") or \
       cat.startswith("autó-motor|autós hűtő") or \
       "gps navigációk" in cat:
        return "elektronika"

    if cat.startswith("okosotthon"):
        return "elektronika"

    # --- 4. Háztartási gépek / konyha ---
    if cat.startswith("háztartási kisgép") \
       or cat.startswith("konyha, háztartás") \
       or "konyhai kisgépek" in cat:
        # Ide menjenek a vízforralók, kávéfőzők, grillsütők, vákuumozók stb.
        return "haztartasi-gepek"

    # --- 5. Otthon, kert ---
    if cat.startswith("otthon, barkács, kert|kert"):
        return "kert"

    if cat.startswith("otthon, barkács, kert"):
        # bútor, lakástextil, szerszám, medence stb.
        return "otthon"

    # --- 6. Egészség / szépség / látás ---
    if cat.startswith("egészségmegőrzés|szemüvegek") \
       or "kontaktlencse" in cat \
       or "dioptriás" in txt:
        return "latas"

    if cat.startswith("egészségmegőrzés"):
        # vérnyomásmérő, masszírozó gép, tapaszok stb.
        return "szepseg"

    if cat.startswith("drogéria") or cat.startswith("illatszer, ékszer"):
        return "szepseg"

    # --- 7. Játék, baba-mama ---
    if cat.startswith("játék, baba-mama"):
        return "jatekok"

    # --- 8. Állatok / rovarriasztók stb. ---
    if "smartpet" in cat or "háziállat" in cat or "pet " in cat:
        return "allatok"

    if "kullancs" in cat or "szúnyogriasztó" in cat:
        # Ezt is vehetjük állatos/udvari használatnak
        return "allatok"

    # --- 9. Könyv ---
    if cat.startswith("könyv"):
        return "konyv"

    # --- 10. Élelmiszer ---
    if cat.startswith("élelmiszer"):
        # protein, magvak stb. – maradhat sport/otthon között; nálad legyen sporthoz köthető
        if _contains_any(cat, ["egészséges ételek", "sporttápszerek"]):
            return "sport"
        return "otthon"

    # --- 11. Iroda / iskolaszerek ---
    if cat.startswith("irodai felszerelés"):
        return "otthon"

    # --- 12. Egyéb: ha szöveg alapján egyértelműbb ---
    if _contains_any(txt, ["monitor", "videokártya", "ssd", "router", "wifi", "bluetooth"]):
        return "elektronika"

    if _contains_any(txt, ["porszívó", "mosógép", "hűtőszekrény", "mosogatógép"]):
        return "haztartasi-gepek"

    if _contains_any(txt, ["kandalló", "dekor", "függöny", "ágynemű", "törölköző"]):
        return "otthon"

    # --- Default ---
    return "multi"


# ===== Tchibo-specifikus egyszerűsített logika =====

def _assign_tchibo(text: str) -> str:
    t = text.lower()

    # Divat / ruha
    if _contains_any(t, [
        "kabát", "kabátka", "dzseki", "kabátka", "pulóver", "póló", "polo",
        "nadrág", "farmer", "szoknya", "ruha", "blúz", "ing", "tunika",
        "leggings", "harisnya", "melltartó", "bugyi", "tanga", "alsónemű",
        "cipő", "csizma", "bakancs", "papucs", "szandál", "zokni", "sapka",
        "kesztyű", "sál", "kendő"
    ]):
        return "divat"

    # Játék
    if _contains_any(t, [
        "játék", "játékszett", "lego", "puzzle", "társasjáték",
        "plüss", "autós játék", "építőkocka", "babaház"
    ]):
        return "jatekok"

    # Háztartási gép
    if _contains_any(t, [
        "vízforraló", "kávéfőző", "kávégép", "szeletelőgép", "mixer",
        "turmix", "konyhai robot", "gofrisütő", "melegszendvics", "sütő",
        "mikrohullámú", "mikró", "porszívó", "gőztisztító"
    ]):
        return "haztartasi-gepek"

    # Kert
    if _contains_any(t, [
        "kerti", "kültéri", "grill", "napernyő", "kerti szék", "kerti asztal",
        "virágláda", "locsoló", "slag"
    ]):
        return "kert"

    # Otthon (lakástextil, dekor, tárolás)
    if _contains_any(t, [
        "ágynemű", "párna", "paplan", "pléd", "takaró", "törölköző",
        "frottír", "függöny", "szőnyeg", "díszpárna", "dekor", "tárolódoboz",
        "kosár", "polc", "fogas"
    ]):
        return "otthon"

    return "multi"


# ===== Generikus / egyéb partnerek =====

def _assign_generic(text: str) -> str:
    t = text.lower()

    if _contains_any(t, ["xbox", "playstation", "ps4", "ps5", "nintendo", "switch",
                         "lego", "társasjáték", "puzzle", "játék"]):
        return "jatekok"

    if _contains_any(t, ["kabát", "pulóver", "póló", "nadrág", "ruha", "cipő", "csizma"]):
        return "divat"

    if _contains_any(t, ["futball", "kosárlabda", "röplabda", "edzés", "fitness",
                         "kerékpár", "bicikli", "kemping", "túra"]):
        return "sport"

    if _contains_any(t, ["vízforraló", "mosógép", "porszívó", "hűtő", "kávéfőző"]):
        return "haztartasi-gepek"

    if _contains_any(t, ["kutya", "macska", "állateledel", "póráz", "nyakörv"]):
        return "allatok"

    if _contains_any(t, ["szemüveg", "dioptriás", "kontaktlencse"]):
        return "latas"

    if _contains_any(t, ["krém", "szérum", "sampon", "testápoló", "kozmetikum"]):
        return "szepseg"

    if _contains_any(t, ["könyv", "regény", "képregény"]):
        return "konyv"

    return "multi"


# ===== Fő belépési pont =====

def assign_category(partner: str, category_path: str, title: str, desc: str) -> str:
    """
    partner: pl. 'tchibo', 'alza', 'jateksziget', 'regio' stb.
    category_path: az XML-ből jövő teljes kategória-útvonal (Alza esetén pl. "Sport, szabadidő|…")
    title + desc: terméknév és leírás
    """
    p = _norm(partner)
    cat = category_path or ""
    txt = f"{title or ''} {desc or ''}"

    # Alza – részletes, category_path-alapú logika
    if p == "alza":
        return _assign_alza(cat, txt)

    # Tchibo – saját logika
    if p == "tchibo":
        return _assign_tchibo(txt)

    # Játékos partnerek – minden mehet játék kategóriába
    if p in ("jateksziget", "jateknet", "regio", "regiojatek"):
        return "jatekok"

    # Egyéb partnerek – generikus szabályok
    return _assign_generic(txt)
