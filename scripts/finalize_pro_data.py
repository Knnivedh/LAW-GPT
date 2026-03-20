import requests
import pdfplumber
import urllib3
import os
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_DIR = Path("DATA/Statutes")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def download_file(url, filename, verify=True):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }
    try:
        print(f"Downloading {url}...")
        response = requests.get(url, headers=headers, stream=True, timeout=30, verify=verify)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved to {filename}")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def extract_text_from_pdf(pdf_path, txt_path):
    try:
        print(f"Extracting text from {pdf_path}...")
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved text to {txt_path} ({len(text)} chars)")
        return True
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}")
        return False

# 1. Download E-Commerce Rules PDF
ecommerce_pdf = OUTPUT_DIR / "E_Commerce_Rules_2020.pdf"
download_file("https://consumeraffairs.nic.in/sites/default/files/webform/G.S.R.%20458%20%28E%29.pdf", ecommerce_pdf, verify=False)

# 2. Extract Competition Act Text
comp_pdf = OUTPUT_DIR / "Competition_Act_2002.pdf"
comp_txt = OUTPUT_DIR / "Competition_Act_2002.txt"
if comp_pdf.exists():
    extract_text_from_pdf(comp_pdf, comp_txt)

# 3. Extract E-Commerce Rules Text
ecommerce_txt = OUTPUT_DIR / "E_Commerce_Rules_2020.txt"
if ecommerce_pdf.exists():
    extract_text_from_pdf(ecommerce_pdf, ecommerce_txt)

# 4. Final Verification
acts = ["Indian_Contract_Act_1872", "Sale_of_Goods_Act_1930", "Specific_Relief_Act_1963", 
        "Negotiable_Instruments_Act_1881", "Competition_Act_2002", "E_Commerce_Rules_2020"]
print("\nFinal Data Check:")
for act in acts:
    p = OUTPUT_DIR / f"{act}.txt"
    size = p.stat().st_size if p.exists() else 0
    print(f" - {act}: {'[OK]' if size > 1000 else '[MISSING/FAIL]'} ({size} bytes)")
