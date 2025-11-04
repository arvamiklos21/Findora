-    items = []
-    # Heureka feed: SHOPITEM elemek
-    shopitems = [e for e in root.iter() if strip_ns(e.tag) == "SHOPITEM"]
+    items = []
+    # Keressünk több lehetséges elemnevet (namespace-függetlenül)
+    def lname(x): 
+        return strip_ns(x.tag).upper()
+    CAND_ITEM = {"SHOPITEM", "ITEM", "PRODUCT", "OFFER", "ENTRY"}
+    shopitems = [e for e in root.iter() if lname(e) in CAND_ITEM]

     for it in shopitems:
-        title = (findtext_ci(it, ["PRODUCTNAME", "NAME", "TITLE"]) or "").strip()
-        url   = (findtext_ci(it, ["URL"]) or "").strip()
-        img   = (findtext_ci(it, ["IMGURL", "IMGURL_ALTERNATIVE"]) or "").strip()
-        price = (findtext_ci(it, ["PRICE_VAT", "PRICE"]) or "").strip()
+        title = (findtext_ci(it, [
+            "PRODUCTNAME","PRODUCT","NAME","TITLE","ITEM_NAME"
+        ]) or "").strip()
+        url   = (findtext_ci(it, [
+            "URL","ITEM_URL","PRODUCTURL","LINK"
+        ]) or "").strip()
+        img   = (findtext_ci(it, [
+            "IMGURL","IMGURL_ALTERNATIVE","IMAGE","IMAGE_URL","IMG"
+        ]) or "").strip()
+        price = (findtext_ci(it, [
+            "PRICE_VAT","PRICE","PRICE_WITH_VAT","ITEM_PRICE","PRICE_FINAL"
+        ]) or "").strip()
