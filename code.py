# SPDX-FileCopyrightText: 2021 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
A macro/hotkey program for Adafruit MACROPAD with an integrated Dragon Drop game.
"""

# Import required libraries
import os
import time
import displayio
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_macropad import MacroPad
import dragondrop_game  # Import the Dragon Drop game module

# CONFIGURABLES ------------------------
MACRO_FOLDER = '/macros'
GAME_KEY = 11  # Key to press to start the Dragon Drop game (Key 11 is the last key)

# CLASSES AND FUNCTIONS ----------------
class App:
    """Class representing a host-side application, for which we have a set of macro sequences."""
    def __init__(self, appdata):
        self.name = appdata['name']
        self.macros = appdata['macros']

    def switch(self):
        """Activate application settings; update OLED labels and LED colors."""
        group[13].text = self.name  # Application name
        if self.name:
            rect.fill = 0xFFFFFF
        else:  # empty app name indicates blank screen
            rect.fill = 0x000000
        for i in range(12):
            if i < len(self.macros):  # Key in use, set label + LED color
                macropad.pixels[i] = self.macros[i][0]
                group[i].text = self.macros[i][1]
            else:  # Key not in use, no label or LED
                macropad.pixels[i] = 0
                group[i].text = ''
        macropad.keyboard.release_all()
        macropad.consumer_control.release()
        macropad.mouse.release_all()
        macropad.stop_tone()
        macropad.pixels.show()
        macropad.display.refresh()

# INITIALIZATION -----------------------
macropad = MacroPad()
macropad.display.auto_refresh = False
macropad.pixels.auto_write = False

# Set up displayio group with all the labels
group = displayio.Group()
for key_index in range(12):
    x = key_index % 3
    y = key_index // 3
    group.append(label.Label(terminalio.FONT, text='', color=0xFFFFFF,
                             anchored_position=((macropad.display.width - 1) * x / 2,
                                                macropad.display.height - 1 -
                                                (3 - y) * 12),
                             anchor_point=(x / 2, 1.0)))
rect = Rect(0, 0, macropad.display.width, 13, fill=0xFFFFFF)
group.append(rect)
group.append(label.Label(terminalio.FONT, text='', color=0x000000,
                         anchored_position=(macropad.display.width//2, 0),
                         anchor_point=(0.5, 0.0)))

# Macro menu group for the macro menu
macro_menu_group = group  # Assign the macro menu to a variable

macropad.display.root_group = group

# Load all the macro key setups from .py files in MACRO_FOLDER
apps = []
files = os.listdir(MACRO_FOLDER)
files.sort()
for filename in files:
    if filename.endswith('.py') and not filename.startswith('._'):
        try:
            module = __import__(MACRO_FOLDER + '/' + filename[:-3])
            apps.append(App(module.app))
        except (SyntaxError, ImportError, AttributeError, KeyError, NameError,
                IndexError, TypeError) as err:
            print(f"ERROR in {filename}: {err}")

if not apps:
    group[13].text = 'NO MACRO FILES FOUND'
    macropad.display.refresh()
    while True:
        pass

# Add game mode as an App
last_position = None
app_index = 0
apps.append(App({'name': 'Dragon Drop', 'macros': []}))  # Add "Dragon Drop" as an app
apps[app_index].switch()

# MAIN LOOP ----------------------------
while True:
    # Read encoder position. If it's changed, switch apps.
    position = macropad.encoder
    if position != last_position:
        app_index = position % len(apps)  # Handle wrap-around between apps
        apps[app_index].switch()  # Switch to the selected app
        last_position = position

    # Handle key events
    event = macropad.keys.events.get()
    if event:
        if app_index == len(apps) - 1:  # "Dragon Drop" app is selected
            if event.pressed and event.key_number == GAME_KEY:
                print("Starting Dragon Drop game...")
                result = dragondrop_game.run_game(macropad)  # Pass the macropad instance
                if result == "game_ended":
                    print("Exiting Dragon Drop game...")
                    # Reset to macro menu display group
                    macropad.display.rotation = 0  # Reset display rotation to default
                    macropad.display.root_group = macro_menu_group
                    macropad.display.refresh()
            elif event.pressed:
                # Any other keypress while in game selection skips the game
                print(f"Key {event.key_number} pressed. Skipping game.")
        else:
            # Handle key events for macro apps
            if event.key_number >= len(apps[app_index].macros):
                continue
            key_number = event.key_number
            pressed = event.pressed

            sequence = apps[app_index].macros[key_number][2]
            if pressed:
                for item in sequence:
                    if isinstance(item, int):
                        if item >= 0:
                            macropad.keyboard.press(item)
                        else:
                            macropad.keyboard.release(-item)
                    elif isinstance(item, float):
                        time.sleep(item)
                    elif isinstance(item, str):
                        macropad.keyboard_layout.write(item)
                    elif isinstance(item, list):
                        for code in item:
                            if isinstance(code, int):
                                macropad.consumer_control.release()
                                macropad.consumer_control.press(code)
                            if isinstance(code, float):
                                time.sleep(code)
                    elif isinstance(item, dict):
                        if 'buttons' in item:
                            if item['buttons'] >= 0:
                                macropad.mouse.press(item['buttons'])
                            else:
                                macropad.mouse.release(-item['buttons'])
                        macropad.mouse.move(item.get('x', 0), item.get('y', 0), item.get('wheel', 0))
                        if 'tone' in item:
                            if item['tone'] > 0:
                                macropad.stop_tone()
                                macropad.start_tone(item['tone'])
                            else:
                                macropad.stop_tone()
                        elif 'play' in item:
                            macropad.play_file(item['play'])
            else:
                for item in sequence:
                    if isinstance(item, int):
                        if item >= 0:
                            macropad.keyboard.release(item)
                    elif isinstance(item, dict) and 'buttons' in item:
                        if item['buttons'] >= 0:
                            macropad.mouse.release(item['buttons'])
                macropad.consumer_control.release()
