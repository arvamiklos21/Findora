"""
Category assignment logic for the OnlineMárkabolt feed.

This module defines a single function, ``assign_category``, which is
responsible for mapping a product's free‑form textual data to one of the
predefined high‑level categories used throughout the project.  The partner's
original feed contains a variety of product type and category fields (for
example ``PRODUCTNAME``, ``CATEGORYTEXT`` or ``g:product_type``).  The
``assign_category`` function ingests a dictionary of these fields, normalises
the text and applies a series of heuristics based on Hungarian keywords to
determine the most appropriate category.  If no suitable category can be
identified, the catch‑all category ``"Multi"`` is returned.

The target categories are:

    * Elektronika
    * Háztartási gépek
    * Számítástechnika
    * Mobil & kiegészítők
    * Gaming
    * Smart Home
    * Otthon
    * Lakberendezés
    * Konyha & főzés
    * Kert
    * Játékok
    * Divat
    * Szépség
    * Drogéria
    * Baba
    * Sport
    * Egészség
    * Látás
    * Állatok
    * Könyv
    * Utazás
    * Iroda & iskola
    * Szerszám & barkács
    * Autó/Motor & autóápolás
    * Multi (catch‑all)

The heuristics are largely keyword based: each category has an associated
list of indicative substrings.  After normalising all available text (to
lowercase and with diacritics removed), the function searches for these
keywords in descending order of specificity.  Should multiple categories
match, the first (most specific) match wins.  Only when none of the
keywords are present does the function fall back to the partner's own
category values via a translation table or finally to ``"Multi"``.

The goal of these heuristics is to achieve high coverage (≥95%) on the
OnlineMárkabolt product set.  They are intentionally generous in their
keyword lists to capture a broad range of related products, and can be
extended in the future as new product types appear.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, Optional


def _strip_accents(text: str) -> str:
    """Return the given text with diacritics removed.

    The incoming feed contains Hungarian product names and category
    descriptions which may include accented characters.  To simplify
    keyword matching we remove these accents using Unicode normalisation.
    ``unicodedata.normalize('NFKD', text)`` decomposes characters into
    their base letter and combining marks; the latter are then dropped.
    ``unicodedata.combining`` identifies combining marks.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _prepare_text(fields: Dict[str, Optional[str]]) -> str:
    """Concatenate and normalise all textual values from the feed fields.

    The `fields` argument is a dictionary passed from the parser in
    ``scripts/build-onlinemarkabolt.py``.  Values may be ``None`` or
    arbitrary strings.  This helper lowercases each non‑empty string,
    strips accents and returns a single search text.
    """
    parts: Iterable[str] = (str(v) for v in fields.values() if v)
    combined = " \n ".join(parts)
    # lower case first to maintain case‑insensitive matching
    combined = combined.lower()
    combined = _strip_accents(combined)
    return combined


# Define keyword lists for each target category.  The order of these
# definitions matters: categories appearing earlier in the list have higher
# priority when multiple keywords match.  Keywords themselves are stored
# without accents to align with the normalised text.
CATEGORY_KEYWORDS: Dict[str, Iterable[str]] = {
    # Kitchen & cooking: extractor hoods, hobs, sinks, mixers, food prep
    "Konyha & főzés": [
        "paraelszivo", "szagelszivo", "elszivo", "elszivorendszer",
        "sut", "suto", "mikro", "mikrohullam", "fozolap", "fuzolap",
        "tuzhely", "tuzhely", "fozolemez", "mosogato", "mosogatotal",
        "mosogatotalca", "csaptelep", "husdaralo", "kavefozo", "kavesgep",
        "kenyerpirito", "robotgep", "szeletelo", "vizforralo",
        "grill", "fritoz", "parako", "suto", "konyha", "edeny",
        "serpenyo", "talca", "cseppento", "vagodeszka",
    ],
    # Household appliances: washing, cooling, cleaning, climate
    "Háztartási gépek": [
        "mosogep", "mosoge", "szaritogep", "szaritomasina", "mosogatogep",
        "porszivo", "porszivorobot", "robotporszivo", "hutogep",
        "hutolada", "hutokehely", "hutokamra", "hut", "fagyaszto",
        "borhuto", "hutoszekreny", "klima", "legkondicionalo", "radiator",
        "futotest", "vasalo", "gozallomas", "legmoso", "legparasitott",
        "porszivo", "szaritogep", "mososzaritogep", "borhuto",
        "huto", "hutoszekreny", "takaritogep", "paratlantasito", "paratartalom", "lefelszivo",
    ],
    # Electronics: audio/visual equipment, consumer electronics
    "Elektronika": [
        "tv", "televizio", "smarttv", "led tv", "monitor",
        "hangfal", "hangrendszer", "erosito", "hifi", "soundbar",
        "kamera", "mikrofon", "dvd", "blu-ray", "projektor",
        "lemezjatszo", "fejhallgato", "fejhallgato", "hangszoro",
        "mp3", "mp4", "fotokamera", "fenykepezo",
    ],
    # Computing: computers, laptops, components
    "Számítástechnika": [
        "laptop", "notebook", "tablet", "szamitogep", "pc",
        "monitor", "billentyuzet", "eger", "nyomtato", "router",
        "modem", "ssd", "hdd", "ram", "videokartya", "gpu",
        "cpu", "processzor", "proci", "alaplap", "motherboard",
        "szamitastechnika", "szkenner", "scanner", "plotter",
    ],
    # Mobile & accessories
    "Mobil & kiegészítők": [
        "mobiltelefon", "okostelefon", "smartphone", "telefon", "mobil",
        "okosora", "okos ora", "smartwatch", "karora", "toke", "tok",
        "tolto", "toltokabel", "powerbank", "fulhallgato", "fejhallgato",
        "earbuds", "tartozek", "tok", "kabel", "adapter",
    ],
    # Gaming
    "Gaming": [
        "playstation", "ps5", "ps4", "xbox", "nintendo", "jatekkonzol",
        "jatek konzol", "videokonzol", "videjatek", "controller",
        "joystick", "gamepad", "gamer", "vr", "kinect",
    ],
    # Smart Home
    "Smart Home": [
        "smarthome", "smart home", "okos otthon", "okosotthon", "okos", "smart",
        "wifi", "wi-fi", "zigbee", "z-wave", "smart plug", "smart bulb",
        "smart lock", "okoslampa", "okoslampa", "okostermosztat", "smart thermostat",
        "security camera", "biztonsagi kamera", "kapucsengo", "kapucsengo",
    ],
    # Home: textiles and home accessories
    "Otthon": [
        "paplan", "parna", "parna", "agynemu", "takaritokeszlet", "takaro", "szonyeg",
        "fuggony", "fuggony", "asztalterito", "terito", "lampa", "vilagitas", "vilagit", "otthon",
        "haztartasi kiegeszito", "dekoracio", "asztalterito", "torolkozo",
    ],
    # Home decoration / furnishing
    "Lakberendezés": [
        "butor", "szekreny", "asztal", "szek", "polc", "komod", "kanape",
        "fotel", "agykeret", "agy", "gardrob", "tukor", "tukor", "cipotarolo", "ciposzekreny",
    ],
    # Garden
    "Kert": [
        "kert", "kerti", "funyiro", "furolap", "funyiro", "funyirogép",
        "szegelynyiro", "permetezes", "locsolo", "locsolo", "trimmer",
        "furesz", "lancfuresz", "lombfuvo", "lombszivo", "grill", "kerti butor",
        "medence", "medence", "kerti grill", "kerti szerszam", "kemping",
    ],
    # Toys
    "Játékok": [
        "jatek", "tarsasjatek", "lego", "pluss", "jatekauto", "jatekfigura",
        "barbie", "babajatek", "baba jatek", "puzzle", "tarsas", "jatekkartya",
    ],
    # Fashion
    "Divat": [
        "ruha", "polo", "poló", "ing", "nadrag", "kabát", "szoknya",
        "cipo", "cipő", "csizma", "csizma", "cipo", "öv", "ov",
        "sapka", "kalap", "sal", "kesztyu", "divat", "divatos",
    ],
    # Beauty
    "Szépség": [
        "parfum", "parfüm", "smink", "kozmetikum", "arckrem", "arckrém",
        "hajszarito", "hajszárító", "hajvasalo", "hajvasaló", "borotva", "epilator",
        "szempillaspiral", "puder", "púder", "ruzs", "ruzs", "kozmetika", "kozmetikai",
    ],
    # Drug store / household consumables
    "Drogéria": [
        "higienia", "higiénia", "fogkefe", "fogkrem", "sampon", "dezodor", "spray",
        "szappan", "tusfurdo", "tusfürdő", "wc papir", "wc papir", "mososzer",
        "mososzer", "oblito", "oblitő", "tisztitoszer", "tisztitoszer",
        "fertotlenito", "fertőtlenítő", "mosogatoszer", "mosogato szer",
    ],
    # Baby
    "Baba": [
        "baba", "babatap", "baba tap", "babakocsi", "babahordozo", "pelenka",
        "cumisuveg", "cumis uveg", "babaruhazat", "babajatek", "jaroka",
    ],
    # Sport
    "Sport": [
        "sport", "kerekpar", "kerékpár", "futopad", "futópad", "bicikli", "bicikli",
        "labda", "kosarlabda", "kosárlabda", "teniszueto", "teniszuto", "foci",
        "fitnesz", "edzogep", "edzőgép", "protein", "kondi", "rugalmas szalag",
    ],
    # Health
    "Egészség": [
        "vitamin", "gyogyszer", "gyógyszer", "gyogyaszat", "gyógyászat", "lazmero",
        "lázmérő", "orvosi", "masszirozo", "masszírozó", "fajdalomcsillapito",
        "fájdalomcsillapító", "ortopedia", "ortopéd", "fertotlenito", "fertőtlenítő",
    ],
    # Vision
    "Látás": [
        "szemuveg", "szemüveg", "kontaktlencse", "kontaktlencse", "kontakt", "napszemuveg", "napszemüveg", "optika",
    ],
    # Animals
    "Állatok": [
        "kutya", "macska", "kutyatap", "macskatáp", "macskatap", "allateledel", "állateledel",
        "allat", "allatfelszereles", "allat felszereles", "nyakorv", "kutyanyakorv", "akvarium",
        "terrarium", "kutyahaz", "macskabutor", "kisallat", "kis allat", "madareteto",
    ],
    # Books
    "Könyv": [
        "konyv", "könyv", "regeny", "regény", "novella", "tankonyv", "tankönyv",
        "album", "kepregeny", "képregény", "szotar", "szótár", "enciklopedia",
        "lexikon", "konyvek", "konyvcsomag",
    ],
    # Travel
    "Utazás": [
        "borond", "bőrönd", "utazo", "utazó", "taska", "táska", "utazotaska",
        "kemping", "turabota", "turabot", "halozsak", "hálózsák", "sator", "sátor",
        "hatizsak", "hátizsák", "bortart", "alomhazak", "hordozo bőrönd",
    ],
    # Office & school
    "Iroda & iskola": [
        "iroda", "iskola", "toll", "ceruza", "papir", "papír", "fuzet", "füzet",
        "jegyzet", "iroszer", "írószer", "nyomtato", "nyomtató", "fenymasolo",
        "fénymásoló", "iratrendezo", "iratrendező", "mappa", "szamologep", "számológép",
        "tuzogep", "tűzőgép", "irodaszer", "asztali lampa",
    ],
    # Tools & DIY
    "Szerszám & barkács": [
        "furogep", "fúrógép", "furo", "fúró", "csavarhuzo", "csavarhúzó", "kalapacs",
        "kalapács", "fogo", "fogó", "veso", "véső", "csiszolo", "csiszoló",
        "reszelo", "reszelő", "furesz", "fűrész", "satu", "flex", "sarokcsiszolo",
        "hegeszto", "hegesztő", "ragasztopisztoly", "keszlet", "csavar", "racsni",
    ],
    # Auto / motor & car care
    "Autó/Motor & autóápolás": [
        "auto", "autó", "motor", "motorkerekpar", "motorkerékpár", "motoros",
        "autoapolas", "autóápolás", "autoapolo", "autóápoló", "akkumulator", "akkumulátor",
        "motorolaj", "olaj", "kenoanyag", "kenőanyag", "szelvedo", "szélvédő",
        "ablakmoso", "ablakmosó", "gumi", "abroncs", "kerek", "felni", "ules", "ülés", "lojalis",
    ],
}


# Mapping from partner's original categories (if provided) to our high‑level ones.
ORIGINAL_TO_TARGET: Dict[str, str] = {
    "haztartasi_gepek": "Háztartási gépek",
    "elektronika": "Elektronika",
    "szamitastechnika": "Számítástechnika",
    "mobil": "Mobil & kiegészítők",
    "gaming": "Gaming",
    "smarthome": "Smart Home",
    "otthon": "Otthon",
    "lakberendezes": "Lakberendezés",
    "konyha": "Konyha & főzés",
    "kert": "Kert",
    "jatek": "Játékok",
    "divat": "Divat",
    "szepseg": "Szépség",
    "drogeria": "Drogéria",
    "baba": "Baba",
    "sport": "Sport",
    "egeszseg": "Egészség",
    "latas": "Látás",
    "allat": "Állatok",
    "konyv": "Könyv",
    "utazas": "Utazás",
    "iroda": "Iroda & iskola",
    "szerszam": "Szerszám & barkács",
    "barkacs": "Szerszám & barkács",
    "auto": "Autó/Motor & autóápolás",
    "motor": "Autó/Motor & autóápolás",
    "autoapolas": "Autó/Motor & autóápolás",
    "multi": "Multi",
}


def assign_category(cat_fields: Dict[str, Optional[str]]) -> str:
    """Assign a high‑level category based on the provided field values.

    Parameters
    ----------
    cat_fields:
        A dictionary of field names to values extracted from the partner's feed.
        Typical keys include ``PRODUCTNAME``, ``CATEGORYTEXT``, ``g:product_type``
        and ``category``.  Any non‑string values are ignored.  The values are
        concatenated, normalised (lowercased, accents stripped) and scanned
        against a series of keyword lists.  The first matching category is
        returned.

    Returns
    -------
    str
        One of the predefined categories listed above.  If no keywords match
        and the partner's own ``category`` field matches a known label, a
        translation is returned.  Otherwise ``"Multi"``.
    """
    # Prepare a single lowercase, accentless text for matching
    text = _prepare_text(cat_fields)

    # Iterate through categories in order of priority
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            # Using a simple substring search for performance; keywords are
            # already normalised without accents.  Word boundaries are not
            # enforced so that composite terms like "mosogépek" also match
            # "mosogep".
            if kw in text:
                return category

    # No keyword matched; attempt to map partner's original category
    # Some feeds may place the category name in different fields; we try
    # ``category``, ``categorytext`` and ``g:product_type`` in order.
    for key in ("category", "CATEGORYTEXT", "g:product_type", "product_type"):
        raw = cat_fields.get(key) or cat_fields.get(key.upper())
        if not raw:
            continue
        raw_norm = _strip_accents(str(raw)).lower()
        # Extract the last segment after any separators (\n or > or /)
        # to improve matching; e.g. "Elektronika > TV" → "tv"
        # We'll split on common delimiters and iterate from last to first.
        for seg in re.split(r"[\n>/|»]+", raw_norm)[::-1]:
            seg = seg.strip()
            if not seg:
                continue
            if seg in ORIGINAL_TO_TARGET:
                return ORIGINAL_TO_TARGET[seg]
            # Some partner categories include plural forms or suffixes; try
            # stripping trailing 'ok', 'ek', 'ak' etc.  This rudimentary
            # stemming helps map "haztartasigepek" to "haztartasi_gepek".
            seg_stripped = re.sub(r"(ok|ek|ak)$", "", seg)
            if seg_stripped in ORIGINAL_TO_TARGET:
                return ORIGINAL_TO_TARGET[seg_stripped]

    # Default fallback
    return "Multi"


if __name__ == "__main__":  # pragma: no cover
    # Basic self‑test to exercise the classifier.  This block is not
    # exhaustive but demonstrates how the heuristics behave on a small
    # selection of synthetic examples.  It prints category assignments to
    # stdout and can be run manually for sanity checks.
    tests = [
        {"PRODUCTNAME": "Falmec Inox 90 páraelszívó", "category": "multi"},
        {"PRODUCTNAME": "Bosch WAT28420 mosógép", "category": "haztartasi_gepek"},
        {"PRODUCTNAME": "Sony Bravia 55\" LED TV", "category": "elektronika"},
        {"PRODUCTNAME": "Dell Inspiron laptop", "category": "szamitastechnika"},
        {"PRODUCTNAME": "Apple iPhone 14", "category": "mobil"},
        {"PRODUCTNAME": "PlayStation 5 játék konzol", "category": "gaming"},
        {"PRODUCTNAME": "Philips Hue okos lámpa", "category": "smarthome"},
        {"PRODUCTNAME": "Ágynemű garnitúra", "category": "otthon"},
        {"PRODUCTNAME": "Kerti fűnyíró gép", "category": "kert"},
        {"PRODUCTNAME": "Cata 600 páraelszívó", "CATEGORYTEXT": "Konyha > Főzés", "category": "multi"},
    ]
    for i, t in enumerate(tests, 1):
        cat = assign_category(t)
        print(f"Test {i}: {t.get('PRODUCTNAME', '')} → {cat}")
