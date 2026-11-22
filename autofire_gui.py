"""
Controller Autofire - window version.
Hold the fire button on your controller and it registers rapid presses,
like you're mashing it. For offline / single-player games.
"""

import ctypes
import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(HERE, "autofire_settings.json")

# ---------- colours ----------
BG = "#16171d"
CARD = "#20222b"
CARD_LINE = "#2c2f3a"
TEXT = "#eceef4"
MUTED = "#9a9fb0"
ACCENT = "#e8453c"      # red, like the GameSir app
GOOD = "#3ecf73"
WARN = "#f0b429"
OFF = "#3a3d49"

FONT = "Segoe UI"

DEFAULTS = {
    "enabled": True,
    "rate": 12,
    "rt": True,
    "rb": False,
    "lt": False,
}

MIN_RATE, MAX_RATE = 4, 25
DUTY = 0.5
TRIGGER_THRESHOLD = 60
POLL_SECONDS = 0.002

DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT = 0x0001, 0x0002, 0x0004, 0x0008
DPAD_ALL = DPAD_UP | DPAD_DOWN | DPAD_LEFT | DPAD_RIGHT
BACK = 0x0020
RB = 0x0200


def hide_console():
    """Hide the black terminal window behind the app (Windows only)."""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            s.update({k: v for k, v in json.load(f).items() if k in DEFAULTS})
    except Exception:
        pass
    s["rate"] = max(MIN_RATE, min(MAX_RATE, int(s["rate"])))
    return s


def save_settings(s):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2)
    except Exception:
        pass


def beep(freq, ms=70):
    try:
        import winsound
        threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()
    except Exception:
        pass


class Pulser:
    """Turns a held button into fast press/release. First shot is instant."""

    def __init__(self):
        self.start = None

    def output(self, held, now, period):
        if not held:
            self.start = None
            return False
        if self.start is None:
            self.start = now
        return ((now - self.start) % period) < period * DUTY


class Engine(threading.Thread):
    """Reads the real controller, writes a virtual one with pulsed fire buttons."""

    def __init__(self, settings, XInput, vg):
        super().__init__(daemon=True)
        self.s = settings
        self.XInput = XInput
        self.vg = vg
        self.stop_flag = threading.Event()
        self.status = "starting"      # starting | searching | running | disconnected | error
        self.error = ""
        self.firing = False
        self.changed_from_pad = False

    def stop(self):
        self.stop_flag.set()

    def _find_real_pad(self):
        while not self.stop_flag.is_set():
            for slot, connected in enumerate(self.XInput.get_connected()):
                if connected:
                    return slot
            time.sleep(0.4)
        return None

    def run(self):
        X = self.XInput
        self.status = "searching"
        real = self._find_real_pad()   # before creating the virtual pad
        if real is None:
            return

        try:
            pad = self.vg.VX360Gamepad()
        except Exception as e:
            self.status = "error"
            self.error = ("Could not create the virtual controller.\n"
                          "ViGEmBus may not be installed - run the setup file, "
                          f"then restart your PC.\n\nDetails: {e}")
            return

        def rumble(client, target, large_motor, small_motor, led_number, user_data):
            try:
                X.set_vibration(real, large_motor / 255, small_motor / 255)
            except Exception:
                pass

        try:
            pad.register_notification(callback_function=rumble)
        except Exception:
            pass

        rt_p, rb_p, lt_p = Pulser(), Pulser(), Pulser()
        prev = 0
        self.status = "running"

        try:
            while not self.stop_flag.is_set():
                try:
                    g = X.get_state(real).Gamepad
                except X.XInputNotConnectedError:
                    self.status = "disconnected"
                    self.firing = False
                    pad.reset()
                    pad.update()
                    while not self.stop_flag.is_set() and not X.get_connected()[real]:
                        time.sleep(0.4)
                    self.status = "running"
                    continue

                s = self.s
                buttons = g.wButtons
                newly = buttons & ~prev
                prev = buttons

                # View/Back + D-pad shortcuts (D-pad hidden from the game meanwhile)
                if buttons & BACK:
                    if newly & DPAD_UP:
                        s["enabled"] = not s["enabled"]
                        beep(1200 if s["enabled"] else 500)
                        self.changed_from_pad = True
                    if newly & DPAD_RIGHT:
                        s["rate"] = min(MAX_RATE, s["rate"] + 1)
                        beep(900)
                        self.changed_from_pad = True
                    if newly & DPAD_LEFT:
                        s["rate"] = max(MIN_RATE, s["rate"] - 1)
                        beep(700)
                        self.changed_from_pad = True
                    if newly & DPAD_DOWN:
                        s["rb"] = not s["rb"]
                        beep(1000 if s["rb"] else 600)
                        self.changed_from_pad = True
                    buttons &= ~DPAD_ALL

                now = time.perf_counter()
                period = 1.0 / s["rate"]
                rt, lt = g.bRightTrigger, g.bLeftTrigger
                firing = False

                if s["enabled"] and s["rt"] and rt > TRIGGER_THRESHOLD:
                    rt = 255 if rt_p.output(True, now, period) else 0
                    firing = True
                else:
                    rt_p.output(False, now, period)

                if s["enabled"] and s["lt"] and lt > TRIGGER_THRESHOLD:
                    lt = 255 if lt_p.output(True, now, period) else 0
                    firing = True
                else:
                    lt_p.output(False, now, period)

                if s["enabled"] and s["rb"] and (buttons & RB):
                    if not rb_p.output(True, now, period):
                        buttons &= ~RB
                    firing = True
                else:
                    rb_p.output(False, now, period)

                self.firing = firing

                r = pad.report
                r.wButtons = buttons
                r.bLeftTrigger = lt
                r.bRightTrigger = rt
                r.sThumbLX, r.sThumbLY = g.sThumbLX, g.sThumbLY
                r.sThumbRX, r.sThumbRY = g.sThumbRX, g.sThumbRY
                pad.update()

                time.sleep(POLL_SECONDS)
        finally:
            try:
                pad.reset()
                pad.update()
                X.set_vibration(real, 0, 0)
            except Exception:
                pass


# ======================= WINDOW =======================

class Card(tk.Frame):
    def __init__(self, parent, title=None):
        super().__init__(parent, bg=CARD, highlightbackground=CARD_LINE,
                         highlightthickness=1, padx=16, pady=14)
        if title:
            tk.Label(self, text=title.upper(), bg=CARD, fg=MUTED,
                     font=(FONT, 8, "bold")).pack(anchor="w", pady=(0, 8))


class App:
    def __init__(self, root, engine, settings):
        self.root = root
        self.engine = engine
        self.s = settings

        root.title("Controller Autofire")
        root.configure(bg=BG)
        root.resizable(False, False)

        wrap = tk.Frame(root, bg=BG, padx=18, pady=16)
        wrap.pack(fill="both", expand=True)

        # ---- header
        head = tk.Frame(wrap, bg=BG)
        head.pack(fill="x", pady=(0, 12))
        tk.Label(head, text="Controller Autofire", bg=BG, fg=TEXT,
                 font=(FONT, 16, "bold")).pack(side="left")
        self.status_dot = tk.Label(head, text="●", bg=BG, fg=WARN, font=(FONT, 12))
        self.status_dot.pack(side="right")
        self.status_lbl = tk.Label(head, text="Starting…", bg=BG, fg=MUTED,
                                   font=(FONT, 9))
        self.status_lbl.pack(side="right", padx=(0, 4))

        # ---- main switch
        main = Card(wrap)
        main.pack(fill="x", pady=(0, 10))
        self.toggle_btn = tk.Button(main, text="", font=(FONT, 15, "bold"),
                                    relief="flat", bd=0, cursor="hand2",
                                    activeforeground=TEXT, pady=12,
                                    command=self.toggle_enabled)
        self.toggle_btn.pack(fill="x")
        self.fire_lbl = tk.Label(main, text="", bg=CARD, fg=MUTED, font=(FONT, 10))
        self.fire_lbl.pack(pady=(10, 0))

        # ---- speed
        speed = Card(wrap, "Fire speed")
        speed.pack(fill="x", pady=(0, 10))
        row = tk.Frame(speed, bg=CARD)
        row.pack(fill="x")
        btn = dict(font=(FONT, 16, "bold"), relief="flat", bd=0, cursor="hand2",
                   bg=OFF, fg=TEXT, activebackground="#4a4e5c",
                   activeforeground=TEXT, width=3)
        tk.Button(row, text="−", command=lambda: self.change_rate(-1), **btn).pack(side="left")
        self.rate_lbl = tk.Label(row, text="", bg=CARD, fg=TEXT,
                                 font=(FONT, 13, "bold"))
        self.rate_lbl.pack(side="left", expand=True)
        tk.Button(row, text="+", command=lambda: self.change_rate(1), **btn).pack(side="right")
        tk.Label(speed, text="If some shots don't register in a game, press − to slow it down.",
                 bg=CARD, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(8, 0))

        # ---- which buttons
        which = Card(wrap, "Which buttons auto-fire when held")
        which.pack(fill="x", pady=(0, 10))
        self.vars = {}
        for key, label in (("rt", "Right Trigger (RT)  — normal shoot button"),
                           ("rb", "Right Bumper (RB)"),
                           ("lt", "Left Trigger (LT)  — usually aim, keep off")):
            v = tk.BooleanVar(value=self.s[key])
            self.vars[key] = v
            tk.Checkbutton(which, text=label, variable=v, bg=CARD, fg=TEXT,
                           selectcolor=OFF, activebackground=CARD,
                           activeforeground=TEXT, font=(FONT, 10), anchor="w",
                           highlightthickness=0, bd=0,
                           command=lambda k=key: self.on_check(k)).pack(fill="x")

        # ---- controller shortcuts
        sc = Card(wrap, "Change it mid-game with your controller")
        sc.pack(fill="x", pady=(0, 10))
        self.draw_pad(sc)
        tk.Label(sc, text="Hold the VIEW button, then tap the D-pad:",
                 bg=CARD, fg=TEXT, font=(FONT, 10, "bold")).pack(anchor="w", pady=(8, 4))
        for arrow, what in (("▲  Up", "Auto-fire on / off  (turn off for the bow)"),
                            ("▶  Right", "Faster"),
                            ("◀  Left", "Slower"),
                            ("▼  Down", "Bumper (RB) auto-fire on / off")):
            row = tk.Frame(sc, bg=CARD)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=arrow, bg=CARD, fg=ACCENT, width=9, anchor="w",
                     font=(FONT, 10, "bold")).pack(side="left")
            tk.Label(row, text=what, bg=CARD, fg=TEXT, font=(FONT, 10)).pack(side="left")
        tk.Label(sc, text="You'll hear a beep each time.", bg=CARD, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w", pady=(6, 0))

        tk.Label(wrap, text="Keep this window open while you play. Close it to stop.",
                 bg=BG, fg=MUTED, font=(FONT, 9)).pack(pady=(4, 0))

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_static()
        self.tick()

    # simple controller sketch showing where VIEW and the D-pad are
    def draw_pad(self, parent):
        c = tk.Canvas(parent, width=340, height=150, bg=CARD, highlightthickness=0)
        c.pack()
        body = "#d9dbe2"
        c.create_oval(40, 30, 150, 145, fill=body, outline="")
        c.create_oval(190, 30, 300, 145, fill=body, outline="")
        c.create_rectangle(95, 25, 245, 110, fill=body, outline="")
        # left stick
        c.create_oval(78, 48, 112, 82, fill="#9aa0ad", outline=ACCENT, width=3)
        # right stick
        c.create_oval(205, 82, 239, 116, fill="#9aa0ad", outline=ACCENT, width=3)
        # face buttons
        for (x, y, t) in ((262, 46, "Y"), (247, 61, "X"), (277, 61, "B"), (262, 76, "A")):
            c.create_oval(x - 7, y - 7, x + 7, y + 7, fill="white", outline="")
            c.create_text(x, y, text=t, fill=ACCENT, font=(FONT, 7, "bold"))
        # D-pad (highlighted)
        cx, cy = 128, 98
        c.create_rectangle(cx - 6, cy - 18, cx + 6, cy + 18, fill=ACCENT, outline="")
        c.create_rectangle(cx - 18, cy - 6, cx + 18, cy + 6, fill=ACCENT, outline="")
        # G logo
        c.create_oval(160, 38, 180, 58, fill="#b9bdc8", outline="")
        c.create_text(170, 48, text="G", fill="white", font=(FONT, 8, "bold"))
        # VIEW (highlighted) and MENU
        c.create_oval(139, 44, 153, 56, fill=ACCENT, outline="")
        c.create_oval(187, 44, 201, 56, fill="#b9bdc8", outline="")
        # labels
        c.create_line(146, 44, 146, 12, fill=ACCENT, width=2)
        c.create_text(146, 6, text="VIEW (small button left of the G)",
                      fill=TEXT, font=(FONT, 8, "bold"))
        c.create_line(110, 98, 22, 98, fill=ACCENT, width=2)
        c.create_text(22, 86, text="D-pad", fill=TEXT, font=(FONT, 8, "bold"))
        # triggers
        c.create_text(275, 18, text="RT = fire", fill=MUTED, font=(FONT, 8))

    # ---- actions
    def toggle_enabled(self):
        self.s["enabled"] = not self.s["enabled"]
        save_settings(self.s)
        self.refresh_static()

    def change_rate(self, step):
        self.s["rate"] = max(MIN_RATE, min(MAX_RATE, self.s["rate"] + step))
        save_settings(self.s)
        self.refresh_static()

    def on_check(self, key):
        self.s[key] = bool(self.vars[key].get())
        save_settings(self.s)

    def refresh_static(self):
        if self.s["enabled"]:
            self.toggle_btn.configure(text="AUTO-FIRE ON", bg=ACCENT, fg="white",
                                      activebackground="#c9362f")
        else:
            self.toggle_btn.configure(text="AUTO-FIRE OFF", bg=OFF, fg=MUTED,
                                      activebackground="#4a4e5c")
        self.rate_lbl.configure(text=f"{self.s['rate']} shots / sec")

    def tick(self):
        e = self.engine
        if e.status == "error":
            self.status_dot.configure(fg=ACCENT)
            self.status_lbl.configure(text="Error")
            messagebox.showerror("Controller Autofire", e.error)
            self.on_close()
            return
        text, colour = {
            "starting": ("Starting…", WARN),
            "searching": ("Looking for controller… (Xbox/PC mode)", WARN),
            "running": ("Controller connected", GOOD),
            "disconnected": ("Controller disconnected", ACCENT),
        }.get(e.status, ("", MUTED))
        self.status_dot.configure(fg=colour)
        self.status_lbl.configure(text=text)

        if e.changed_from_pad:      # settings changed with the controller
            e.changed_from_pad = False
            for k, v in self.vars.items():
                v.set(self.s[k])
            save_settings(self.s)
            self.refresh_static()

        if not self.s["enabled"]:
            self.fire_lbl.configure(text="Fire buttons work normally", fg=MUTED)
        elif e.firing:
            self.fire_lbl.configure(text="●  FIRING", fg=ACCENT)
        else:
            self.fire_lbl.configure(text="Hold RT in game to auto-fire", fg=MUTED)

        self.root.after(80, self.tick)

    def on_close(self):
        save_settings(self.s)
        self.engine.stop()
        self.engine.join(timeout=1.5)
        self.root.destroy()


def main():
    try:
        import XInput
        import vgamepad as vg
    except Exception as e:
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("Controller Autofire",
                             "Missing parts. Run '2 - Start Autofire.bat' so it can "
                             f"install them.\n\nDetails: {e}")
        return

    hide_console()
    settings = load_settings()
    engine = Engine(settings, XInput, vg)
    engine.start()

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root, engine, settings)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("Controller Autofire", f"Something went wrong:\n\n{err}")
        except Exception:
            pass
