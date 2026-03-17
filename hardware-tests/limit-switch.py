import RPi.GPIO as GPIO
import time

PIN = 17  # BCM numbering; use the GPIO wired to the white signal wire

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # internal pull‑up

print("Reading endstop. Press Ctrl+C to quit.")

try:
    last_state = GPIO.input(PIN)
    while True:
        state = GPIO.input(PIN)
        if state != last_state:
            if state == GPIO.LOW:
                print("SWITCH PRESSED")
            else:
                print("SWITCH RELEASED")
            last_state = state
        time.sleep(0.01)   # simple debounce / CPU relief
except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()
