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
import traceback
import sys

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

start_money = None
end_money = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "disconnected_logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

MINOR_EXCEPTIONS = (
    UnicodeDecodeError,
    ValueError,
    FileNotFoundError,
    TimeoutError,
    ConnectionError,
    BrokenPipeError,
)

SERIOUS_EXCEPTIONS = (
    MemoryError,
    SystemExit,
    KeyboardInterrupt,
)

def is_minor_exception(exc: Exception) -> bool:
    if isinstance(exc, MINOR_EXCEPTIONS):
        return True
    if isinstance(exc, SERIOUS_EXCEPTIONS):
        return False
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    if "tesseract" in name or "pytesseract" in name or "image" in name and "corrupt" in msg:
        return True
    return False

def handle_exception(e: Exception, context: str = ""):
    tb = traceback.format_exc()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Exception in {context}: {repr(e)}\n{tb}\n"
    try:
        with open(os.path.join(LOG_DIR, "error.log"), "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        print("Failed to write error log.", file=sys.stderr)
        print(log_entry, file=sys.stderr)
    if is_minor_exception(e):
        print(f"⚠️ Minor error in {context}: {e} (logged, continuing)")
    else:
        print(f"❌ Serious error in {context}: {e} (raising)")
        raise

def launch_roblox(place_id=None):
    try:
        if OS_NAME == "darwin":
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
    except Exception as e:
        handle_exception(e, "launch_roblox")

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
        handle_exception(e, "focus_roblox")
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
        handle_exception(e, "quit_roblox")

def fullscreen_roblox():
    try:
        pass
    except Exception as e:
        handle_exception(e, "fullscreen_roblox")

def safe_image_to_string(img, config="--psm 7 digits"):
    try:
        return pytesseract.image_to_string(img, config=config)
    except Exception as e:
        if is_minor_exception(e):
            handle_exception(e, "safe_image_to_string")
            return ""
        else:
            handle_exception(e, "safe_image_to_string")

def safe_image_to_data(img):
    try:
        return pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except Exception as e:
        if is_minor_exception(e):
            handle_exception(e, "safe_image_to_data")
            return {"text": []}
        else:
            handle_exception(e, "safe_image_to_data")

def read_money_box():
    try:
        region = (41, 149, 171, 176)
        img = ImageGrab.grab(bbox=region)
        gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        text = safe_image_to_string(thresh, config="--psm 7 digits")
        text = "".join([c for c in text if c.isdigit()])
        try:
            return int(text) if text else None
        except ValueError as ve:
            handle_exception(ve, "parse_money_value")
            return None
    except Exception as e:
        if is_minor_exception(e):
            handle_exception(e, "read_money_box")
            return None
        else:
            handle_exception(e, "read_money_box")

def check_disconnected():
    try:
        img = ImageGrab.grab()
        img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        data = safe_image_to_data(thresh)

        found = False
        for i, word in enumerate(data.get("text", [])):
            try:
                if not word:
                    continue
                if "disconnected" in word.lower():
                    found = True
                    (x, y, w, h) = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
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
                        handle_exception(e, "saving_disconnected_screenshot")
                    break
            except Exception as inner_e:
                if is_minor_exception(inner_e):
                    handle_exception(inner_e, "check_disconnected_inner")
                    continue
                else:
                    handle_exception(inner_e, "check_disconnected_inner")
        return found
    except Exception as e:
        if is_minor_exception(e):
            handle_exception(e, "check_disconnected")
            return False
        else:
            handle_exception(e, "check_disconnected")

def reconnect_if_disconnected():
    time.sleep(1)
    while True:
        try:
            if check_disconnected():
                launch_roblox(place_id="18687417158")
                time.sleep(15)
                print("✅ Reconnected to Roblox.")
            time.sleep(1)
        except Exception as e:
            if is_minor_exception(e):
                handle_exception(e, "reconnect_if_disconnected_loop")
                time.sleep(2)
                continue
            else:
                handle_exception(e, "reconnect_if_disconnected_loop")

def press_keys(keys, hold_time=3):
    try:
        for k in keys:
            keyboard.press(k)
        time.sleep(hold_time)
        for k in keys:
            keyboard.release(k)
    except Exception as e:
        if is_minor_exception(e):
            handle_exception(e, "press_keys")
        else:
            handle_exception(e, "press_keys")

def spin_sequence():
    def hold_extra(key):
        try:
            time.sleep(0.2)
            keyboard.release(key)
        except Exception as e:
            if is_minor_exception(e):
                handle_exception(e, "spin_sequence_hold_extra")
            else:
                handle_exception(e, "spin_sequence_hold_extra")

    try:
        for k in ["w", "a", "s", "d"]:
            keyboard.press(k)
            time.sleep(0.2)
            threading.Thread(target=hold_extra, args=(k,), daemon=True).start()
    except Exception as e:
        if is_minor_exception(e):
            handle_exception(e, "spin_sequence")
        else:
            handle_exception(e, "spin_sequence")

def occasional_f():
    try:
        if random.random() < 0.1:
            keyboard.press("f")
            time.sleep(1)
            keyboard.release("f")
    except Exception as e:
        if is_minor_exception(e):
            handle_exception(e, "occasional_f")
        else:
            handle_exception(e, "occasional_f")

def movement_loop():
    global running, last_move, paused, start_money
    try:
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
            time.sleep(0.2)
            pyautogui.click(138, 31)
            time.sleep(0.2)
            start_money = read_money_box()
            print(f"💰 Starting money: {start_money}")
        except Exception as e:
            if is_minor_exception(e):
                handle_exception(e, "movement_loop_open_chat_or_read_money")
            else:
                handle_exception(e, "movement_loop_open_chat_or_read_money")

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
            except Exception as loop_e:
                if is_minor_exception(loop_e):
                    handle_exception(loop_e, "movement_loop_iteration")
                    time.sleep(0.5)
                    continue
                else:
                    handle_exception(loop_e, "movement_loop_iteration")
    except Exception as e:
        if is_minor_exception(e):
            handle_exception(e, "movement_loop_top")
        else:
            handle_exception(e, "movement_loop_top")

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
        if is_minor_exception(e):
            handle_exception(e, "on_press")
        else:
            handle_exception(e, "on_press")

if __name__ == "__main__":
    try:
        coin_flip = input("Coin Flip? (y/n): ").lower()
        if coin_flip == "n":
            try:
                ability_count = int(input("How many abilities? (1-4): "))
                ability_map = ["q", "e", "r", "t"]
                abilities = ability_map[:max(0, min(4, ability_count))]
            except Exception as e:
                if is_minor_exception(e):
                    handle_exception(e, "ability_input")
                    abilities = ["q"]
                else:
                    handle_exception(e, "ability_input")

        threading.Thread(target=movement_loop, daemon=True).start()
        threading.Thread(target=reconnect_if_disconnected, daemon=True).start()

        with kb.Listener(on_press=on_press) as listener:
            listener.join()
    except Exception as e:
        if is_minor_exception(e):
            handle_exception(e, "__main__")
        else:
            handle_exception(e, "__main__")
