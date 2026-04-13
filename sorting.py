#!/usr/bin/env python3
import sys, time, signal
import inventory
import RPi.GPIO as GPIO

STEP, DIR, EN = 17, 27, 22

HALL_PIN = 18

# Carousel has 4 bins arranged in order around the wheel.
# Index 0 = bin_id 1, index 1 = bin_id 2, etc.
# Rotating forward (DIR=LOW) increments the index.
NUM_BINS    = 4
STEP_DELAY  = 0.005
POLL_DELAY  = 0.01

STEP_DELAY = 0.005
POLL_DELAY = 0.01

# Steps between one bin and the next — tune after hardware testing.
# With a 200-step/rev motor and 4 bins this would be 200/4 = 50,
# but gearing/microstepping may change this.
# Run python sorting.py --home then manually step to the next bin and count the steps to calibrate it.
STEPS_PER_BIN = 50

# Tracks which bin is currently at the front (home position).
# Updated every time we detect the hall sensor or complete a move.
_current_bin_index = 0   # 0-based index into the carousel

def setup():
    if GPIO.getmode() is None:        # ← only set mode if not already set
        GPIO.setmode(GPIO.BCM)
    GPIO.setup(STEP, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(DIR, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(EN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(HALL_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.output(EN, GPIO.LOW)


def cleanup():
    try:
        GPIO.output(STEP, GPIO.LOW)
        GPIO.output(EN, GPIO.HIGH)
    finally:
        GPIO.cleanup()

def bin_id_to_index(bin_id: int) -> int:
    """Convert a 1-based DB bin_id to a 0-based carousel index."""
    return (bin_id - 1) % NUM_BINS

def hall_detected() -> bool:
    """Returns True when the sensor sees a magnet (FALLING = LOW)."""
    return GPIO.input(HALL_PIN) == GPIO.LOW


def step_motor(direction=GPIO.LOW):
    GPIO.output(DIR, direction)
    GPIO.output(STEP, GPIO.HIGH)
    time.sleep(STEP_DELAY)
    GPIO.output(STEP, GPIO.LOW)
    time.sleep(STEP_DELAY)

def home_carousel(max_steps=5000) -> bool:
    """Rotate until the hall sensor fires, establishing bin 0 as current position.
    Call once on startup or whenever position is uncertain.
    """
    global _current_bin_index
    for _ in range(max_steps):
        if hall_detected():
            _current_bin_index = 0
            print("Homed to bin index 0.")
            return True
        step_motor()
        time.sleep(POLL_DELAY)
    print("Homing failed — hall sensor not detected within max_steps.")
    return False


def rotate_to_bin_index(target_index: int) -> bool:
    """Rotate the carousel forward to bring target_index to the front.
    Uses step counting between bins rather than polling the sensor mid-move,
    and re-confirms with the hall sensor when passing bin 0.
    """
    global _current_bin_index

    steps_needed = (target_index - _current_bin_index) % NUM_BINS
    if steps_needed == 0:
        print(f"Already at bin index {target_index}.")
        return True

    total_steps = steps_needed * STEPS_PER_BIN
    print(f"Rotating {steps_needed} bin(s) ({total_steps} steps) to reach index {target_index}.")

    for s in range(total_steps):
        step_motor()
        time.sleep(POLL_DELAY)

        # Each time we pass through a bin boundary, update the tracked index.
        # A bin boundary is every STEPS_PER_BIN steps.
        if (s + 1) % STEPS_PER_BIN == 0:
            _current_bin_index = (_current_bin_index + 1) % NUM_BINS
            # If we just passed bin 0, re-confirm with the hall sensor.
            if _current_bin_index == 0:
                if hall_detected():
                    print("Hall sensor confirmed bin 0 passage.")
                else:
                    print("Warning: expected hall pulse at bin 0 but none detected — check calibration.")

    print(f"Now at bin index {_current_bin_index}.")
    return _current_bin_index == target_index


def lookup_item_target(item_id):
    q = "SELECT category FROM masterinventory WHERE id = ?"
    category_row = inventory.get_data(q, (item_id,))
    if not category_row:
        print("Item has no category in masterinventory.")
        return None

    category_id = category_row[0][0]

    q = "SELECT id FROM bin WHERE category_id = ?"
    bin_row = inventory.get_data(q, (category_id,))
    if not bin_row:
        print("No bin exists for this category.")
        return None

    bin_id = bin_row[0][0]

    return item_id, category_id, bin_id



def sort_item(item_id) -> bool:
    setup()
    target = lookup_item_target(item_id)
    if not target:
        return False

    _, category_id, bin_id = target
    target_index = bin_id_to_index(bin_id)
    print(f"Item {item_id} -> category {category_id} -> bin_id {bin_id} -> carousel index {target_index}")

    ok = rotate_to_bin_index(target_index)
    if not ok:
        print(f"Failed to reach carousel index {target_index}.")
        return False

    print(f"Item {item_id} sorted successfully.")
    return True


def main():
    setup()
    signal.signal(signal.SIGINT, lambda s, f: (cleanup(), sys.exit(0)))

    if "--home" in sys.argv:
        home_carousel()
        cleanup()
        return

    if len(sys.argv) < 2:
        print("Usage: python sorting.py <item_id>  |  python sorting.py --home")
        cleanup()
        return

    try:
        item_id = int(sys.argv[1])
        sort_item(item_id)
    finally:
        cleanup()


if __name__ == "__main__":
    main()