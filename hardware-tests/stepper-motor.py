#!/usr/bin/env python3
#ADD WEIGHT BEFORE RUNNING
import RPi.GPIO as GPIO, time, signal, sys

STEP, DIR, EN = 17, 27, 22
STEP_DELAY = 0.005  # 5 ms high, 5 ms low (slow and visible)

def cleanup(code=0):
   GPIO.output(STEP, GPIO.LOW)
   GPIO.output(EN, GPIO.HIGH)  # disable driver
   GPIO.cleanup()
   sys.exit(code)

signal.signal(signal.SIGINT, lambda s, f: cleanup(0))

GPIO.setmode(GPIO.BCM)
GPIO.setup(STEP, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(DIR, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(EN, GPIO.OUT, initial=GPIO.LOW)  # LOW=enabled on A4988

GPIO.output(EN, GPIO.LOW)

# Set direction once; flip to GPIO.HIGH to test the other way.
GPIO.output(DIR, GPIO.LOW)

try:
   while True:
       GPIO.output(STEP, GPIO.HIGH)
       time.sleep(STEP_DELAY)
       GPIO.output(STEP, GPIO.LOW)
       time.sleep(STEP_DELAY)
finally:
   cleanup(0)


