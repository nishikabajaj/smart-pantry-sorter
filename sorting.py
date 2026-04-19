#!/usr/bin/env python3
import sys, time, signal
import inventory
import RPi.GPIO as GPIO

STEP     = 17
DIR      = 27
EN       = 22
HALL_PIN = 18

NUM_BINS = 4  # bins 0-3 (bin_id 1-4 in DB)

# Ramp config
STEP_DELAY_START = 0.05   # slow start (high torque)
STEP_DELAY_MIN   = 0.005  # full speed
ACCEL_STEPS      = 200    # steps to reach full speed

# Safety limit — max steps per bin transit before giving up.
# Prevents infinite spinning
MAX_STEPS_PER_BIN = 300

# For the demo, bin 0 is assumed to be facing the user at startup.
_current_bin_index = 1


def setup():
    if GPIO.getmode() is None:
        GPIO.setmode(GPIO.BCM)
    GPIO.setup(STEP,     GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(DIR,      GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(EN,       GPIO.OUT, initial=GPIO.LOW)   # LOW = enabled on A4988
    GPIO.setup(HALL_PIN, GPIO.IN,  pull_up_down=GPIO.PUD_UP)
    GPIO.output(EN, GPIO.LOW)


def cleanup():
    try:
        GPIO.output(STEP, GPIO.LOW)
        GPIO.output(EN,   GPIO.HIGH)  # disable driver
    finally:
        GPIO.cleanup()


def hall_detected() -> bool:
    """Returns True when the hall sensor sees a magnet (active-low)."""
    return GPIO.input(HALL_PIN) == GPIO.LOW


def _step_once(delay: float):
    """Send one step pulse at the given half-period delay."""
    GPIO.output(STEP, GPIO.HIGH)
    time.sleep(delay)
    GPIO.output(STEP, GPIO.LOW)
    time.sleep(delay)


def _wait_for_hall_pulse(accel_state: dict) -> bool:
    """
    Step the motor until the hall sensor fires (LOW), then step past it
    until it releases (HIGH again) to avoid re-triggering on the same magnet.
    Uses shared accel_state dict so ramp continues smoothly across multiple
    bin transits.
    Returns True if the pulse was detected, False if MAX_STEPS_PER_BIN exceeded.
    """
    steps = 0
    OVERSHOOT_STEPS = 10  # tune up/down as needed

    # Step until sensor fires
    while not hall_detected():
        _step_once(accel_state['delay'])
        if accel_state['count'] < ACCEL_STEPS:
            accel_state['delay'] = max(
                STEP_DELAY_MIN,
                accel_state['delay'] - accel_state['increment']
            )
        accel_state['count'] += 1
        steps += 1
        if steps > MAX_STEPS_PER_BIN:
            print("Hall sensor not detected — exceeded MAX_STEPS_PER_BIN.")
            return False

    # Step past the magnet so sensor releases before next transit
    while hall_detected():
        _step_once(accel_state['delay'])
        accel_state['count'] += 1
        
    # Extra steps to nudge bin flush to the user-facing position
    for _ in range(OVERSHOOT_STEPS):
        _step_once(accel_state['delay'])
        accel_state['count'] += 1

    return True


def rotate_to_bin_index(target_index: int) -> bool:
    """
    Rotate the carousel forward (DIR=HIGH) by counting hall sensor pulses.
    Each pulse = passing one bin. Stops after the required number of pulses.
    Returns True if the move completed successfully.
    """
    global _current_bin_index

    pulses_needed = (target_index - _current_bin_index) % NUM_BINS
    if pulses_needed == 0:
        print(f"Already at bin index {target_index}.")
        return True

    print(f"Rotating {pulses_needed} bin(s) to reach index {target_index}.")
    GPIO.output(DIR, GPIO.LOW)

    # Shared acceleration state across all pulses so ramp is continuous
    accel_state = {
        'delay':     STEP_DELAY_START,
        'increment': (STEP_DELAY_START - STEP_DELAY_MIN) / ACCEL_STEPS,
        'count':     0,
    }

    for pulse in range(pulses_needed):
        ok = _wait_for_hall_pulse(accel_state)
        if not ok:
            print(f"Failed on pulse {pulse + 1} of {pulses_needed}.")
            return False
        _current_bin_index = (_current_bin_index + 1) % NUM_BINS
        print(f"Passed bin index {_current_bin_index}.")

    print(f"Now at bin index {_current_bin_index}.")
    return _current_bin_index == target_index


# DB lookup 


def bin_id_to_index(bin_id: int) -> int:
    """Convert a 1-based DB bin_id to a 0-based carousel index."""
    return (bin_id - 1) % NUM_BINS


def lookup_item_target(item_id):
    """
    Returns (item_id, category_id, bin_id) for the given item,
    or None if the item has no category or no assigned bin.
    """
    category_row = inventory.get_data(
        "SELECT category FROM masterinventory WHERE id = ?", (item_id,)
    )
    if not category_row:
        print("Item has no category in masterinventory.")
        return None

    category_id = category_row[0][0]

    bin_row = inventory.get_data(
        "SELECT id FROM bin WHERE category_id = ?", (category_id,)
    )
    if not bin_row:
        print("No bin exists for this category.")
        return None

    bin_id = bin_row[0][0]
    return item_id, category_id, bin_id


# Public entry point

def sort_item(item_id: int) -> bool:
    """
    Look up which bin the item belongs to, rotate the carousel to that bin,
    and return True on success. Called by inventory.py after adding an item.
    """
    setup()

    target = lookup_item_target(item_id)
    if not target:
        return False

    _, category_id, bin_id = target
    target_index = bin_id_to_index(bin_id)
    print(f"Item {item_id} -> category {category_id} -> bin_id {bin_id} -> carousel index {target_index}")

    ok = rotate_to_bin_index(target_index)
    if ok:
        print(f"Item {item_id} sorted successfully.")
    else:
        print(f"Failed to reach carousel index {target_index}.")
    return ok


# CLI

def main():
    setup()
    signal.signal(signal.SIGINT, lambda s, f: (cleanup(), sys.exit(0)))

    if len(sys.argv) < 2:
        print("Usage: python sorting.py <item_id>")
        cleanup()
        return

    try:
        item_id = int(sys.argv[1])
        sort_item(item_id)
    finally:
        cleanup()


if __name__ == "__main__":
    main()