import platform
import random
import time
import threading
import subprocess
import pyautogui
import os
import datetime
from pynput import keyboard as kb
from pynput.keyboard import Controller, Key
import pytesseract
from PIL import ImageGrab
import cv2
import numpy as np

keyboard = Controller()
OS_NAME = platform.system().lower()  # "darwin", "windows", "linux"

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
        if place_id:
            os.system(f"open roblox://placeId={place_id}")
        else:
            os.system("open -a RobloxPlayer")
    elif OS_NAME == "windows":
        if place_id:
            os.system(f"start roblox-player:1+launchmode:play+gameinfo:&placeId={place_id}")
        else:
            os.system("start RobloxPlayerBeta.exe")
    elif OS_NAME == "linux":
        if place_id:
            os.system(f"wine RobloxPlayerBeta.exe -play -placeId {place_id}")
        else:
            os.system("wine RobloxPlayerBeta.exe")

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
        elif OS_NAME == "linux":
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
            os.system("taskkill /im RobloxPlayerBeta.exe /f")
        elif OS_NAME == "linux":
            os.system("pkill -f RobloxPlayerBeta.exe")
    except Exception as e:
        print("Error quitting Roblox:", e)

def fullscreen_roblox():
    pass  # Left blank – too dependent on platform/GUI libs

# === Money OCR Helper ===
def read_money_box():
    """Reads money value from predefined region and returns as int (if found)."""
    # Region: (x1, y1, x2, y2)
    region = (41, 149, 171, 176)  # adjusted to integer box
    img = ImageGrab.grab(bbox=region)
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

    text = pytesseract.image_to_string(thresh, config="--psm 7 digits")
    text = "".join([c for c in text if c.isdigit()])
    try:
        return int(text)
    except ValueError:
        return None

# === Disconnected Detection ===
def check_disconnected():
    img = ImageGrab.grab()
    img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)

    found = False
    for i, word in enumerate(data["text"]):
        if "disconnected" in word.lower():
            found = True
            (x, y, w, h) = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])

            # Increase bounding box size by 10 pixels in all directions
            x = max(0, x - 10)
            y = max(0, y - 10)
            w += 20
            h += 20

            cv2.rectangle(img_bgr, (x, y), (x + w, y + h), (0, 0, 255), 3)

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(img_bgr, timestamp, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 255), 2, cv2.LINE_AA)

            filename = os.path.join(LOG_DIR, f"disconnected_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            try:
                cv2.imwrite(filename, img_bgr)
                print(f"⚠️ Disconnected detected! Logged to {filename}")
            except Exception as e:
                print("❌ Failed to save screenshot:", e)
            break
    return found

def reconnect_if_disconnected():
    time.sleep(1)
    while True:
        if check_disconnected():
            launch_roblox(place_id="18687417158")
            time.sleep(15)
            print("✅ Reconnected to Roblox.")
        time.sleep(1)

# === Movement & actions ===
def press_keys(keys, hold_time=3):
    for k in keys:
        keyboard.press(k)
    time.sleep(hold_time)
    for k in keys:
        keyboard.release(k)

def spin_sequence():
    def hold_extra(key):
        time.sleep(0.2)
        keyboard.release(key)

    for k in ["w", "a", "s", "d"]:
        keyboard.press(k)
        time.sleep(0.2)
        threading.Thread(target=hold_extra, args=(k,), daemon=True).start()

def occasional_f():
    if random.random() < 0.1:
        keyboard.press("f")
        time.sleep(1)
        keyboard.release("f")

# === Main Loop ===
def movement_loop():
    global running, last_move, paused, start_money
    paused = True
    launch_roblox(place_id="18687417158")
    time.sleep(15)
    fullscreen_roblox()
    print("Focusing Roblox...")
    if not focus_roblox():
        print("Roblox not found.")
        running = False
        return
    fullscreen_roblox()

    # === Added Step: Open chat, click, read money ===
    keyboard.press("/")
    time.sleep(0.2)
    keyboard.release("/")
    pyautogui.click(138, 31)
    time.sleep(0.2)
    start_money = read_money_box()
    print(f"💰 Starting money: {start_money}")

    print("Starting bot...")
    paused = False

    while running:
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

def on_press(key):
    global running, end_money
    if key == kb.Key.f9:
        print("F9 pressed. Stopping bot.")
        end_money = read_money_box()
        print(f"💰 Ending money: {end_money}")
        if start_money is not None and end_money is not None:
            print(f"📈 Money gained: {end_money - start_money}")
        quit_roblox()
        running = False
        return False

# === Entry Point ===
if __name__ == "__main__":
    coin_flip = input("Coin Flip? (y/n): ").lower()
    if coin_flip == "n":
        ability_count = int(input("How many abilities? (1-4): "))
        ability_map = ["q", "e", "r", "t"]
        abilities = ability_map[:ability_count]

    threading.Thread(target=movement_loop, daemon=True).start()
    threading.Thread(target=reconnect_if_disconnected, daemon=True).start()

    with kb.Listener(on_press=on_press) as listener:
        listener.join()
