#!/usr/bin/env python3
#ADD WEIGHT BEFORE RUNNING
import RPi.GPIO as GPIO, time, signal, sys

STEP, DIR, EN = 17, 27, 22
STEP_DELAY = 0.01  # 5 ms high, 5 ms low (slow and visible)

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
    step_delay = 0.05  # Start slow for high torque
    accel_steps = 200  # Steps to reach full speed
    accel_increment = (0.05 - STEP_DELAY) / accel_steps

    step_count = 0
    while True:
        GPIO.output(STEP, GPIO.HIGH)
        time.sleep(step_delay)
        GPIO.output(STEP, GPIO.LOW)
        time.sleep(step_delay)

        step_count += 1
        if step_count < accel_steps:
            step_delay = max(STEP_DELAY, step_delay - accel_increment)  # Accelerate
finally:
    cleanup(0)


