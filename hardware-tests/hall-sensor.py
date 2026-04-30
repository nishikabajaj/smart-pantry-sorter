import RPi.GPIO as GPIO
import time

HALL_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(HALL_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Hall Effect Sensor Test - Waiting for magnet...")

try:
    prev = GPIO.input(HALL_PIN)
    while True:
        curr = GPIO.input(HALL_PIN)
        if prev == GPIO.HIGH and curr == GPIO.LOW:  # FALLING edge
            print("Magnet Detected!")
        prev = curr
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nCleaning up...")
    GPIO.cleanup()