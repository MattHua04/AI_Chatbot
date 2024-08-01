import time
from config import *
import RPi.GPIO as GPIO
from multiprocessing import Process, Queue

def tactileInit():
    # Set up buttons
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Action button
    GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Volume down button
    GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Volume up button
    # Start button audio feedback
    buttonPresses = Queue()
    actionButtonCounter = Process(target=buttonCounter, args=(buttonPresses,))
    actionButtonCounter.start()
    return buttonPresses

def buttonCounter(buttonPresses):
    while True:
        if (
            GPIO.input(16) == GPIO.HIGH
            or GPIO.input(23) == GPIO.HIGH
            or GPIO.input(24) == GPIO.HIGH
        ):
            buttonPresses.put("press")
            while (
                GPIO.input(16) == GPIO.HIGH
                or GPIO.input(23) == GPIO.HIGH
                or GPIO.input(24) == GPIO.HIGH
            ):
                time.sleep(0.1)