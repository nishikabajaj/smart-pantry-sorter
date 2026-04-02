#!/usr/bin/env python3
import sys
import time
import RPi.GPIO as GPIO

# BCM GPIO numbers for the four limit switches; edit as needed.
# Wiring example (NO contact to GND, C to GPIO):
#  Limit 1 -> GPIO18
#  Limit 2 -> GPIO23
#  Limit 3 -> GPIO24
#  Limit 4 -> GPIO25
PINS = [18, 23, 24, 25]
REFRESH_SECONDS = 0.1


def setup():
   GPIO.setmode(GPIO.BCM)
   for pin in PINS:
       GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def read_states():
   # Returns list of booleans: True means switch is pressed/closed (wired NC->GPIO, NO->GND).
   # With this wiring the pin idles LOW; pressing opens NC and the pull-up drives the pin HIGH.
   return [GPIO.input(pin) == GPIO.HIGH for pin in PINS]


def print_states(states):
   # Log every poll as a single line with a timestamp.
   stamp = time.strftime("%H:%M:%S")
   values = " ".join(f"L{i+1}:{'YES' if s else 'NO '}" for i, s in enumerate(states))
   sys.stdout.write(f"{stamp}  {values}\n")
   sys.stdout.flush()


def main():
   setup()
   last_states = None
   try:
       while True:
           states = read_states()
           print_states(states)
           if last_states is not None and states != last_states:
               changes = []
               for i, (prev, curr) in enumerate(zip(last_states, states)):
                   if prev != curr:
                       changes.append(f"L{i+1} -> {'PRESSED' if curr else 'OPEN'}")
               if changes:
                   sys.stdout.write("  CHANGE: " + ", ".join(changes) + "\n")
                   sys.stdout.flush()
           last_states = states
           time.sleep(REFRESH_SECONDS)
   except KeyboardInterrupt:
       pass
   finally:
       GPIO.cleanup()
       print("Exiting.")


if __name__ == "__main__":
   main()



