print("[AWIN] Feedlist betöltése helyi CSV-ből (scripts/datafeeds.csv)")
feedlist = []
with open("scripts/datafeeds.csv", newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # az AWIN CSV oszlopnevei: merchant_name, fid, datafeed_url stb.
        if row.get("Merchant Name") in ["AliExpress EU", "Alibaba EU", "Lunzo HU"]:
            feedlist.append({
                "merchant_name": row["Merchant Name"],
                "fid": row["Feed ID"],
                "datafeed_url": row["Datafeed URL"]
            })
