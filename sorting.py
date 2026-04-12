#!/usr/bin/env python3
import sys, time, signal, load_cell
import inventory
import RPi.GPIO as GPIO

STEP, DIR, EN = 17, 27, 22

LIMIT_PINS = {
    1: 18,
    2: 23,
    3: 24,
    4: 25,
}

# The physical limit switch that gets triggered when rotating to a
# target bin is NOT the switch numbered the same as that bin. The carousel has
# a single stopper, and the switch positions are physically laid out so that
# arriving at a bin activates a *different* switch number.

# Mapping (bin -> which limit switch position is activated upon arrival):
#   Bin 1 -> Position 1  (switch at LIMIT_PINS[1])
#   Bin 2 -> Position 4  (switch at LIMIT_PINS[4])
#   Bin 3 -> Position 3  (switch at LIMIT_PINS[3])
#   Bin 4 -> Position 2  (switch at LIMIT_PINS[2])

BIN_TO_LIMIT_POSITION = {
    1: 1,
    2: 4,
    3: 3,
    4: 2,
}

STEP_DELAY = 0.005
POLL_DELAY = 0.01

def setup():
    if GPIO.getmode() is None:        # ← only set mode if not already set
        GPIO.setmode(GPIO.BCM)
    GPIO.setup(STEP, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(DIR, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(EN, GPIO.OUT, initial=GPIO.HIGH)
    for pin in LIMIT_PINS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.output(EN, GPIO.LOW)


def cleanup(code=0):
    try:
        GPIO.output(STEP, GPIO.LOW)
        GPIO.output(EN, GPIO.HIGH)
    finally:
        GPIO.cleanup()


def lookup_item_target(item_id):
    q = "SELECT category FROM masterinventory WHERE id = ?"
    category_row = inventory.get_data(q, (item_id,))
    if not category_row:
        print("This item has not been added to the pantry or has no category.")
        return None

    category_id = category_row[0][0]

    q = "SELECT id FROM bin WHERE category_id = ?"
    bin_row = inventory.get_data(q, (category_id,))
    if not bin_row:
        print("No bin exists for this category.")
        return None

    bin_id = bin_row[0][0]

    return item_id, category_id, bin_id


def get_limit_state(bin_id):
    pin = LIMIT_PINS[bin_id]
    return GPIO.input(pin) == GPIO.HIGH


def step_motor(direction=GPIO.LOW):
    GPIO.output(DIR, direction)
    GPIO.output(STEP, GPIO.HIGH)
    time.sleep(STEP_DELAY)
    GPIO.output(STEP, GPIO.LOW)
    time.sleep(STEP_DELAY)


def rotate_until_bin(target_bin, direction=GPIO.LOW, max_steps=5000):
    target_limit_position = BIN_TO_LIMIT_POSITION[target_bin]
    
    for _ in range(max_steps):
        if get_limit_state(target_limit_position):
            return True
        step_motor(direction)
        time.sleep(POLL_DELAY)
    return False


def sort_item(item_id):
    setup()
    target = lookup_item_target(item_id)
    if not target:
        print("lookup_item_target returned None")
        return False

    _, category_id, bin_id = target
    print(f"Target bin_id: {bin_id}")
    print(f"Limit switch states at startup:")
    for b, pos in BIN_TO_LIMIT_POSITION.items():
        pin = LIMIT_PINS[pos]
        print(f"  bin {b} -> limit position {pos} -> pin {pin} -> {GPIO.input(pin)}")

    ok = rotate_until_bin(bin_id)
    print(f"rotate_until_bin returned: {ok}")
    if not ok:
        print(f"Could not position bin {bin_id} for category {category_id}.")
        return False

    print(f"Item {item_id} sorted to bin {bin_id} for category {category_id}.")
    return True


def main():
    setup()
    signal.signal(signal.SIGINT, lambda s, f: cleanup(0))
    try:
        item_id = int(sys.argv[1])
        sort_item(item_id)
    finally:
        cleanup(0)


if __name__ == "__main__":
    main()