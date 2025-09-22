import requests
import sys
import subprocess
import json

BOT_URL = "https://raw.githubusercontent.com/LizardRush/Forsaken-Python-Bot/refs/heads/main/bot.py"
PKG_URL = "https://raw.githubusercontent.com/LizardRush/Forsaken-Python-Bot/refs/heads/main/packages.json"

def install_requirements():
    try:
        r = requests.get(PKG_URL, timeout=10)
        if r.status_code == 200:
            packages = json.loads(r.text)
            if isinstance(packages, list):
                for pkg in packages:
                    print(f"📦 Installing {pkg}...")
                    subprocess.run([sys.executable, "-m", "pip", "install", pkg], check=False)
            else:
                print("⚠️ packages.json is not a list")
        else:
            print("⚠️ No packages.json found (status:", r.status_code, ")")
    except Exception as e:
        print("⚠️ Failed to install requirements:", e)

def run_bot():
    try:
        r = requests.get(BOT_URL, timeout=10)
        if r.status_code == 200:
            code = r.text
            print("✅ Running latest bot version...")
            exec(code, globals())
        else:
            print("❌ Failed to fetch bot script:", r.status_code)
    except Exception as e:
        print("❌ Error fetching bot script:", e)
        sys.exit(1)

if __name__ == "__main__":
    install_requirements()
    run_bot()
