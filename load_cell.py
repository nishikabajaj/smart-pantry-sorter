import time
from hx711 import HX711
import RPi.GPIO as GPIO

DT_PIN      = 5
SCK_PIN     = 6
SAMPLES     = 5
TARE_SAMPLES = 10
CAL_SAMPLES  = 10
SCALE        = -721.7  # update after calibration

GPIO.setwarnings(False)

hx = HX711(dout_pin=DT_PIN, pd_sck_pin=SCK_PIN)
hx.reset()

# Tare on startup
baseline   = sum(hx.get_raw_data(times=TARE_SAMPLES)) / TARE_SAMPLES
hx._offset = baseline


def get_weight_g() -> float:
    offset   = getattr(hx, "_offset", 0.0)
    readings = hx.get_raw_data(times=SAMPLES)
    raw      = sum(readings) / len(readings) - offset
    return raw / SCALE


def stable_weight_g(tolerance_g: float = 2.0, retries: int = 5, delay: float = 0.3) -> float:
    prev = get_weight_g()
    for _ in range(retries):
        time.sleep(delay)
        curr = get_weight_g()
        if abs(curr - prev) <= tolerance_g:
            return curr
        prev = curr
    return prev


def cleanup():
    GPIO.cleanup()