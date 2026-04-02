# Before running: pip install hx711-rpi RPi.GPIO
# Calibrate: place a known weight, note raw, then set SCALE = raw / known_weight and rerun.

#!/usr/bin/env python3
import sys
import time
import threading
import queue
import termios
import tty
import atexit

from hx711 import HX711
import RPi.GPIO as GPIO

DT_PIN = 5    # GPIO5 (DOUT)
SCK_PIN = 6   # GPIO6 (PD_SCK)
SAMPLES = 5   # readings to average
CAL_SAMPLES = 10  # readings to average when calibrating
SLEEP = 0.2   # seconds between prints
TARE_SAMPLES = 10  # readings to average when taring

# Replace after calibration: SCALE = raw_counts / known_weight
SCALE = -721.7  # placeholder; adjust after calibration
KNOWN_WEIGHT_G = 100.0  # set to the calibration mass you place on the scale

ORIG_TERM_ATTRS = None

def start_key_listener(cmds: queue.Queue):
   """Listen for single keypresses (no Enter needed)."""
   global ORIG_TERM_ATTRS
   if sys.stdin.isatty():
       ORIG_TERM_ATTRS = termios.tcgetattr(sys.stdin)
       tty.setcbreak(sys.stdin)
       atexit.register(restore_terminal)

   def _listener():
       while True:
           ch = sys.stdin.buffer.read(1)
           if not ch:
               break
           ch = ch.decode(errors="ignore").lower()
           if ch:
               cmds.put(ch)

   t = threading.Thread(target=_listener, daemon=True)
   t.start()


def restore_terminal():
   global ORIG_TERM_ATTRS
   if ORIG_TERM_ATTRS and sys.stdin.isatty():
       termios.tcsetattr(sys.stdin, termios.TCSADRAIN, ORIG_TERM_ATTRS)
       ORIG_TERM_ATTRS = None


def tare_scale(hx: HX711):
   # Fallback tare for drivers without tare()/zero(): store baseline
   baseline = read_mean(hx, TARE_SAMPLES)
   hx._offset = baseline  # stash on instance


def read_mean(hx: HX711, samples: int) -> float:
   readings = hx.get_raw_data(times=samples)
   return sum(readings) / float(len(readings))


def get_weight_mean(hx: HX711, samples: int) -> float:
   offset = getattr(hx, "_offset", 0.0)
   return read_mean(hx, samples) - offset


def calibrate_scale(hx: HX711, known_weight_g: float):
   """Compute SCALE using the current known weight on the platform."""
   global SCALE
   raw = get_weight_mean(hx, CAL_SAMPLES)
   SCALE = raw / known_weight_g
   print(f"Calibrated: raw={raw:.1f} at {known_weight_g}g -> SCALE={SCALE:.3f}")


def main():
   hx = HX711(dout_pin=DT_PIN, pd_sck_pin=SCK_PIN)
   hx.reset()
   tare_scale(hx)

   cmds = queue.Queue()
   start_key_listener(cmds)
   print(f"HX711 test: 't' to tare, 'c' to calibrate {KNOWN_WEIGHT_G}g, Ctrl+C to exit")
   print(f"Current SCALE: {SCALE}")
   try:
       while True:
           while not cmds.empty():
               cmd = cmds.get_nowait()
               if cmd == "t":
                   print("Taring...")
                   tare_scale(hx)
                   print("Tare complete.")
               if cmd == "c":
                   print(f"Calibrating with {KNOWN_WEIGHT_G}g on the scale...")
                   calibrate_scale(hx, KNOWN_WEIGHT_G)
           raw = get_weight_mean(hx, SAMPLES)
           grams = raw / SCALE
           print(f"Raw: {raw:10.1f} | Weight: {grams:8.2f} g", flush=True)
           time.sleep(SLEEP)
   except KeyboardInterrupt:
       pass
   finally:
       GPIO.cleanup()
       restore_terminal()
       print("Goodbye.")


if __name__ == "__main__":
   main()

