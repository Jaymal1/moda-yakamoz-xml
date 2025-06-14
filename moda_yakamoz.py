import os
import json
import hashlib
import requests
import xml.etree.ElementTree as ET
from deep_translator import GoogleTranslator
from forex_python.converter import CurrencyRates
import math
import copy
import xml.dom.minidom
import subprocess

def load_processed_ids(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_processed_ids(ids, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(list(ids), f)

def hash_text(text):
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()

def get_product_id(product):
    urunadi = product.find("UrunAdi")
    marka = product.find("Marka")
    resim = product.find("Resim")
    if urunadi is not None and marka is not None:
        raw_id = f"{urunadi.text}|{marka.text}|{resim.text if resim is not None else ''}"
        return hash_text(raw_id)
    return None

def run_script_moda_yakamoz():
    print("Running Moda Yakamoz XML translation...")

    url = "https://modayakamoz.com/xml/yalin1"
    response = requests.get(url)
    with open("original_moda.xml", "wb") as f:
        f.write(response.content)

    tree = ET.parse("original_moda.xml")
    root = tree.getroot()

    translator = GoogleTranslator(source="auto", target="en")
    currency = CurrencyRates()
    try:
        rate = currency.get_rate("TRY", "USD")
    except Exception as e:
        print(f"Currency API failed. Using fallback rate. Error: {e}")
        rate = 0.031

    processed_ids_file = "processed_ids_moda.json"
    processed_ids = load_processed_ids(processed_ids_file)
    new_processed_ids = set()

    translated_root = ET.Element(root.tag)
    products = root.findall(".//Urun")

    for i, product in enumerate(products, start=1):
        product_id = get_product_id(product)
        if product_id is None:
            print(f"Skipping product {i} with no valid ID.")
            continue

        if product_id in processed_ids:
            print(f"Skipping already processed product {i}")
            translated_root.append(copy.deepcopy(product))
            continue

        print(f"Translating product {i}...")

        product_copy = copy.deepcopy(product)

        # Translate fields
        for tag in ["UrunAdi", "Aciklama", "Marka", "Kategori"]:
            field = product_copy.find(tag)
            if field is not None and field.text:
                try:
                    field.text = translator.translate(field.text)
                except Exception as e:
                    print(f"{tag} translation error: {e}")

        fiyat = product_copy.find("SatisFiyati")
        if fiyat is not None and fiyat.text:
            try:
                lira = float(fiyat.text.replace(",", "."))
                usd = math.ceil(lira * rate * 100) / 100.0
                fiyat.text = f"{usd:.2f}"
            except Exception as e:
                print(f"SatisFiyati conversion error: {e}")

        secenekler = product_copy.find("UrunSecenek")
        if secenekler is not None:
            for secenek in secenekler.findall("Secenek"):
                ad = secenek.find("Ad")
                deger = secenek.find("Deger")
                if ad is not None and ad.text:
                    try:
                        ad.text = translator.translate(ad.text)
                    except Exception as e:
                        print(f"Secenek Ad translation error: {e}")
                if deger is not None and deger.text:
                    try:
                        deger.text = translator.translate(deger.text)
                    except Exception as e:
                        print(f"Secenek Deger translation error: {e}")

        translated_root.append(product_copy)
        new_processed_ids.add(product_id)

    all_processed_ids = processed_ids.union(new_processed_ids)
    save_processed_ids(all_processed_ids, processed_ids_file)

    rough_string = ET.tostring(translated_root, encoding="utf-8")
    reparsed = xml.dom.minidom.parseString(rough_string)
    with open("translatedsample_moda.xml", "w", encoding="utf-8") as f:
        f.write(reparsed.toprettyxml(indent="  "))

    print("Moda Yakamoz script completed.")

    # Auto-commit changes
    try:
        subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions"], check=True)
        subprocess.run(["git", "add", "translatedsample_moda.xml", "original_moda.xml", "processed_ids_moda.json"], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update translated Moda Yakamoz XML"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Changes committed and pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git commit/push failed: {e}")

if __name__ == "__main__":
    run_script_moda_yakamoz()
