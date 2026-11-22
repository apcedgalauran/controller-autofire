"""
Universal controller auto-fire for Windows (offline / single-player use).

Your real controller is mirrored onto a virtual Xbox 360 controller. While you
hold the fire button, the virtual controller pulses it on/off at a fast rate.

In-game controls (hold BACK / View, then press):
  D-pad Up     auto-fire ON / OFF
  D-pad Right  faster  (+1 shot/sec)
  D-pad Left   slower  (-1 shot/sec)
  D-pad Down   also auto-fire RB

Press Ctrl+C in this window to quit.
"""

import sys
import threading
import time

try:
    import winsound
except ImportError:
    winsound = None

import XInput
import vgamepad as vg

# ======================= SETTINGS =======================
SHOTS_PER_SEC = 12
MIN_RATE, MAX_RATE = 4, 25
DUTY = 0.5
TRIGGER_THRESHOLD = 60
AUTOFIRE_RT = True
AUTOFIRE_RB = False
AUTOFIRE_LT = False
START_ENABLED = True
POLL_SECONDS = 0.002
SOUND = True
# ========================================================

DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT = 0x0001, 0x0002, 0x0004, 0x0008
DPAD_ALL = DPAD_UP | DPAD_DOWN | DPAD_LEFT | DPAD_RIGHT
BACK = 0x0020
RB = 0x0200


def beep(freq, ms=70):
    if SOUND and winsound:
        threading.Thread(target=winsound.Beep, args=(freq, ms), daemon=True).start()


class Pulser:
    def __init__(self):
        self.start = None

    def output(self, held, now, period):
        if not held:
            self.start = None
            return False
        if self.start is None:
            self.start = now
        return ((now - self.start) % period) < period * DUTY


def find_real_pad():
    print("Looking for your controller (make sure it's in Xbox/PC mode)...")
    while True:
        for slot, connected in enumerate(XInput.get_connected()):
            if connected:
                print(f"Found controller in slot {slot}.")
                return slot
        time.sleep(0.5)


def show_status(enabled, rate, rb_auto):
    state = "ON " if enabled else "OFF"
    rb = "ON " if rb_auto else "OFF"
    print(f"\rAuto-fire: {state} | Rate: {rate:>2}/s | RB auto-fire: {rb}   ",
          end="", flush=True)


def main():
    rate = SHOTS_PER_SEC
    enabled = START_ENABLED
    rb_auto = AUTOFIRE_RB

    real = find_real_pad()

    try:
        pad = vg.VX360Gamepad()
    except Exception as e:
        print("\nCould not create the virtual controller. Is ViGEmBus installed?")
        print(f"Details: {e}")
        input("Press Enter to close...")
        sys.exit(1)

    def rumble(client, target, large_motor, small_motor, led_number, user_data):
        try:
            XInput.set_vibration(real, large_motor / 255, small_motor / 255)
        except Exception:
            pass

    pad.register_notification(callback_function=rumble)

    rt_p, rb_p, lt_p = Pulser(), Pulser(), Pulser()
    prev_buttons = 0

    print("Virtual controller is running. Start your game now.")
    print("Hold BACK + D-pad: Up = on/off, Right/Left = rate, Down = RB auto-fire")
    show_status(enabled, rate, rb_auto)

    try:
        while True:
            try:
                g = XInput.get_state(real).Gamepad
            except XInput.XInputNotConnectedError:
                pad.reset()
                pad.update()
                print("\nController disconnected. Reconnect it (or restart this script).")
                while not XInput.get_connected()[real]:
                    time.sleep(0.5)
                print("Reconnected.")
                show_status(enabled, rate, rb_auto)
                continue

            buttons = g.wButtons
            newly_pressed = buttons & ~prev_buttons
            prev_buttons = buttons

            if buttons & BACK:
                changed = False
                if newly_pressed & DPAD_UP:
                    enabled = not enabled
                    beep(1200 if enabled else 500)
                    changed = True
                if newly_pressed & DPAD_RIGHT:
                    rate = min(MAX_RATE, rate + 1)
                    beep(900)
                    changed = True
                if newly_pressed & DPAD_LEFT:
                    rate = max(MIN_RATE, rate - 1)
                    beep(700)
                    changed = True
                if newly_pressed & DPAD_DOWN:
                    rb_auto = not rb_auto
                    beep(1000 if rb_auto else 600)
                    changed = True
                if changed:
                    show_status(enabled, rate, rb_auto)
                buttons &= ~DPAD_ALL

            now = time.perf_counter()
            period = 1.0 / rate
            rt, lt = g.bRightTrigger, g.bLeftTrigger

            if enabled and AUTOFIRE_RT and rt > TRIGGER_THRESHOLD:
                rt = 255 if rt_p.output(True, now, period) else 0
            else:
                rt_p.output(False, now, period)

            if enabled and AUTOFIRE_LT and lt > TRIGGER_THRESHOLD:
                lt = 255 if lt_p.output(True, now, period) else 0
            else:
                lt_p.output(False, now, period)

            if enabled and rb_auto and (buttons & RB):
                if not rb_p.output(True, now, period):
                    buttons &= ~RB
            else:
                rb_p.output(False, now, period)

            r = pad.report
            r.wButtons = buttons
            r.bLeftTrigger = lt
            r.bRightTrigger = rt
            r.sThumbLX, r.sThumbLY = g.sThumbLX, g.sThumbLY
            r.sThumbRX, r.sThumbRY = g.sThumbRX, g.sThumbRY
            pad.update()

            time.sleep(POLL_SECONDS)

    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        try:
            pad.reset()
            pad.update()
            XInput.set_vibration(real, 0, 0)
        except Exception:
            pass


if __name__ == "__main__":
    main()
