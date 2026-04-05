# HX711 load cell interface for the smart pantry sorter.
#
# Responsibilities:
#   - Owns the HX711 instance and its GPIO lifecycle
#   - Persists calibration (SCALE + offset) across reboots via JSON
#   - Exposes a simple get_weight_g() for inventory.py to call
#   - Provides tare() and calibrate() for setup/maintenance
#
# Usage from another module:
#   from loadcell import LoadCell
#   lc = LoadCell()          # initializes hardware once
#   grams = lc.get_weight_g()
#   lc.cleanup()             # call on shutdown

import json
import os
import time

from hx711 import HX711
import RPi.GPIO as GPIO

# GPIO pins
DT_PIN  = 5   # GPIO5  (DOUT)
SCK_PIN = 6   # GPIO6  (PD_SCK)

# Sampling constants
SAMPLES      = 5   # readings averaged for a normal weight measurement
TARE_SAMPLES = 10  # readings averaged when taring
CAL_SAMPLES  = 10  # readings averaged when calibrating

# Calibration file — persists SCALE and tare offset between runs
CAL_FILE = os.path.join(os.path.dirname(__file__), "loadcell_cal.json")

# Fallback defaults (replace after first real calibration)
DEFAULT_SCALE  = -721.7   # raw counts per gram  — update after calibration
DEFAULT_OFFSET = 0.0      # tare offset in raw counts


def _load_cal() -> tuple[float, float]:
    """Return (scale, offset) from the calibration file, or defaults."""
    if os.path.exists(CAL_FILE):
        try:
            with open(CAL_FILE) as f:
                d = json.load(f)
            return float(d["scale"]), float(d["offset"])
        except (KeyError, ValueError, json.JSONDecodeError):
            pass
    return DEFAULT_SCALE, DEFAULT_OFFSET


def _save_cal(scale: float, offset: float) -> None:
    """Persist (scale, offset) to the calibration file."""
    with open(CAL_FILE, "w") as f:
        json.dump({"scale": scale, "offset": offset}, f, indent=2)
    print(f"Calibration saved -> scale={scale:.4f}, offset={offset:.1f}")


# LoadCell class
class LoadCell:
    """Wraps the HX711 for the pantry sorter.

    Keep one instance alive for the lifetime of the process so that GPIO
    is set up and torn down exactly once.
    """

    def __init__(self):
        self._scale, self._offset = _load_cal()
        self._hx = HX711(dout_pin=DT_PIN, pd_sck_pin=SCK_PIN)
        self._hx.reset()
        # Re-apply the persisted tare offset so the sensor is zeroed
        # without having to physically tare on every startup.
        self._hx._offset = self._offset

    # Internal helpers
    def _read_mean(self, samples: int) -> float:
        """Return the mean of `samples` raw HX711 readings."""
        readings = self._hx.get_raw_data(times=samples)
        return sum(readings) / float(len(readings))

    def _raw_net(self, samples: int) -> float:
        """Mean raw reading minus the stored tare offset."""
        return self._read_mean(samples) - self._offset

    # Public API
    def tare(self) -> None:
        """Zero the scale with nothing on the platform."""
        self._offset = self._read_mean(TARE_SAMPLES)
        self._hx._offset = self._offset
        _save_cal(self._scale, self._offset)
        print("Tare complete.")

    def calibrate(self, known_weight_g: float) -> None:
        """Compute and persist SCALE using a known mass on the platform.

        Place `known_weight_g` grams on the platform before calling this.
        """
        raw_net = self._raw_net(CAL_SAMPLES)
        if abs(raw_net) < 1:
            print("Error: raw net reading is near zero — tare first, then place the weight.")
            return
        self._scale = raw_net / known_weight_g
        _save_cal(self._scale, self._offset)
        print(f"Calibration complete: raw_net={raw_net:.1f} / {known_weight_g}g -> scale={self._scale:.4f}")

    def get_weight_g(self, samples: int = SAMPLES) -> float:
        """Return the current weight in grams (negative means nothing on platform / below tare)."""
        if abs(self._scale) < 1e-6:
            raise RuntimeError("Load cell scale is ~0 — run calibrate() first.")
        return self._raw_net(samples) / self._scale

    def stable_weight_g(self, samples: int = SAMPLES, retries: int = 3,
                         tolerance_g: float = 2.0, delay: float = 0.3) -> float:
        """Return a stable weight by taking two consecutive readings that agree
        within `tolerance_g` grams.  Useful when an item has just been placed
        and the platform is still settling.
        """
        prev = self.get_weight_g(samples)
        for _ in range(retries):
            time.sleep(delay)
            curr = self.get_weight_g(samples)
            if abs(curr - prev) <= tolerance_g:
                return curr
            prev = curr
        # Return the last reading even if it never fully settled
        return prev

    def cleanup(self) -> None:
        """Release GPIO resources.  Call once on process shutdown."""
        try:
            GPIO.cleanup()
        except Exception:
            pass