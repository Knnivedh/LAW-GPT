import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_file(url, filename, verify=True):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }
    try:
        print(f"Downloading {url} (Verify={verify})...")
        response = requests.get(url, headers=headers, stream=True, timeout=30, verify=verify)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved to {filename}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

# Consumer Protection E-Commerce Rules (Retry with verify=False)
download_file("https://consumeraffairs.nic.in/sites/default/files/webform/G.S.R.%20458%20%28E%29.pdf", "DATA/Statutes/E_Commerce_Rules_2020.pdf", verify=False)
