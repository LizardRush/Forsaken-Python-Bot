import platform
import random
import time
import threading
import subprocess
import pyautogui
import os
import sys
import io
import datetime
from pynput import keyboard as kb
from pynput.keyboard import Controller, Key
import pytesseract
from PIL import ImageGrab
import cv2
import numpy as np

# === GLOBAL UTF-8 SAFE IO ===
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
os.environ["PYTHONIOENCODING"] = "utf-8"

keyboard = Controller()
OS_NAME = platform.system().lower()

movement_keys = [["w"], ["a"], ["s"], ["d"],
                 ["w", "a"], ["w", "d"], ["a", "s"], ["d", "s"]]
reverse_map = {"w": "s", "s": "w", "a": "d", "d": "a"}

paused = False
running = True
last_move = None
coin_flip = None
abilities = []

# === Money tracking ===
start_money = None
end_money = None

# === Disconnected log setup ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "disconnected_logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# === OS-specific helpers ===
def launch_roblox(place_id=None):
    if OS_NAME == "darwin":  # macOS
        cmd = f"open roblox://placeId={place_id}" if place_id else "open -a RobloxPlayer"
    elif OS_NAME == "windows":
        cmd = f'start roblox-player:1+launchmode:play+gameinfo:&placeId={place_id}' if place_id else "start RobloxPlayerBeta.exe"
    else:
        cmd = f"wine RobloxPlayerBeta.exe -play -placeId {place_id}" if place_id else "wine RobloxPlayerBeta.exe"
    os.system(cmd)

def focus_roblox():
    try:
        if OS_NAME == "darwin":
            script = '''
            tell application "System Events"
                set frontmost of process "RobloxPlayer" to true
            end tell
            '''
            subprocess.run(["osascript", "-e", script], check=True)
        elif OS_NAME == "windows":
            os.system("nircmd win activate ititle Roblox")
        else:
            os.system("xdotool search --onlyvisible --class Roblox windowactivate")
        time.sleep(0.5)
        return True
    except Exception as e:
        print("Could not focus Roblox:", e)
        return False

def quit_roblox():
    try:
        if OS_NAME == "darwin":
            focus_roblox()
            time.sleep(0.5)
            keyboard.press(Key.cmd)
            keyboard.press("q")
            time.sleep(0.2)
            keyboard.release(Key.cmd)
            keyboard.release("q")
        elif OS_NAME == "windows":
            os.system("taskkill /im RobloxPlayerBeta.exe /f >nul 2>&1")
        else:
            os.system("pkill -f RobloxPlayerBeta.exe")
    except Exception as e:
        print("Error quitting Roblox:", e)

def fullscreen_roblox():
    pass  # left empty — platform dependent

# === Safe Tesseract Call ===
def safe_tesseract_image_to_data(img, **kwargs):
    try:
        if isinstance(img, np.ndarray):
            success, buf = cv2.imencode(".png", img)
            if not success:
                print("⚠️ Failed to encode image to PNG.")
                return {"text": []}
            img_bytes = buf.tobytes()
        else:
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

        return pytesseract.image_to_data(img_bytes, output_type=pytesseract.Output.DICT, **kwargs)
    except pytesseract.TesseractError as e:
        print("⚠️ Tesseract internal error:", e)
        return {"text": []}
    except UnicodeDecodeError:
        print("⚠️ UnicodeDecodeError inside Tesseract. Skipping frame.")
        return {"text": []}
    except Exception as e:
        print("⚠️ OCR exception:", e)
        return {"text": []}

# === Money OCR Helper ===
def read_money_box():
    try:
        region = (41, 149, 171, 176)
        img = ImageGrab.grab(bbox=region)
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        success, buf = cv2.imencode(".png", thresh)
        if not success:
            return None
        img_bytes = buf.tobytes()
        text = pytesseract.image_to_string(img_bytes, config="--psm 7 digits")
        text = "".join([c for c in text if c.isdigit()])
        return int(text) if text else None
    except UnicodeDecodeError:
        print("⚠️ Money OCR Unicode error. Skipping value read.")
        return None
    except Exception as e:
        print("⚠️ Failed to read money box:", e)
        return None

# === Disconnected Detection ===
def check_disconnected():
    try:
        img = ImageGrab.grab()
        img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        data = safe_tesseract_image_to_data(thresh)
        for i, word in enumerate(data.get("text", [])):
            if "disconnected" in word.lower():
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                x, y, w, h = max(0, x - 10), max(0, y - 10), w + 20, h + 20
                cv2.rectangle(img_bgr, (x, y), (x + w, y + h), (0, 0, 255), 3)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(img_bgr, timestamp, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 0, 255), 2, cv2.LINE_AA)
                filename = os.path.join(LOG_DIR, f"disconnected_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                cv2.imwrite(filename, img_bgr)
                print(f"⚠️ Disconnected detected! Logged to {filename}")
                return True
        return False
    except Exception as e:
        print("⚠️ check_disconnected failed:", e)
        return False

def reconnect_if_disconnected():
    time.sleep(1)
    while running:
        if check_disconnected():
            print("🔁 Reconnecting to Roblox...")
            launch_roblox(place_id="18687417158")
            time.sleep(15)
            print("✅ Reconnected to Roblox.")
        time.sleep(1)

# === Movement & actions ===
def press_keys(keys, hold_time=3):
    try:
        for k in keys:
            keyboard.press(k)
        time.sleep(hold_time)
        for k in keys:
            keyboard.release(k)
    except Exception as e:
        print("⚠️ press_keys error:", e)

def spin_sequence():
    def hold_extra(key):
        time.sleep(0.2)
        keyboard.release(key)
    for k in ["w", "a", "s", "d"]:
        keyboard.press(k)
        time.sleep(0.2)
        threading.Thread(target=hold_extra, args=(k,), daemon=True).start()

def occasional_f():
    try:
        if random.random() < 0.1:
            keyboard.press("f")
            time.sleep(1)
            keyboard.release("f")
    except Exception as e:
        print("⚠️ occasional_f error:", e)

# === Main Loop ===
def movement_loop():
    global running, last_move, paused, start_money
    paused = True
    launch_roblox(place_id="18687417158")
    time.sleep(20)
    fullscreen_roblox()
    print("Focusing Roblox...")
    if not focus_roblox():
        print("Roblox not found.")
        running = False
        return
    fullscreen_roblox()

    try:
        keyboard.press("/")
        time.sleep(0.2)
        keyboard.release("/")
        time.sleep(1)
        pyautogui.click(138, 31)
        time.sleep(1)
        start_money = read_money_box()
        print(f"💰 Starting money: {start_money}")
    except Exception as e:
        print("⚠️ Failed initial money read:", e)

    print("Starting bot...")
    paused = False

    while running:
        try:
            if paused:
                time.sleep(0.1)
                continue
            focus_roblox()
            if coin_flip == "y":
                keyboard.press("q")
                time.sleep(0.1)
                keyboard.release("q")
            else:
                time.sleep(random.uniform(1.5, 3.0))
                if random.random() < 0.05:
                    spin_sequence()
                occasional_f()

                if abilities and random.random() < 0.25:
                    ability = random.choice(abilities)
                    keyboard.press(ability)
                    time.sleep(0.2)
                    keyboard.release(ability)
                    time.sleep(5)
                else:
                    choices = [k for k in movement_keys if k != last_move]
                    keys = random.choice(choices) if choices else random.choice(movement_keys)
                    sprinting = random.random() < 0.5
                    if sprinting:
                        keyboard.press(Key.shift)
                    press_keys(keys, hold_time=random.uniform(2, 4))
                    if sprinting:
                        keyboard.release(Key.shift)
                    last_move = keys
        except Exception as e:
            print("⚠️ Main loop minor error:", e)
            continue

def on_press(key):
    global running, end_money
    try:
        if key == kb.Key.f9:
            print("F9 pressed. Stopping bot.")
            end_money = read_money_box()
            print(f"💰 Ending money: {end_money}")
            if start_money is not None and end_money is not None:
                print(f"📈 Money gained: {end_money - start_money}")
            quit_roblox()
            running = False
            return False
    except Exception as e:
        print("⚠️ on_press error:", e)

# === Entry Point ===
if __name__ == "__main__":
    try:
        coin_flip = input("Coin Flip? (y/n): ").lower()
        if coin_flip == "n":
            ability_count = int(input("How many abilities? (1-4): "))
            ability_map = ["q", "e", "r", "t"]
            abilities = ability_map[:ability_count]

        threading.Thread(target=movement_loop, daemon=True).start()
        threading.Thread(target=reconnect_if_disconnected, daemon=True).start()

        with kb.Listener(on_press=on_press) as listener:
            listener.join()
    except Exception as e:
        print("💥 Fatal Error:", e)
        quit_roblox()
        running = False
