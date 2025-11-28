# pepita_category_assign.py
#
# Pepita (Dognet) → Findora 25 fő kategória (findora_main)
#
# Bemenet:
#   docs/feeds/pepita/page-*.json
#   (mezők: title, desc, category_path, category_root, stb.)
#
# Kimenet:
#   Ugyanazok a page-*.json fájlok FELÜLÍRVA,
#   minden item-hez beírva:
#       item["findora_main"] = "<backend_kategoria_slug>"
#
# Használt Findora fő kategória kulcsok:
#   elektronika
#   haztartasi_gepek
#   szamitastechnika
#   mobil
#   gaming
#   smart_home
#   otthon
#   lakberendezes
#   konyha_fozes
#   kert
#   jatekok
#   divat
#   szepseg
#   drogeria
#   baba
#   sport
#   egeszseg
#   latas
#   allatok
#   konyv
#   utazas
#   iroda_iskola
#   szerszam_barkacs
#   auto_motor
#   multi
#
# FUTTATÁS (repo gyökeréből):
#   python pepita_category_assign.py
#

import os
import json
import glob


PEPITA_DIR = os.path.join("docs", "feeds", "pepita")


def norm(s: str) -> str:
    """Egyszerű normalizálás összehasonlításhoz."""
    if not s:
        return ""
    return " ".join(str(s).strip().lower().split())


def map_pepita_category(category_path: str, category_root: str) -> str:
    """
    Pepita kategóriák → Findora findora_main slug.

    category_path pl.:
        "Játékok > Kreatív & Építő játékok"
    category_root pl.:
        "Játékok"
    """

    cp = category_path or ""
    cr = category_root or ""

    cp_n = norm(cp)
    cr_n = norm(cr)

    # ===== 1. BABÁK & TIPEGŐK → baba =====
    if cr_n == norm("Babák & Tipegők"):
        return "baba"

    # ===== 2. BÚTOROK =====
    if cr_n == norm("Bútorok"):
        # Speciális: babaszoba → baba
        if "babaszoba" in cp_n:
            return "baba"
        # Minden más bútor → lakberendezés
        return "lakberendezes"

    # ===== 3. DIVAT & ÖLTÖZKÖDÉS → divat =====
    if cr_n == norm("Divat & Öltözködés"):
        return "divat"

    # ===== 4. IRODASZER & ÍRÓSZER → iroda_iskola =====
    if cr_n == norm("Irodaszer & Írószer"):
        return "iroda_iskola"

    # ===== 5. JÁRMŰVEK & ALKATRÉSZEK → auto_motor =====
    if cr_n == norm("Járművek & Alkatrészek"):
        return "auto_motor"

    # ===== 6. JÁTÉKOK → jatekok =====
    if cr_n == norm("Játékok"):
        return "jatekok"

    # ===== 7. KÖNYVEK → konyv =====
    if cr_n == norm("Könyvek"):
        return "konyv"

    # ===== 8. MŰSZAKI CIKK & ELEKTRONIKA =====
    if cr_n == norm("Műszaki cikk & Elektronika"):
        # Részletes bontás subkategória szerint
        if "gaming" in cp_n:
            return "gaming"
        if "számítógépek és kiegészítők" in cp_n:
            return "szamitastechnika"
        if "telefonok" in cp_n:
            return "mobil"
        if "szépségápolási gépek" in cp_n:
            return "szepseg"
        # Minden audio / tv / foto stb. → elektronika
        return "elektronika"

    # ===== 9. MŰVÉSZET & HOBBI → otthon (hobbi, kreatív, dekor) =====
    if cr_n == norm("Művészet & Hobbi"):
        return "otthon"

    # ===== 10. OTTHON & KERT =====
    if cr_n == norm("Otthon & Kert"):
        # Biztonság, háztartási kellék, lámpa, party stb. → otthon
        if "háztartási kisgépek" in cp_n or "háztartási nagygépek" in cp_n:
            return "haztartasi_gepek"
        if "konyha & étkezés" in cp_n:
            return "konyha_fozes"
        if cp_n.startswith("otthon & kert > kert") or "kerti" in cp_n:
            return "kert"
        if "dekorációk" in cp_n:
            return "lakberendezes"
        # Egyéb otthon & kert → otthon
        return "otthon"

    # ===== 11. SPORT & SZABADIDŐ → sport =====
    if cr_n == norm("Sport & Szabadidő"):
        return "sport"

    # ===== 12. SZÉPSÉG & EGÉSZSÉG =====
    if cr_n == norm("Szépség & Egészség"):
        if (
            "egészségügyi eszközök" in cp_n
            or "otthoni betegápolás" in cp_n
            or "masszázs" in cp_n
            or "szájápolás" in cp_n
        ):
            return "egeszseg"
        if (
            "fodrászat & kozmetika" in cp_n
            or "hajápolás" in cp_n
            or "kézápolás" in cp_n
            or "lábápolás" in cp_n
            or "körömápolás" in cp_n
            or "sminkelés" in cp_n
            or "szőrtelenítés" in cp_n
            or "borotválkozás" in cp_n
        ):
            return "szepseg"
        if "testápolás & higiénia" in cp_n:
            return "drogeria"
        # fallback: szépség
        return "szepseg"

    # ===== 13. ÁLLATTARTÁS → allatok =====
    if cr_n == norm("Állattartás"):
        return "allatok"

    # ===== 14. ÉLELMISZER & ITAL → multi (nincs külön élelmiszer kategória) =====
    if cr_n == norm("Élelmiszer & Ital"):
        return "multi"

    # ===== 15. ÉPÍTKEZÉS & FELÚJÍTÁS → szerszam_barkacs =====
    if cr_n == norm("Építkezés & Felújítás"):
        return "szerszam_barkacs"

    # ===== fallback =====
    return "multi"


def process_page(path: str) -> None:
    print(f"[INFO] Feldolgozás: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items") or []
    changed = 0

    for it in items:
        cp = it.get("category_path") or it.get("category_text") or ""
        cr = it.get("category_root") or ""
        findora_main = map_pepita_category(cp, cr)
        if it.get("findora_main") != findora_main:
            it["findora_main"] = findora_main
            changed += 1

    data["items"] = items

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] {os.path.basename(path)} – {len(items)} termék, {changed} módosítva")


def main():
    if not os.path.isdir(PEPITA_DIR):
        print(f"[HIBA] Nem találom a pepita mappát: {PEPITA_DIR}")
        return

    pattern = os.path.join(PEPITA_DIR, "page-*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"[HIBA] Nem találtam page-*.json fájlokat a {PEPITA_DIR} alatt.")
        return

    print(f"[INFO] Összes pepita page: {len(files)}")

    for path in files:
        process_page(path)

    print("[KÉSZ] pepita_category_assign lefutott minden page-re.")


if __name__ == "__main__":
    main()
