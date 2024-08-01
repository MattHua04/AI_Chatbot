import math
import time
import certifi
import alsaaudio
from config import *
import RPi.GPIO as GPIO
from pymongo import MongoClient
from multiprocessing import Process, Queue
from chatbot.lights.ringLight import *
from chatbot.audio.audioOut import *

def volControlInit(pixels, lightsUsageStatus, sleepLightsState, currentColor):
    # Volume control requirements
    audio = alsaaudio.Mixer("Speaker")
    audio.setvolume(
        round(math.log((stateCol.find_one()['volume']) * 25 / 19) / 0.0488)
    )  # Default volume level to database volume
    volLevelVerbal = Queue()
    volLevelButton = Queue()
    volQueue = Queue()
    # Start volume control process
    controlVol = Process(
        target=volControl,
        args=(
            audio,
            pixels,
            volLevelVerbal,
            volLevelButton,
            volQueue,
            lightsUsageStatus,
            sleepLightsState,
            currentColor,
        ),
    )
    controlVol.start()
    return audio, volLevelVerbal, volLevelButton, volQueue

def volControl(
    audio,
    pixels,
    volLevelVerbal,
    volLevelButton,
    volQueue,
    lightsUsageStatus,
    sleepLightsState,
    currentColor,
):
    db = MongoClient(MDB_CONN_STR, tlsCAFile=certifi.where())['test']
    stateCol = db["spotifies"]
    currentVol = -1
    terminateVolLights = Queue()
    volLightsProcess = Process(
        target=volLights,
        args=(pixels, volQueue, lightsUsageStatus, sleepLightsState, currentColor, terminateVolLights),
    )
    volLightsProcess.start()
    while True:
        if not volLevelVerbal.empty():
            currentVol = volLevelVerbal.get()
        state = None
        while state == None:
            try:
                state = stateCol.find_one()
            except:
                db = MongoClient(MDB_CONN_STR, tlsCAFile=certifi.where())['test']
                stateCol = db["spotifies"]
                state = stateCol.find_one()

        # Set volume
        requestVol = state['volume']
        if currentVol != requestVol:
            currentVol = requestVol
            volQueue.put(requestVol)
            try:
                audio.setvolume(
                    round(math.log((requestVol) * 25 / 19) / 0.0488)
                )
            except:
                audio.setvolume(0)
        
        # Increase volume
        if GPIO.input(23) == GPIO.HIGH and GPIO.input(24) == GPIO.LOW:
            try:
                terminateVolLights.put("terminate")
            except:
                pass
            if currentVol == -1:
                currentVol = (
                    round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5) * 5
                )
            if round(currentVol) <= 100:
                try:
                    audio.setvolume(
                        round(math.log((currentVol + 5) * 25 / 19) / 0.0488)
                    )
                    volLevelVerbal.put(currentVol + 5)
                    volLevelButton.put(currentVol + 5)
                    stateCol.update_one(state, {'$set': {'volume': currentVol + 5}})
                except:
                    audio.setvolume(100)
                    stateCol.update_one(state, {'$set': {'volume': 100}})
            currentVol = currentVol + 5 if (currentVol + 5 < 100) else 100
            volQueue.put(currentVol)
            holdStart = time.time()
            while GPIO.input(23) == GPIO.HIGH and GPIO.input(24) == GPIO.LOW:
                time.sleep(0.1)
                if time.time() - holdStart >= 1:
                    try:
                        terminateVolLights.put("terminate")
                    except:
                        pass
                    if currentVol == -1:
                        currentVol = (
                            round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5)
                            * 5
                        )
                    if round(currentVol) <= 100:
                        state = stateCol.find_one()
                        try:
                            click = Process(target=buttonSound)
                            click.start()
                            audio.setvolume(
                                round(math.log((currentVol + 5) * 25 / 19) / 0.0488)
                            )
                            volLevelVerbal.put(currentVol + 5)
                            volLevelButton.put(currentVol + 5)
                        except:
                            audio.setvolume(100)
                    currentVol = currentVol + 5 if (currentVol + 5 < 100) else 100
                    stateCol.update_one(state, {'$set': {'volume': currentVol}})
                    volQueue.put(currentVol)
        # Decrease volume
        elif GPIO.input(23) == GPIO.LOW and GPIO.input(24) == GPIO.HIGH:
            try:
                terminateVolLights.put("terminate")
            except:
                pass
            if currentVol == -1:
                currentVol = (
                    round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5) * 5
                )
            if round(currentVol) >= 0:
                try:
                    audio.setvolume(
                        round(math.log((currentVol - 5) * 25 / 19) / 0.0488)
                    )
                    volLevelVerbal.put(currentVol - 5)
                    volLevelButton.put(currentVol - 5)
                    stateCol.update_one(state, {'$set': {'volume': currentVol - 5}})
                except:
                    audio.setvolume(0)
                    stateCol.update_one(state, {'$set': {'volume': 0}})
            currentVol = currentVol - 5 if (currentVol - 5 > 0) else 0
            volQueue.put(currentVol)
            holdStart = time.time()
            while GPIO.input(23) == GPIO.HIGH or GPIO.input(24) == GPIO.HIGH:
                time.sleep(0.1)
                if time.time() - holdStart >= 1:
                    try:
                        terminateVolLights.put("terminate")
                    except:
                        pass
                    if currentVol == -1:
                        currentVol = (
                            round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5)
                            * 5
                        )
                    if round(currentVol) >= 0:
                        state = stateCol.find_one()
                        try:
                            click = Process(target=buttonSound)
                            click.start()
                            audio.setvolume(
                                round(math.log((currentVol - 5) * 25 / 19) / 0.0488)
                            )
                            volLevelVerbal.put(currentVol - 5)
                            volLevelButton.put(currentVol - 5)
                        except:
                            audio.setvolume(0)
                    currentVol = currentVol - 5 if (currentVol - 5 > 0) else 0
                    stateCol.update_one(state, {'$set': {'volume': currentVol}})
                    volQueue.put(currentVol)