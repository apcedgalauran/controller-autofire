# Controller Autofire

Hold the fire button on your controller and it registers rapid presses, as if you were mashing it. This turns semi-automatic guns into fully automatic ones in offline games. It works with any game that supports an Xbox controller, such as The Last of Us Part II and Black Ops 3 (Campaign/Zombies).

It reads your real controller and mirrors it to a virtual Xbox 360 controller (via ViGEmBus). While a fire button is held, the virtual controller pulses it on and off at a set rate. Everything else passes straight through, including rumble.

> **Offline / single-player only.** Games with online anti-cheat can flag virtual controllers and macros.

## Setup (once)

1. Put your controller in **PC/Xbox (XInput) mode**.
2. Run **`1 - Setup (run once).bat`**. It installs Python packages, ViGEmBus and HidHide.
3. Restart your PC.
4. Open **HidHide Configuration Client**:
   - **Applications**: add your `python.exe` (run `where python` to find it).
   - **Devices**: tick your controller, then tick **Enable device hiding**.

   This hides the real controller from games so they only see the virtual one. Without it, the game sees the held trigger and ignores the pulses.

## Use

1. Run **`2 - Start Autofire.bat`**. It installs any missing packages and opens the app.
2. Wait for **Controller connected**, then launch your game.
3. Hold **RT** to auto-fire. Close the window to stop.

The app lets you:
- turn auto-fire on or off
- set the fire speed (1 to 60 shots per second): type a number and press Enter, or use − / +
- choose which buttons auto-fire (RT, RB, LT)

Settings are saved in `autofire_settings.json`.

### Controller shortcuts

Hold **View**, the small button left of the home/logo button, then tap the D-pad:

| D-pad | Action |
|-------|--------|
| Up    | Auto-fire on/off (turn it off for bows or charge weapons) |
| Right | Faster |
| Left  | Slower |
| Down  | RB auto-fire on/off |

## Tips

- If some shots don't register, lower the speed. Games read input once per frame, so at 60 FPS anything above about 30 shots/sec can drop presses, and many games also cap fire rate at the gun's animation speed.
- For Steam games, set **Steam Input** to **Disable** in the game's Properties → Controller.
- Close DS4Windows or similar tools while this is running.
- To use your controller normally again, untick **Enable device hiding** in HidHide.

## Files

| File | What it is |
|------|------------|
| `autofire_gui.py` | The app (window version) |
| `autofire.py` | Terminal-only version |
| `1 - Setup (run once).bat` | One-time installer |
| `2 - Start Autofire.bat` | Launcher |
