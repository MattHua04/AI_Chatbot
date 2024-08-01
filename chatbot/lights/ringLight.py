import time
from config import *
import RPi.GPIO as GPIO
from rpi_ws281x import *
from multiprocessing import Process, Queue

def lightsInit():
    LED_COUNT = 45  # Number of LED pixels.
    LED_PIN = 10  # GPIO pin connected to the pixels (18 uses PWM!).
    # LED_PIN = 10		# GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10  # DMA channel to use for generating signal (try 10)
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = (
        False
    )  # True to invert the signal (when using NPN transistor level shift)
    LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53
    pixels = PixelStrip(
        LED_COUNT,
        LED_PIN,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        LED_BRIGHTNESS,
        LED_CHANNEL,
    )
    pixels.begin()
    lightsUsageStatus = Queue()
    sleepLightsState = Queue()
    currentColor = Queue()
    onOff = Queue()
    return pixels, lightsUsageStatus, sleepLightsState, currentColor, onOff

def wheel(pos):
    # Generate rainbow colors across 0-255 positions.
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)


def lightsControl(pixels, onOff, lightsUsageStatus, sleepLightsState):
    # Turn on the lights
    lightsUsageStatus.put(True)
    for i in range(pixels.numPixels()):
        pixels.setPixelColor(i, wheel((int(i * 256 / pixels.numPixels())) & 255))
        pixels.show()
        time.sleep(5 / 1000.0)
    while onOff.empty():
        for j in range(256):
            for i in range(pixels.numPixels()):
                pixels.setPixelColor(
                    i, wheel((int(i * 256 / pixels.numPixels()) + j) & 255)
                )
            pixels.show()
            time.sleep(3 / 1000.0)
    # Turn off the lights
    onOff.get()
    for i in range(pixels.numPixels())[::-1]:
        pixels.setPixelColor(i, Color(0, 0, 0))
        pixels.show()
        time.sleep(5 / 1000.0)
    lightsUsageStatus.put(False)


def sleepLights(pixels, sleepLightsState, currentColor):
    high = 25
    low = 3
    downTime = 1 / (45 * (high - low))
    pause = False
    while not sleepLightsState.empty():
        sleepLightsState.get()
    while sleepLightsState.empty():
        for intensity in range(low, high):
            for i in range(pixels.numPixels()):
                if not sleepLightsState.empty():
                    while not sleepLightsState.empty():
                        request = sleepLightsState.get()
                        if request == "pause":
                            pause = True
                    if pause:
                        resume = False
                        while not resume:
                            if not sleepLightsState.empty():
                                while not sleepLightsState.empty():
                                    request = sleepLightsState.get()
                                    if request == "resume":
                                        resume = True
                                        break
                        continue
                    else:
                        return
                pixels.setPixelColor(i, Color(intensity, 0, 0))
                while not currentColor.empty():
                    currentColor.get()
                currentColor.put(Color(intensity, 0, 0))
                time.sleep(downTime)
            pixels.show()
        for intensity in range(low, high + 1)[::-1]:
            for i in range(pixels.numPixels()):
                if not sleepLightsState.empty():
                    while not sleepLightsState.empty():
                        request = sleepLightsState.get()
                        if request == "pause":
                            pause = True
                    if pause:
                        resume = False
                        while not resume:
                            if not sleepLightsState.empty():
                                while not sleepLightsState.empty():
                                    request = sleepLightsState.get()
                                    if request == "resume":
                                        resume = True
                                        break
                        continue
                    else:
                        return
                pixels.setPixelColor(i, Color(intensity, 0, 0))
                while not currentColor.empty():
                    currentColor.get()
                currentColor.put(Color(intensity, 0, 0))
                time.sleep(downTime)
            pixels.show()


def clearLights(pixels):
    for i in range(pixels.numPixels())[::-1]:
        pixels.setPixelColor(i, Color(0, 0, 0))
        pixels.show()
        time.sleep(5 / 1000.0)
        
def volLights(pixels, volQueue, lightsUsageStatus, sleepLightsState, currentColor, terminateVolLights):
    lastRequest = time.time()
    volLightsOn = False
    while True:
        while not terminateVolLights.empty():
            terminateVolLights.get()
            try:
                volLightsOff.terminate()
            except:
                pass
        while not lightsUsageStatus.empty():
            lightsInUse = lightsUsageStatus.get()
        if time.time() - lastRequest >= 2 and volLightsOn:
            volLightsOff = Process(
                target=volLightsCooldown,
                args=(pixels, lightsInUse, sleepLightsState, currentColor),
            )
            volLightsOff.start()
            volLightsOn = False
        if not volQueue.empty():
            lastRequest = time.time()
            volLightsOn = True
            currentVol = volQueue.get()
            if lightsInUse == "sleep" or not lightsInUse:
                sleepLightsState.put("pause")
                redBackGround = Color(20, 0, 0)
                if lightsInUse == "sleep":
                    while not currentColor.empty():
                        redBackGround = currentColor.get()
                    currentColor.put(redBackGround)
                for i in range(pixels.numPixels())[
                    round((currentVol / 100) * pixels.numPixels()) :
                ]:
                    pixels.setPixelColor(i, redBackGround)
                pixels.show()
                for i in range(round((currentVol / 100) * pixels.numPixels())):
                    pixels.setPixelColor(i, Color(20, 20, 20))
                pixels.show()
                
def volLightsCooldown(pixels, lightsInUse, sleepLightsState, currentColor):
    if not lightsInUse:
        for i in range(pixels.numPixels())[::-1]:
            pixels.setPixelColor(i, Color(0, 0, 0))
            pixels.show()
            time.sleep(5 / 1000.0)
    else:
        currentShade = Color(0, 0, 0)
        while not currentColor.empty():
            currentShade = currentColor.get()
        for i in range(pixels.numPixels())[::-1]:
            pixels.setPixelColor(i, currentShade)
            pixels.show()
            time.sleep(5 / 1000.0)
    if lightsInUse == "sleep":
        sleepLightsState.put("resume")