# category_assign.py
#
# Kategória hozzárendelés partnerenként.
# Első körben: Alza – g:product_type fő szint (a '|' előtti rész) alapján.

from typing import Optional


# ===== Alza: főszintű product_type → Findora kategória ID =====

ALZA_MAIN_MAP = {
    # Elektronika
    "PC és laptop": "kat-elektronika",
    "Telefon, tablet, okosóra": "kat-elektronika",
    "TV, fotó, audió, videó": "kat-elektronika",
    "Gaming és szórakozás": "kat-elektronika",
    "Okosotthon": "kat-elektronika",

    # Cseh megfelelőik (ha keveredik a feedben)
    "Počítače a notebooky": "kat-elektronika",
    "Mobily, chytré hodinky, tablety": "kat-elektronika",
    "TV, foto, audio-video": "kat-elektronika",
    "Chytrá domácnost": "kat-elektronika",

    # Háztartási gépek (kis + nagy + konyhai)
    "Háztartási kisgép": "kat-gepek",
    "Háztartási nagygép": "kat-gepek",
    "Konyha, háztartás": "kat-gepek",

    # Cseh megfelelőik
    "Domácí a osobní spotřebiče": "kat-gepek",
    "Velké spotřebiče": "kat-gepek",
    "Kuchyňské a domácí potřeby": "kat-gepek",

    # Otthon, barkács, kert
    "Otthon, barkács, kert": "kat-otthon",
    "Dům, dílna a zahrada": "kat-otthon",

    # Játékok
    "Játék, baba-mama": "kat-jatekok",
    "Hračky, pro děti a miminka": "kat-jatekok",

    # Sport
    "Sport, szabadidő": "kat-sport",
    "Sport a outdoor": "kat-sport",
    "Sport a outdoor": "kat-sport",  # ha így is előfordul

    # Könyv / iroda
    "Irodai felszerelés": "kat-konyv",
    "Kancelář a papírnictví": "kat-konyv",

    # Szépség / drogéria / egészség
    "Illatszer, ékszer": "kat-szepseg",
    "Drogéria": "kat-szepseg",
    "Egészségmegőrzés": "kat-szepseg",

    "Kosmetika, parfémy a krása": "kat-szepseg",
    "Drogerie": "kat-szepseg",
    "Lékárna a zdraví": "kat-szepseg",

    # Autó
    "Autó-motor": "kat-auto",
    "Auto-moto": "kat-auto",

    # Élelmiszer – ha nincs külön élelmiszer füled, átmenetileg mehet otthonba
    "Élelmiszer": "kat-otthon",
}


def _normalize_product_type(value: Optional[str]) -> str:
    """Levágja a szóközöket, és csak az első szintet adja vissza (a '|' előtti részt)."""
    if not value:
        return ""
    txt = value.strip()
    # product_type: "Fő szint | Alszint | stb."
    main = txt.split("|", 1)[0].strip()
    return main


def assign_category_for_alza(product_type: Optional[str],
                             title: Optional[str] = "",
                             description: Optional[str] = "") -> str:
    """
    Alza termék kategorizálása.
    Elsődlegesen a g:product_type fő szint alapján dönt.
    Ha nincs direkt találat, pár biztonságos kulcsszót használunk.
    """
    main = _normalize_product_type(product_type)
    cat = ALZA_MAIN_MAP.get(main)
    if cat:
        return cat

    # Fallback: nagyon óvatos kulcsszavas logika teljes szövegre
    text = " ".join(filter(None, [product_type or "", title or "", description or ""])).lower()

    # Konzol / gaming mindig elektronika
    if any(w in text for w in ["konzol", "játékkonzol", "jatek konzol", "ps4", "ps5", "xbox", "nintendo", "switch"]):
        return "kat-elektronika"

    # Mosógép, mosogatógép, porszívó stb. – gépek
    if any(w in text for w in ["mosógép", "mosogep", "mosogatógép", "mosogatogep",
                               "porszívó", "porszivo", "robotporszívó", "robotporszivo",
                               "mikrohullámú", "mikrohullamu", "sütő", "suto",
                               "hűtőszekrény", "hutogep", "fagyasztó", "fagyaszto"]):
        return "kat-gepek"

    # Klasszikus gyerekjátékok
    if any(w in text for w in ["lego", "társasjáték", "tarsasjatek",
                               "plüss", "pluss", "babajáték", "babakocsi"]):
        return "kat-jatekok"

    # Sportos cucc
    if any(w in text for w in ["futócipő", "futocipo", "foci", "labda", "kerékpár", "kerekpar",
                               "roller", "edzőpad", "fitnesz", "kemping", "túra", "tura"]):
        return "kat-sport"

    # Ha semmi nem talált: dobjuk "egyéb"-be vagy egy általános otthon kategóriába
    return "kat-egyeb"


def assign_category(partner_id: str,
                    product_type: Optional[str],
                    title: Optional[str] = "",
                    description: Optional[str] = "") -> str:
    """
    Általános belépési pont – partner alapján delegál.
    Később ide jöhet Tchibo, Regio, Játéksziget stb.
    """
    pid = (partner_id or "").lower()

    if pid == "alza":
        return assign_category_for_alza(product_type, title, description)

    # TODO: más partnerek később
    return "kat-egyeb"
