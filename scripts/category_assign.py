# category_assign.py
"""
Findora – kategória hozzárendelés Alza XML-ekhez (product_type alapján).

Visszaadott értékek:
  - "kat-elektronika"
  - "kat-gepek"
  - "kat-otthon"
  - "kat-kert"
  - "kat-jatekok"
  - "kat-divat"
  - "kat-szepseg"
  - "kat-sport"
  - "kat-latas"
  - "kat-konyv"
  - "kat-utazas"
  - "kat-multi"
vagy None (ha nem tudunk dönteni, vagy nem alza partner).
"""

import unicodedata
import re
from typing import Any, Dict, Optional


# ===== Segéd: normalizált szöveg =====

def _norm(s: str) -> str:
    if not s:
        return ""
    s = str(s)
    s = s.lower()
    # ékezetek leszedése
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # whitespace normalizálás
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _split_product_type(pt_raw: str) -> (str, str):
    """
    "PC és laptop | Kiegészítők" → ("pc es laptop", "kiegeszitok")
    """
    norm = _norm(pt_raw)
    if "|" in norm:
        main, sub = norm.split("|", 1)
        return main.strip(), sub.strip()
    return norm, ""


# ===== Kat-* konstansok =====

KAT_ELEKTRONIKA = "kat-elektronika"
KAT_GEPEK       = "kat-gepek"
KAT_OTTHON      = "kat-otthon"
KAT_KERT        = "kat-kert"
KAT_JATEKOK     = "kat-jatekok"
KAT_DIVAT       = "kat-divat"
KAT_SZEPSEG     = "kat-szepseg"
KAT_SPORT       = "kat-sport"
KAT_LATAS       = "kat-latas"
KAT_KONYV       = "kat-konyv"
KAT_UTAZAS      = "kat-utazas"
KAT_MULTI       = "kat-multi"


# ===== Alza-specifikus szabályok =====

def _assign_alza(product_type: str) -> Optional[str]:
    main, sub = _split_product_type(product_type)

    # --- PC, laptop, hálózat, nyomtató, szoftver → ELEKTRONIKA ---
    if main.startswith("pc es laptop") or main.startswith("počítače a notebooky") or main.startswith("pocitace a notebooky"):
        # minden PC-s dolog nálad Elektronika
        return KAT_ELEKTRONIKA

    # --- Telefon, tablet, okosóra / mobily, chytré hodinky → ELEKTRONIKA ---
    if (
        main.startswith("telefon, tablet, okosora")
        or main.startswith("mobily, chytre hodinky, tablety")
    ):
        return KAT_ELEKTRONIKA

    # --- TV / fotó / audió / video → ELEKTRONIKA ---
    if main.startswith("tv, foto") or main.startswith("tv, fotó") or main.startswith("tv, foto, audio-video"):
        # hangfal, soundbar, fejhallgató, TV, kamera, drón, rádió, hi-fi stb.
        return KAT_ELEKTRONIKA

    # --- Okosotthon / Chytrá domácnost → ELEKTRONIKA ---
    if main.startswith("okosotthon") or main.startswith("chytra domacnost"):
        return KAT_ELEKTRONIKA

    # --- Gaming & szórakozás / Gaming, hry a zábava ---
    if main.startswith("gaming es szorakozas") or main.startswith("gaming, hry a zabava"):
        # külön választva a táblázatod szerint
        if "tarsasjatek" in sub:
            return KAT_JATEKOK
        if "pc es konzoljatekok" in sub or "pc gaming" in sub:
            return KAT_ELEKTRONIKA
        if "xbox" in sub or "playstation" in sub or "nintendo switch" in sub:
            return KAT_ELEKTRONIKA
        if "virtualis valosag" in sub:
            return KAT_ELEKTRONIKA
        if "merch" in sub or "figurka" in sub or "ajandekok" in sub:
            # Filmes és gamer ajándékok → Elektronika nálad
            return KAT_ELEKTRONIKA
        # alapértelmezés: játék
        return KAT_JATEKOK

    # --- Játék, baba-mama / Hračky, pro děti a miminka → JÁTÉKOK ---
    if main.startswith("jatek, baba-mama") or main.startswith("hracky, pro deti a miminka"):
        return KAT_JATEKOK

    # --- Sport, szabadidő / Sport a outdoor → SPORT / SZÉPSÉG / UTAZÁS ---
    if main.startswith("sport, szabadido") or main.startswith("sport a outdoor"):
        # Hátizsák - táska / Batohy a zavazadla → Utazás
        if "hatizsak" in sub or "batoh" in sub or "zavazadla" in sub:
            return KAT_UTAZAS
        # Sporttápszerek / sportovní výživa → Sport
        if "sporttap" in sub or "sporttap szer" in sub or "sportovni vyziva" in sub:
            return KAT_SPORT
        # Egészséges ételek → Szépség (nálad így volt)
        if "egeszseges etelek" in sub:
            return KAT_SZEPSEG
        return KAT_SPORT

    # --- Háztartási kisgép / Domácí a osobní spotřebiče → GÉPEK / SZÉPSÉG ---
    if main.startswith("haztartasi kisgep") or main.startswith("domaci a osobni spotrebice"):
        # Haj- és szakállápolás / Péče o vlasy a vousy → Szépség
        if "haj-" in sub or "haj es szakallapolas" in sub or "pece o vlasy a vousy" in sub:
            return KAT_SZEPSEG
        # egyéb kisgépek: kávéfőző, vízforraló, porszívó, légkezelés stb. → gépek
        return KAT_GEPEK

    # --- Háztartási nagygép / Velké spotřebiče → GÉPEK ---
    if main.startswith("haztartasi nagyg") or main.startswith("velke spotrebice"):
        return KAT_GEPEK

    # --- Konyha, háztartás / Kuchyňské a domácí potřeby → OTTHON ---
    if main.startswith("konyha, haztartas") or main.startswith("kuchynske a domaci potreby"):
        # minden itt: tálalás, konyhai eszközök, sütési kellékek, takarítás → otthon
        return KAT_OTTHON

    # --- Otthon, barkács, kert / Dům, dílna a zahrada → OTTHON vagy KERT ---
    if main.startswith("otthon, barkacs, kert") or main.startswith("dum, dilna a zahrada"):
        # Otthoni / lakberendezős dolgok
        if (
            "butor" in sub
            or "lakberendezes" in sub
            or "dekoracio" in sub
            or "dekorace" in sub
            or "lakberendezesi kell" in sub
            or "lakberendezesi kiegeszitok" in sub
            or "evszakok szerint" in sub
            or "szaunak" in sub
        ):
            return KAT_OTTHON

        # Műhely, szerszám, építés, kert, medence, grill stb. → kert
        if (
            "kert" in sub
            or "grill" in sub
            or "udirny" in sub
            or "grillek" in sub
            or "epitoipar" in sub
            or "epites" in sub
            or "muhely" in sub
            or "zahrada" in sub
            or "dilna" in sub
            or "szerszam" in sub
            or "elektromos halozat" in sub
            or "elektroinstalace" in sub
            or "medencek" in sub
        ):
            return KAT_KERT

        # Széfek, zárak, lakatok / Zabezpečení a zámečnictví → kert (nálad így ment)
        if "szef" in sub or "zar" in sub or "lakat" in sub or "zabezpeceni" in sub:
            return KAT_KERT

        # ha nem egyértelmű, de „dílna / dílna, zahrada” jelleg → kert
        if "dilna" in sub:
            return KAT_KERT

        # alapértelmezés: otthon
        return KAT_OTTHON

    # --- Irodai felszerelés / Kancelář a papírnictví → KÖNYV vagy OTTHON ---
    if main.startswith("irodai felszereles") or main.startswith("kancelar a papirnictvi"):
        # Irodaszerek, iskolaszerek, papír írószer → Könyv
        if (
            "irodaszerek" in sub
            or "iskolaszerek" in sub
            or "papirnictvi" in sub
            or "skolni potreby" in sub
        ):
            return KAT_KONYV
        # Irodatechnika, irodabútor → otthon (iroda / home office)
        return KAT_OTTHON

    # --- Illatszer, ékszer / Kosmetika, parfémy a krása → SZÉPSÉG / DIVAT ---
    if main.startswith("illatszer, ekszer") or main.startswith("kosmetika, parfemy a krasa") or main.startswith("kosmetika, parfémy a krása"):
        # Ékszerek, karórák → Divat
        if "ekszerek" in sub or "ekszer" in sub or "karorak" in sub or "karora" in sub:
            return KAT_DIVAT
        # egyéb: parfüm, smink, haj/arc/testrész → szépség
        return KAT_SZEPSEG

    # --- Drogéria / Drogerie → SZÉPSÉG vagy OTTHON ---
    if main.startswith("drogeria") or main.startswith("drogéria"):
        # Mosószerek → otthon (nálad így volt a nagy listában)
        if "mososzerek" in sub or "praci prostredky" in sub:
            return KAT_OTTHON
        # Gyertyák, illatpálcikák, szépségápolás, higiénia stb. → szépség
        return KAT_SZEPSEG

    # --- Egészségmegőrzés / Lékárna a zdraví → LÁTÁS vagy SZÉPSÉG ---
    if main.startswith("egeszsegmegorzes") or main.startswith("lekarn") or main.startswith("lekarn a zdravi") or main.startswith("lekarn a zdraví"):
        # szemüveg, kontaktlencse → látás
        if "szemuveg" in sub or "kontaklencs" in sub or "bryle" in sub:
            return KAT_LATAS
        # vitamin, étrendkiegészítő, gyógyászati segédeszköz → szépség
        return KAT_SZEPSEG

    # --- Élelmiszer → OTTHON ---
    if main.startswith("elelmiszer"):
        return KAT_OTTHON

    # --- Autó-motor / Auto-moto → UTAZÁS vagy KERT ---
    if main.startswith("auto-motor") or main.startswith("auto-moto") or main.startswith("autó-motor"):
        # utazós dolgok
        if (
            "csomagtartok es boxok" in sub
            or "csomagtartok" in sub
            or "boxok" in sub
            or "autohuto" in sub
            or "auto huto" in sub
            or "akku" in sub
            or "akumulator" in sub
            or "tolt" in sub
            or "folyadek" in sub
            or "elektromos jarmu" in sub
            or "kamionos felszereles" in sub
            or "tartozekok utanfutokhoz" in sub
        ):
            return KAT_UTAZAS
        # szerszám, gumi tartozékok, autóizzók, autós kiegészítők → kert (garázs / barkács)
        return KAT_KERT

    # --- Sport, szabadidő → SPORT (ha idáig nem lett kivétel) ---
    if main.startswith("sport, szabadido"):
        return KAT_SPORT

    # --- Játék, baba-mama → JÁTÉKOK (ha idáig nem lett kivétel) ---
    if main.startswith("jatek, baba-mama"):
        return KAT_JATEKOK

    # ha semmi nem illett rá, multi
    return KAT_MULTI


# ===== Publikus belépési pont =====

def assign_category(partner_id: str, item: Dict[str, Any]) -> Optional[str]:
    """
    partner_id: pl. "alza"
    item: a normalizált rekord (amit a build_*.py gyárt).

    Visszatér:
      - "kat-..." string, ha tudtunk kategóriát adni
      - None, ha nem (ilyenkor a frontend fallback / BASE_CATEGORY_BY_PARTNER dolgozik).
    """
    partner_id = (partner_id or "").strip().lower()

    if partner_id == "alza":
        # Alza: a product_type / categoryPath alapján
        pt = (
            item.get("product_type")
            or item.get("categoryPath")
            or item.get("category_path")
            or item.get("g:product_type")
            or ""
        )
        return _assign_alza(pt)

    # más partnerekre most nem nyúlunk – marad a régi logika / default
    return None
