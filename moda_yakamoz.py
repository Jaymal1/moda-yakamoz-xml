import xml.etree.ElementTree as ET
import requests
from deep_translator import GoogleTranslator
from datetime import datetime
import os

# Constants
XML_URL = "https://modayakamoz.com/xml/yalin1"
OUTPUT_FILE = "translated_modayakamoz.xml"
TRANSLATED_IDS_FILE = "translated_ids_modayakamoz.txt"
EXCHANGE_RATE_API = "https://api.exchangerate.host/latest?base=TRY&symbols=USD"

# Load already translated product IDs
def load_translated_ids():
    if os.path.exists(TRANSLATED_IDS_FILE):
        with open(TRANSLATED_IDS_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    return set()

# Save newly translated product IDs
def save_translated_ids(ids):
    with open(TRANSLATED_IDS_FILE, "a") as f:
        for id in ids:
            f.write(f"{id}\n")

# Get exchange rate
try:
    exchange_rate = requests.get(EXCHANGE_RATE_API).json()["rates"]["USD"]
except:
    exchange_rate = 0.031  # fallback value

# Download XML
data = requests.get(XML_URL).content
root = ET.fromstring(data)

# Prepare output root
output_root = ET.Element("Urunler")
translated_ids = load_translated_ids()
newly_translated_ids = []

for urun in root.findall("Urun"):
    product_id = urun.findtext("UrunKartiID")
    if product_id in translated_ids:
        continue

    translated_product = ET.SubElement(output_root, "Urun")

    def translate(text):
        return GoogleTranslator(source="tr", target="en").translate(text) if text else ""

    # Basic translations
    ET.SubElement(translated_product, "ID").text = product_id
    ET.SubElement(translated_product, "Name").text = translate(urun.findtext("UrunAdi"))
    ET.SubElement(translated_product, "Description").text = translate(urun.findtext("Aciklama"))
    ET.SubElement(translated_product, "Brand").text = urun.findtext("Marka")
    ET.SubElement(translated_product, "URL").text = urun.findtext("UrunUrl")

    # Images
    image_block = ET.SubElement(translated_product, "Images")
    for img in urun.findall("Resimler/Resim"):
        ET.SubElement(image_block, "Image").text = img.text

    # Variants
    variants_block = ET.SubElement(translated_product, "Variants")
    for secenek in urun.findall("UrunSecenek/Secenek"):
        variant = ET.SubElement(variants_block, "Variant")
        ET.SubElement(variant, "StockCode").text = secenek.findtext("StokKodu")
        ET.SubElement(variant, "Barcode").text = secenek.findtext("Barkod")
        ET.SubElement(variant, "StockQuantity").text = secenek.findtext("StokAdedi")

        try:
            price = float(secenek.findtext("SatisFiyat") or secenek.findtext("SatisFiyati"))
        except:
            price = 0.0
        usd_price = round(price * exchange_rate, 2)
        ET.SubElement(variant, "PriceUSD").text = str(usd_price)

        # Translate attributes
        attributes_block = ET.SubElement(variant, "Attributes")
        for ozellik in secenek.findall("EkSecenekOzellik/Ozellik"):
            attr = ET.SubElement(attributes_block, "Attribute")
            ET.SubElement(attr, "Name").text = translate(ozellik.get("Tanim"))
            ET.SubElement(attr, "Value").text = translate(ozellik.get("Deger"))

    newly_translated_ids.append(product_id)

# Write output
ET.ElementTree(output_root).write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)
save_translated_ids(newly_translated_ids)
print(f"Translated {len(newly_translated_ids)} new products on {datetime.now().isoformat()}")
