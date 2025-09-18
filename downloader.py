import os
import sys
import subprocess
import urllib.request

# === List of required packages ===
REQUIRED_LIBS = [
    "pyautogui",
    "pynput",
    "requests",
    "pytesseract",
    "Pillow",
    "opencv-python",
    "numpy"
]

BOT_URL = "https://raw.githubusercontent.com/LizardRush/Forsaken-Python-Bot/refs/heads/main/bot.py"
BOT_FILENAME = "bot.py"

def install_libs():
    print("[*] Installing required libraries...")
    for lib in REQUIRED_LIBS:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", lib])
            print(f"[+] Installed {lib}")
        except subprocess.CalledProcessError:
            print(f"[!] Failed to install {lib}")

def download_bot():
    print("[*] Downloading bot script...")
    try:
        urllib.request.urlretrieve(BOT_URL, BOT_FILENAME)
        print(f"[+] Bot saved as {BOT_FILENAME}")
    except Exception as e:
        print(f"[!] Failed to download bot: {e}")

def self_destruct():
    script_path = os.path.abspath(__file__)
    print("[*] Cleaning up installer...")
    if os.path.exists(script_path):
        os.remove(script_path)
        print("[+] Installer deleted itself")

if __name__ == "__main__":
    install_libs()
    download_bot()
    print("[*] Done! Run the bot with:")
    print(f"    python {BOT_FILENAME}")
    self_destruct()
