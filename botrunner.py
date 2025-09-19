import requests
import sys

# loll this script is for because updater no work so i uhh used if it works never touch it again logic

URL = "https://raw.githubusercontent.com/LizardRush/Forsaken-Python-Bot/refs/heads/main/bot.py"

try:
    r = requests.get(URL, timeout=10)
    if r.status_code == 200:
        code = r.text
        print("✅ Running latest bot version...")
        exec(code, globals())
    else:
        print("❌ Failed to fetch bot script:", r.status_code)
except Exception as e:
    print("❌ Error fetching bot script:", e)
    sys.exit(1)
