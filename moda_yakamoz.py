import requests
import xml.etree.ElementTree as ET
from googletrans import Translator
import time
from datetime import datetime
import os

def fetch_exchange_rate():
    try:
        response = requests.get("https://api.exchangerate.host/latest?base=TRY&symbols=USD")
        data = response.json()
        return float(data["rates"]["USD"])
    except Exception as e:
        print("Failed to fetch exchange rate:", e)
        return 0.032  # fallback default rate




def fetch_url_with_retries(url, retries=5, backoff_factor=60):
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(1, retries + 1):
        try:
            print(f"Fetching XML (Attempt {attempt})...")
            response = requests.get(url, headers=headers, timeout=900)  # 15 minutes
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt == retries:
                print("All retry attempts failed.")
                raise
            wait_time = backoff_factor * attempt
            print(f"Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)


def run_script_moda_yakamoz():
    print("Running Moda Yakamoz XML translation...")

    url = "https://modayakamoz.com/xml/yalin1"
    xml_data = fetch_url_with_retries(url)

    root = ET.fromstring(xml_data)

    translator = Translator()
    exchange_rate = fetch_exchange_rate()

    translated_root = ET.Element("Products")

    for product in root.findall("Product"):
        translated_product = ET.SubElement(translated_root, "Product")

        for tag in product:
            if tag.tag == "ProductAttributes":
                translated_attributes = ET.SubElement(translated_product, "ProductAttributes")
                for attr in tag.findall("ProductAttribute"):
                    translated_attr = ET.SubElement(translated_attributes, "ProductAttribute")

                    variant_name = attr.find("VariantName")
                    variant_value = attr.find("VariantValue")

                    if variant_name is not None:
                        translated_name = translator.translate(variant_name.text or "", src="tr", dest="en").text
                        ET.SubElement(translated_attr, "VariantName").text = translated_name

                    if variant_value is not None:
                        translated_value = translator.translate(variant_value.text or "", src="tr", dest="en").text
                        ET.SubElement(translated_attr, "VariantValue").text = translated_value

            elif tag.tag == "SatisFiyati":
                try:
                    price_try = float(tag.text.replace(",", "."))
                    price_usd = round(price_try * exchange_rate, 2)
                    ET.SubElement(translated_product, "Price").text = str(price_usd)
                except:
                    ET.SubElement(translated_product, "Price").text = "0.00"

            elif tag.tag in ["UrunAdi", "Aciklama", "Kategori"]:
                translated_text = translator.translate(tag.text or "", src="tr", dest="en").text
                ET.SubElement(translated_product, tag.tag).text = translated_text
            else:
                ET.SubElement(translated_product, tag.tag).text = tag.text

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "translated"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"moda_yakamoz_translated_{timestamp}.xml")
    ET.ElementTree(translated_root).write(output_file, encoding="utf-8", xml_declaration=True)

    print(f"Saved translated XML to {output_file}")

if __name__ == "__main__":
    run_script_moda_yakamoz()
