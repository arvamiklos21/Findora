from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

# A publikált oldalad alap URL-je
BASE_URL = "https://www.findora.hu"

# A GitHub Pages által publikált mappa
DOCS_DIR = Path("docs")

# Ide fogjuk generálni a sitemap-et
OUTPUT_PATH = DOCS_DIR / "sitemap.xml"

# Olyan HTML fájlok, amiket NEM akarunk a sitemap-be tenni
EXCLUDE_FILENAMES = {
    "#_---_általános_keresési_kulcsszavak_---.html",
    "google6fdc3fd590a35a5d.html",
}

def collect_html_files():
    """
    Összegyűjti a docs/ alatti .html fájlokat, kivéve az EXCLUDE_FILENAMES-ben lévőket.
    """
    files = []
    for path in sorted(DOCS_DIR.glob("*.html")):
        if path.name in EXCLUDE_FILENAMES:
            continue
        files.append(path)
    return files

def build_sitemap(urls):
    """
    Felépíti az XML sitemap struktúrát az összegyűjtött fájlokból.
    """
    urlset = ET.Element(
        "urlset",
        attrib={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"},
    )

    today = datetime.utcnow().strftime("%Y-%m-%d")

    for path in urls:
        url_el = ET.SubElement(urlset, "url")

        # <loc>https://www.findora.hu/valami.html</loc>
        loc_el = ET.SubElement(url_el, "loc")
        loc_el.text = f"{BASE_URL}/{path.name}"

        # <lastmod>YYYY-MM-DD</lastmod>
        lastmod_el = ET.SubElement(url_el, "lastmod")
        lastmod_el.text = today

        # <changefreq>...</changefreq>
        changefreq_el = ET.SubElement(url_el, "changefreq")
        if path.name == "index.html":
            changefreq_el.text = "daily"
        else:
            changefreq_el.text = "weekly"

        # <priority>...</priority>
        priority_el = ET.SubElement(url_el, "priority")
        if path.name == "index.html":
            priority_el.text = "1.0"
        else:
            priority_el.text = "0.8"

    return urlset

def write_sitemap(urlset):
    """
    Kiírja az XML-t a docs/sitemap.xml fájlba.
    """
    tree = ET.ElementTree(urlset)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tree.write(OUTPUT_PATH, encoding="utf-8", xml_declaration=True)

def main():
    html_files = collect_html_files()
    if not html_files:
        print("No HTML files found under docs/.")
        return

    urlset = build_sitemap(html_files)
    write_sitemap(urlset)
    print(f"Sitemap generated at {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
