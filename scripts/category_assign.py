# category_assign.py
import re

# Findora kategória ID-k (frontendtel egyezően)
CATEGORY_IDS = {
    "kat-elektronika",
    "kat-gepek",
    "kat-otthon",
    "kat-kert",
    "kat-jatekok",
    "kat-divat",
    "kat-szepseg",
    "kat-sport",
    "kat-latas",
    "kat-allatok",
    "kat-konyv",
    "kat-utazas",
    "kat-multi",
}


def _norm(text: str) -> str:
    """Kisbetű, ékezet nélkül, egy space-ek."""
    if not text:
        return ""
    t = text.lower()
    # egyszerű ékezeteltávolítás
    tr_map = str.maketrans(
        "áéíóöőúüűÁÉÍÓÖŐÚÜŰ",
        "aeiooouuuaeiooouuu",
    )
    t = t.translate(tr_map)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# -------- TCHIBO SZABÁLYOK --------
# title + category_path + description lesz összefűzve
TCHIBO_RULES = [
    # JÁTÉKOK
    (
        "kat-jatekok",
        [
            "jatek",
            "tarsasjatek",
            "tarsas-jatek",
            "lego",
            "pluss",
            "baby born",
            "barbiebaba",
            "jatekauto",
            "jarmu jatek",
            "kirako",
            "puzzle",
            "gyermek jatek",
            "gyerekjatek",
        ],
    ),
    # DIVAT (ruhák, cipők, kiegészítők)
    (
        "kat-divat",
        [
            "kabat",
            "dzseki",
            "parkas",
            "melleny",
            "pulover",
            "kardigan",
            "ruha",
            "szoknya",
            "bluz",
            "polo",
            "polos",
            "ing",
            "felsor",
            "felső",
            "nadrag",
            "farmer",
            "leggings",
            "cicanadrag",
            "pizsama",
            "haloruha",
            "fehernemu",
            "melltarto",
            "alsonadrag",
            "zokni",
            "harisnya",
            "csizma",
            "cipo",
            "szandál",
            "papucs",
            "cipő",
            "sapk",
            "sal",
            "kesztyu",
        ],
    ),
    # HÁZTARTÁSI GÉPEK
    (
        "kat-gepek",
        [
            "porszivo",
            "porszívó",
            "gőztisztito",
            "goztisztito",
            "kavefozo",
            "kávéfőző",
            "espresso",
            "kapszulas kave",
            "vizforralo",
            "vizforraló",
            "mixero",
            "turmix",
            "smoothie",
            "konyhai robot",
            "kenyersuto",
            "bagett",
            "suto",
            "sütőforma keszlet",
            "szenzoros koszuro",
            "melegito parna",
            "melegito takaro",
        ],
    ),
    # OTTHON (bútordekor, textil)
    (
        "kat-otthon",
        [
            "parna",
            "parnacsetlo",
            "parnatok",
            "parnacso",
            "takaró",
            "takaro",
            "plaid",
            "agyterito",
            "agytextil",
            "agy nemu",
            "agynemu",
            "fuggony",
            "fuggonyrud",
            "szonyeg",
            "futosszonyeg",
            "lepedo",
            "torolkozo",
            "torulkozo",
            "asztalterito",
            "asztalfuto",
            "asztali futó",
            "lamp",
            "lampa",
            "fenylanc",
            "fenyfüzér",
            "dekoracio",
            "karacsonyi dekor",
            "tarolodoboz",
            "kosar",
            "szek",
            "karpitos szek",
            "puff",
            "polc",
            "szekreny",
            "akaszto",
            "szennyestarto",
        ],
    ),
    # SZÉPSÉG / WELLNESS – majd később finomítható
    (
        "kat-szepseg",
        [
            "arapkolo",
            "arcapolo",
            "masszazs",
            "kozmetikai",
            "smink",
            "wellness",
            "szepito",
            "borapolo",
            "krem",
            "szappan",
        ],
    ),
    # SPORT
    (
        "kat-sport",
        [
            "futocipo",
            "futocipő",
            "sportmelltarto",
            "sportmelltartó",
            "joga",
            "fitnesz",
            "fitness",
            "edzokotel",
            "sulyzo",
            "kettlebell",
            "sportszivo",
            "sporttaska",
            "futokabat",
            "futofelső",
        ],
    ),
]


def _match_rules(text: str, rules) -> str | None:
    """Végigmegy a (cat_id, [kulcsszó...]) listán, első találatnál visszatér."""
    if not text:
        return None
    for cat_id, needles in rules:
        for n in needles:
            if n in text:
                return cat_id
    return None


def assign_category(
    partner_id: str,
    title: str = "",
    category_path: str = "",
    description: str = "",
) -> str:
    """
    Egységes belépő – minden partner erre hivatkozik.

    Visszaad egy Findora cat ID-t (pl. 'kat-otthon', 'kat-jatekok', stb.).
    Ha semmi nem stimmel, 'kat-multi'.
    """
    pid = (partner_id or "").lower().strip()
    text = _norm(" ".join([title or "", category_path or "", description or ""]))

    # ---- TCHIBO ----
    if pid == "tchibo":
        # 1) szabály-alapú besorolás
        cat = _match_rules(text, TCHIBO_RULES)
        if cat and cat in CATEGORY_IDS:
            return cat

        # 2) ha "gyerek/junior" + ruha → inkább divat, mint játék
        if ("gyerek" in text or "junior" in text) and (
            "ruha" in text or "nadrag" in text or "polo" in text or "pulover" in text
        ):
            return "kat-divat"

        # 3) alap fallback Tchibónál: otthon
        return "kat-otthon"

    # ---- MÁSIK PARTNER (később töltjük fel) ----
    # ide jön majd: alza, jateksziget, regio, stb.
    return "kat-multi"
