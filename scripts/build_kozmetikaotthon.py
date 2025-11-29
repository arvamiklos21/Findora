def main():
    assert FEED_URL, "FEED_KOZMETIKAOTTHON_URL hiányzik (repo Secrets)."

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # régi JSON-ok törlése (globál + kategória + akcio)
    for old in OUT_DIR.rglob("*.json"):
        try:
            old.unlink()
        except OSError:
            pass

    # 1) XML letöltés + parse + dedup – hibatűrő módon
    try:
        xml_clean = fetch_xml(FEED_URL)
        raw_items = parse_items(xml_clean)
        items = dedup_size_variants(raw_items)
        print(f"ℹ KozmetikaOtthon: dedup után {len(items)} termék")
    except Exception as e:
        print(f"[WARN] KozmetikaOtthon feed hiba, üres struktúrát generálok: {e}")
        items = []

    # 2) NORMALIZÁLÁS + KÖZÖS KATEGORIZÁLÁS
    rows = []
    for it in items:
        pid = it["id"]
        title = it["title"]
        desc = it.get("desc") or ""
        url = it.get("url") or ""
        img = it.get("img") or ""
        price = it.get("price")
        discount = it.get("discount")
        category_path = it.get("category_path") or ""
        brand = it.get("brand") or ""

        # CSAK szépség kategória (partner_default = szepseg),
        # de a 25 kategória struktúra ettől még létrejön.
        findora_main = assign_category(
            title=title,
            desc=desc,
            category_path=category_path,
            brand=brand,
            partner="kozmetikaotthon",
            partner_default="szepseg",
        )

        # safety: ha valami hülyeséget ad vissza
        if not findora_main:
            findora_main = "szepseg"

        rows.append(
            {
                "id": pid,
                "title": title,
                "img": img,
                "desc": desc,
                "price": price,
                "discount": discount,
                "url": url,
                "partner": "kozmetikaotthon",
                "category_path": category_path,
                "findora_main": findora_main,
                "cat": findora_main,
            }
        )

    total = len(rows)
    print(f"[INFO] KozmetikaOtthon: normalizált sorok: {total}")

    # 3) HA NINCS EGYETLEN TERMÉK SEM
    if total == 0:
        print("⚠️ KozmetikaOtthon: nincs termék – üres struktúra generálása (25 kategória + akcio).")

        # Globál üres meta + üres page-0001
        paginate_and_write(
            OUT_DIR,
            [],
            PAGE_SIZE_GLOBAL,
            meta_extra={
                "partner": "kozmetikaotthon",
                "scope": "global",
            },
        )

        # Minden kategóriára üres meta + üres page-0001
        for slug in FINDORA_CATS:
            base_dir = OUT_DIR / slug
            paginate_and_write(
                base_dir,
                [],
                PAGE_SIZE_CAT,
                meta_extra={
                    "partner": "kozmetikaotthon",
                    "scope": f"category:{slug}",
                },
            )

        # Akciós blokk üres meta + üres page-0001
        akcio_dir = OUT_DIR / "akcio"
        paginate_and_write(
            akcio_dir,
            [],
            PAGE_SIZE_AKCIO_BLOCK,
            meta_extra={
                "partner": "kozmetikaotthon",
                "scope": "akcio",
            },
        )

        return

    # 4) GLOBÁL FEED
    paginate_and_write(
        OUT_DIR,
        rows,
        PAGE_SIZE_GLOBAL,
        meta_extra={
            "partner": "kozmetikaotthon",
            "scope": "global",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )

    # 5) KATEGÓRIA FEED-EK – 25 kategória mindenképp létezik
    buckets = {slug: [] for slug in FINDORA_CATS}
    for row in rows:
        slug = row.get("findora_main") or "szepseg"
        if slug not in buckets:
            slug = "szepseg"
            row["findora_main"] = "szepseg"
            row["cat"] = "szepseg"
        buckets[slug].append(row)

    for slug, items_cat in buckets.items():
        base_dir = OUT_DIR / slug
        paginate_and_write(
            base_dir,
            items_cat,
            PAGE_SIZE_CAT,
            meta_extra={
                "partner": "kozmetikaotthon",
                "scope": f"category:{slug}",
                "generated_at": datetime.utcnow().isoformat() + "Z",
            },
        )

    # 6) AKCIÓS BLOKK (discount >= 10%)
    akcios_items = [
        row for row in rows
        if row.get("discount") is not None and row["discount"] >= 10
    ]

    akcio_dir = OUT_DIR / "akcio"
    paginate_and_write(
        akcio_dir,
        akcios_items,
        PAGE_SIZE_AKCIO_BLOCK,
        meta_extra={
            "partner": "kozmetikaotthon",
            "scope": "akcio",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    )

    print(
        f"✅ KozmetikaOtthon kész: {total} termék, "
        f"{len(buckets)} kategória (mindegyiknek meta + legalább page-0001.json), "
        f"akciós blokk tételek: {len(akcios_items)} → {OUT_DIR}"
    )
