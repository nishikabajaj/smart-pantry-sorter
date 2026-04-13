import RPi.GPIO as GPIO
import time

# Pin configuration
HALL_PIN = 17  # Change this to your chosen GPIO pin

# GPIO Setup
GPIO.setmode(GPIO.BCM)
# Use internal pull-up resistor so the pin defaults to HIGH
GPIO.setup(HALL_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def magnet_detected(channel):
    """Callback function triggered when magnet is detected."""
    print("Magnet Detected!")

try:
    print("Hall Effect Sensor Test - Waiting for magnet...")
    # Add event detection for a FALLING edge (HIGH to LOW transition)
    GPIO.add_event_detect(HALL_PIN, GPIO.FALLING, callback=magnet_detected, bouncetime=200)

    # Keep the script running
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nCleaning up...")
    GPIO.cleanup()
