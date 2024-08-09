import time
from config import *
import RPi.GPIO as GPIO
from multiprocessing import Process, Queue

def readInputs():
    highCounts = {"action": 0, "volumeDown": 0, "volumeUp": 0}
    start = time.time()
    while time.time() - start < 0.01:
        if GPIO.input(16) == GPIO.HIGH:
            highCounts["action"] += 1
        elif GPIO.input(23) == GPIO.HIGH:
            highCounts["volumeDown"] += 1
        elif GPIO.input(24) == GPIO.HIGH:
            highCounts["volumeUp"] += 1
    maxButton = max(highCounts, key=highCounts.get)
    maxCount = highCounts[maxButton]
    return maxButton if maxCount > 0 else ''

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
        if (readInputs() != ""):
            buttonPresses.put("press")
            while (readInputs() != ""):
                pass