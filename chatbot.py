import os
import re
import math
import time
import copy
import certifi
import spotipy
import alsaaudio
import sounddevice
import numpy as np
from gtts import gTTS
from rpi_ws281x import *
import RPi.GPIO as GPIO
from openai import OpenAI
from mutagen.mp3 import MP3
from spotipy.oauth2 import *
from threading import Thread
import speech_recognition as sr
from pymongo import MongoClient
from difflib import SequenceMatcher
from multiprocessing import Manager, Process, Queue

def listenForKeyWord(
    recorder,
    audio,
    pixels,
    name,
    messages,
    volLevelVerbal,
    volLevelButton,
    volQueue,
    return_dict,
    sleepLightsState,
):
    # Listen for wakeword
    text = ""
    currentVol = -1
    nums = {
        "min": 0,
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "max": 100,
    }
    with sr.Microphone() as source:
        while "hey " + name.lower() not in text.lower():
            speech = recorder.listen(source, phrase_time_limit=3)
            try:
                text += recorder.recognize_google(speech)
            except:
                pass
            # Reset conversation memory when "reset" is heard
            if "reset" in text.lower():
                messages = []
                print("Conversation reset")
                onOff = Queue()
                lights = Process(
                    target=lightsControl,
                    args=(pixels, onOff, lightsUsageStatus, sleepLightsState),
                )
                processes.append(lights)
                lights.start()
                convertToSpeech("Resetting conversation")
                onOff.put("lightsOff")
                print("\033c", end="\r")
                text = ""
            # Verbally increase volume level
            elif "turn it up" in text.lower() or "louder" in text.lower():
                volChange = 5
                wordList = []
                for word in text.split():
                    try:
                        wordList.append(nums[word])
                    except:
                        pass
                    try:
                        wordList.append(int(word))
                    except:
                        wordList.append(word)
                try:
                    if type(wordList[wordList.index("up") + 1]) == int:
                        volChange = wordList[wordList.index("up") + 1]
                except:
                    pass
                try:
                    if type(wordList[wordList.index("louder") + 1]) == int:
                        volChange = wordList[wordList.index("louder") + 1]
                except:
                    pass
                while not volLevelButton.empty():
                    currentVol = volLevelButton.get()
                text = ""
                click = Process(target=buttonSound)
                click.start()
                if currentVol == -1:
                    currentVol = (
                        round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5) * 5
                    )
                if round(currentVol) <= 95:
                    print("Turning up volume")
                    try:
                        audio.setvolume(
                            round(math.log((currentVol + volChange) * 25 / 19) / 0.0488)
                        )
                        volLevelVerbal.put(currentVol + volChange)
                        volLevelButton.put(currentVol + volChange)
                    except:
                        audio.setvolume(100)
                currentVol = (
                    currentVol + volChange if (currentVol + volChange < 100) else 100
                )
                volQueue.put(currentVol)
            # Verbally reduce volume level
            elif (
                "turn it down" in text.lower()
                or "softer" in text.lower()
                or "mute" in text.lower()
            ):
                volChange = 5
                wordList = []
                for word in text.split():
                    try:
                        wordList.append(nums[word])
                    except:
                        pass
                    try:
                        wordList.append(int(word))
                    except:
                        wordList.append(word)
                try:
                    if type(wordList[wordList.index("down") + 1]) == int:
                        volChange = wordList[wordList.index("down") + 1]
                except:
                    pass
                try:
                    if type(wordList[wordList.index("softer") + 1]) == int:
                        volChange = wordList[wordList.index("softer") + 1]
                except:
                    pass
                while not volLevelButton.empty():
                    currentVol = volLevelButton.get()
                text = ""
                click = Process(target=buttonSound)
                click.start()
                if "mute" in wordList:
                    currentVol = 0
                if currentVol == -1:
                    currentVol = (
                        round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5) * 5
                    )
                if round(currentVol) >= 5:
                    print("Turning down volume")
                    try:
                        audio.setvolume(
                            round(math.log((currentVol - volChange) * 25 / 19) / 0.0488)
                        )
                        volLevelVerbal.put(currentVol - volChange)
                        volLevelButton.put(currentVol - volChange)
                    except:
                        audio.setvolume(0)
                currentVol = (
                    currentVol - volChange if (currentVol - volChange > 0) else 0
                )
                volQueue.put(currentVol)
            # Verbally set volume level
            elif "set volume to" in text.lower():
                wordList = []
                skip = False
                for word in text.split():
                    try:
                        wordList.append(nums[word])
                    except:
                        pass
                    try:
                        wordList.append(int(word))
                    except:
                        wordList.append(word)
                try:
                    if type(wordList[wordList.index("to") + 1]) == int:
                        currentVol = round(wordList[wordList.index("to") + 1] / 5) * 5
                except:
                    skip = True
                if not skip:
                    text = ""
                    click = Process(target=buttonSound)
                    click.start()
                    if 0 <= currentVol and currentVol <= 100:
                        print("Setting volume to " + str(currentVol))
                        try:
                            audio.setvolume(
                                round(math.log((currentVol) * 25 / 19) / 0.0488)
                            )
                            volLevelVerbal.put(currentVol)
                            volLevelButton.put(currentVol)
                        except:
                            audio.setvolume(0)
                    if 0 <= currentVol and currentVol <= 100:
                        currentVol = currentVol
                    else:
                        if currentVol < 0:
                            currentVol = 0
                        if currentVol > 100:
                            currentVol = 100
                    volQueue.put(currentVol)
            # Reboot RPi when "reboot" is heard
            elif "reboot" in text.lower():
                print("Rebooting . . .")
                onOff = Queue()
                lights = Process(
                    target=lightsControl,
                    args=(pixels, onOff, lightsUsageStatus, sleepLightsState),
                )
                processes.append(lights)
                lights.start()
                convertToSpeech("Rebooting")
                onOff.put("lightsOff")
                lights.join()
                print("\033c", end="\r")
                messages = "reboot"
                break
    return_dict[0] = messages


def listenForPrompt(recorder, sp, return_dict):
    text = ""
    with sr.Microphone() as source:
        while text == "":
            speech = recorder.listen(source, phrase_time_limit=10)
            try:
                text = recorder.recognize_google(speech)
                # Try to play song on spotify if play is heard
                try:
                    if text.index("play") == 0:
                        try:
                            request = text[5:].lower()
                            auth_manager = SpotifyOAuth(
                                "clientID",
                                "clientSecret",
                                "http://localhost:5173/callback",
                                scope="user-modify-playback-state",
                                cache_path="/home/matthewpi/Spotify/.cache",
                            )
                            sp = spotipy.Spotify(auth_manager=auth_manager)
                            songs = sp.search(request, 1, 0, "track")["tracks"]["items"]
                            for track in songs:
                                if "clean" not in track["name"].lower():
                                    song = track
                                    break
                            albums = sp.search(request, 1, 0, "playlist")["playlists"][
                                "items"
                            ]
                            for playlist in albums:
                                if "clean" not in playlist["name"].lower():
                                    album = playlist
                                    break
                            songName = song["name"].lower()
                            albumName = album["name"].lower()
                            songUri = song["uri"]
                            albumUri = album["uri"]
                            closestSong = SequenceMatcher(
                                None, request, songName
                            ).ratio()
                            closestAlbum = SequenceMatcher(
                                None, request, albumName
                            ).ratio()
                            if closestSong > closestAlbum:
                                sp.shuffle(
                                    False, "spotifyDeviceId"
                                )
                                sp.start_playback(
                                    "spotifyDeviceId",
                                    uris=[songUri],
                                    position_ms=0,
                                )
                                convertToSpeech("Playing " + songName)
                            else:
                                sp.start_playback(
                                    "spotifyDeviceId",
                                    context_uri=albumUri,
                                    position_ms=0,
                                )
                                sp.shuffle(
                                    True, "spotifyDeviceId"
                                )
                                sp.next_track(
                                    "spotifyDeviceId"
                                )
                                convertToSpeech("Playing " + albumName)
                            sp.repeat("off", "spotifyDeviceId")
                        except:
                            convertToSpeech("Unable to find song")
                        text = "cancel"
                        break
                except:
                    pass
                # Stop listening for prompt when "cancel" is heard
                if "cancel" in text.lower():
                    text = "cancel"
                    print("\033[KCancelled", end="\r")
                    convertToSpeech("Cancelling")
                    break
            except:
                print("\033[KSorry I didn't catch that, could you repeat?", end="\r")
                convertToSpeech("Sorry I didn't catch that, could you repeat?")
                pass
    return_dict[0] = text


def convertToSpeech(content):
    # Convert given text to speech
    textToSpeech = gTTS(text=content, tld="us", lang="en", slow=False)
    textToSpeech.save("output.mp3")
    say()


def say(file="output.mp3"):
    # Play output audio file
    os.system("mpg123 " + file)


def respond(responseSentences):
    # Play all sentences of a response
    fileNum = 0
    for sentence in responseSentences:
        textToSpeech = gTTS(text=sentence, tld="us", lang="en", slow=False)
        textToSpeech.save("output%s.mp3" % ("1" if fileNum % 2 == 1 else ""))
        talk = Process(
            target=say, args=("output%s.mp3" % ("1" if fileNum % 2 == 1 else ""),)
        )
        fileNum += 1
        try:
            processingTime = time.time() - processingStart
            time.sleep(fileLen - processingTime)
        except:
            pass
        processingStart = time.time()
        talk.start()
        audioFile = MP3("output%s.mp3" % ("1" if (fileNum - 1) % 2 == 1 else ""))
        fileLen = audioFile.info.length

def sendPrompt(messages):
    client = OpenAI(api_key="OpenAIKey")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    return response.choices[0].message.content

def postPromptResponse(messages, conversation, conversations):
    id = conversation["_id"]
    content = conversation["content"]
    messages = copy.deepcopy(content)
    messages[-1][1] = "(If your answer contains a math equation format it in LateX)\n" + messages[-1][1]
    # Convert content to openai format
    messages = [{"role": "assistant" if message[0] == "AI" else "user", "content": message[1]} for message in messages]
    updated_content = copy.deepcopy(content)
    updated_content.append(["AI", "..."])
    conversations.update_one({"_id": id}, {"$set": {"content": updated_content}})
    # Send prompt to OpenAI
    response = sendPrompt(messages)
    updated_content = copy.deepcopy(content)
    updated_content.append(["AI", response])
    conversations.update_one({"_id": id}, {"$set": {"content": updated_content}})

def findRemotePrompts(sp, pixels, lightsUsageStatus, sleepLightsState):
    # Remote conversation memory
    remoteMessages=[]
    # Connect to MongoDB
    db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
    conversations = db["conversations"]
    # Query for finding conversations with unanswered prompts
    pipeline = [
        {"$addFields": {
            "last_message_owner": {"$arrayElemAt": [{"$arrayElemAt": ["$content", -1]}, 0]}
        }},
        {"$match": {"last_message_owner": "User"}}
    ]
    # Search for unanswered prompts
    while True:
        # Get all prompts and corresponding responses
        conversationQueue = None
        while conversationQueue == None:
            try:
                conversationQueue = list(conversations.aggregate(pipeline))
            except:
                db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                conversations = db["conversations"]
                conversationQueue = list(conversations.aggregate(pipeline))
        try:
            # Check if each prompt has a response given
            threads = []
            for conversation in conversationQueue:
                t = Thread(target=postPromptResponse, args=(remoteMessages, conversation, conversations))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
        except:
            pass
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


def buttonSound():
    os.system("mpg123 button_sound.mp3")


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


def buttonPlayer(buttonPresses):
    while True:
        counter = 0
        while not buttonPresses.empty():
            counter += 1
            if counter > 3:
                while not buttonPresses.empty():
                    buttonPresses.get()
                break
            buttonPresses.get()
            click = Process(target=buttonSound())
            click.start()


def spotifyAuth():
    while True:
        time.sleep(60)
        auth_manager = SpotifyOAuth(
            "clientID",
            "clientSecret",
            "http://localhost:5173/callback",
            scope="user-modify-playback-state",
            cache_path="/home/matthewpi/Spotify/.cache",
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)


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
    db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
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
                db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
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


def splitIntoSentences(text: str) -> list[str]:
    alphabets = "([A-Za-z])"
    prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
    suffixes = "(Inc|Ltd|Jr|Sr|Co)"
    starters = "(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
    acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
    websites = "[.](com|net|org|io|gov|edu|me)"
    digits = "([0-9])"
    multiple_dots = r"\.{2,}"
    text = " " + text + "  "
    text = text.replace("\n", " ")
    text = re.sub(prefixes, "\\1<prd>", text)
    text = re.sub(websites, "<prd>\\1", text)
    text = re.sub(digits + "[.]" + digits, "\\1<prd>\\2", text)
    text = re.sub(
        multiple_dots, lambda match: "<prd>" * len(match.group(0)) + "<stop>", text
    )
    if "Ph.D" in text:
        text = text.replace("Ph.D.", "Ph<prd>D<prd>")
    text = re.sub("\s" + alphabets + "[.] ", " \\1<prd> ", text)
    text = re.sub(acronyms + " " + starters, "\\1<stop> \\2", text)
    text = re.sub(
        alphabets + "[.]" + alphabets + "[.]" + alphabets + "[.]",
        "\\1<prd>\\2<prd>\\3<prd>",
        text,
    )
    text = re.sub(alphabets + "[.]" + alphabets + "[.]", "\\1<prd>\\2<prd>", text)
    text = re.sub(" " + suffixes + "[.] " + starters, " \\1<stop> \\2", text)
    text = re.sub(" " + suffixes + "[.]", " \\1<prd>", text)
    text = re.sub(" " + alphabets + "[.]", " \\1<prd>", text)
    if "" in text:
        text = text.replace(".", ".")
    if '"' in text:
        text = text.replace('."', '".')
    if "!" in text:
        text = text.replace('!"', '"!')
    if "?" in text:
        text = text.replace('?"', '"?')
    text = text.replace(".", ".<stop>")
    text = text.replace("?", "?<stop>")
    text = text.replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    sentences = text.split("<stop>")
    sentences = [s.strip() for s in sentences]
    if sentences and not sentences[-1]:
        sentences = sentences[:-1]
    return sentences


def manageSongRequests(sp):
    lastCall = time.time()
    db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
    stateCol = db["spotifies"]
    previousSearch = ''
    search = ''
    requestSong = ['', '']
    previousPlayState = 0
    while True:
        state = None
        while state == None:
            try:
                state = stateCol.find_one()
            except:
                db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                stateCol = db["spotifies"]
                state = stateCol.find_one()
        
        # Get search results for the user's input
        previousSearch = search
        search = state['input']
        if search != '' and search != previousSearch:
            try:
                searchResults = sp.search(search, 3, 0, "track,playlist")
                playlists = searchResults['playlists']['items']
                formattedPlaylists = []
                for playlist in playlists:
                    formattedPlaylists.append([playlist['name'], playlist['uri'], playlist['images'][0]['url']])
                
                tracks = searchResults['tracks']['items']
                formattedTracks = []
                for track in tracks:
                    formattedTracks.append([track['name'], track['uri'], track['album']['images'][0]['url']])
                
                searchResults = formattedPlaylists + formattedTracks
                stateCol.update_one(state, {'$set': {'searchResults': searchResults}})
            except:
                pass
        elif search == '' and search != previousSearch:
            stateCol.update_one(state, {'$set': {'searchResults': []}})
        
        # Start playing the requested song
        requestSong = state['songRequest']
        if requestSong[0] != '':
            try:
                stateCol.update_one(state, {'$set': {'currentSong': requestSong, 'songRequest': ['', ''], 'playState': 1, 'playControl': 0}})
                if 'playlist' in requestSong[1]:
                    sp.start_playback(
                        "spotifyDeviceId",
                        context_uri=requestSong[1],
                        position_ms=0,
                    )
                    sp.shuffle(True, "spotifyDeviceId")
                    sp.next_track("spotifyDeviceId")
                elif 'track' in requestSong[1]:
                    sp.shuffle(False, "spotifyDeviceId")
                    sp.start_playback(
                        "spotifyDeviceId",
                        uris=[requestSong[1]],
                        position_ms=0,
                    )
            except:
                pass
        
        currentSong = state['currentSong']
        if currentSong[0] != '' and time.time() - lastCall > 0.5:
            lastCall = time.time()
            try:
                song = sp.currently_playing()["item"]
                uri = song["uri"]
                name = song["name"]
                if uri != currentSong[1]:
                    stateCol.update_one(state, {'$set': {'currentSong': [name, uri]}})
            except:
                pass
            
        # Pause / Resume
        requestPlayState = state['playState']
        if requestPlayState != previousPlayState:
            previousPlayState = requestPlayState
            try:
                if sp.currently_playing()["is_playing"] and (requestPlayState == 0):
                    sp.pause_playback(
                        "spotifyDeviceId"
                    )
                elif not sp.currently_playing()["is_playing"] and (requestPlayState == 1):
                    sp.start_playback(
                        "spotifyDeviceId"
                    )
            except:
                pass
        
        # Prev / Next
        requestControlPlayState = state['controlPlayState']
        if requestControlPlayState != 0:
            if requestControlPlayState == 1:
                try:
                    sp.next_track(
                        "spotifyDeviceId"
                    )
                    sp.start_playback(
                        "spotifyDeviceId"
                    )
                    stateCol.update_one(state, {'$set': {'controlPlayState': 0, 'playState': 1}})
                except:
                    pass
            elif requestControlPlayState == -1:
                try:
                    sp.previous_track(
                        "spotifyDeviceId"
                    )
                    sp.start_playback(
                        "spotifyDeviceId"
                    )
                    stateCol.update_one(state, {'$set': {'controlPlayState': 0, 'playState': 1}})
                except:
                    pass


if __name__ == "__main__":
    # Setup Caddy
    os.system("caddy stop")
    os.system("sudo systemctl restart caddy")
    # Connect to MongoDB
    db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
    stateCol = db["spotifies"]
    # List of all multiprocesses
    processes = []
    # Set up action button
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Action button
    GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Volume down button
    GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Volume up button
    # Start action button audio feedback
    buttonPresses = Queue()
    actionButtonCounter = Process(target=buttonCounter, args=(buttonPresses,))
    processes.append(actionButtonCounter)
    actionButtonPlayer = Process(target=buttonPlayer, args=(buttonPresses,))
    processes.append(actionButtonPlayer)
    actionButtonCounter.start()
    actionButtonPlayer.start()
    # Lights
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
    # Setup Spotify
    auth_manager = SpotifyOAuth(
        "clientID",
        "clientSecret",
        "http://localhost:5173/callback",
        scope="user-modify-playback-state",
        cache_path="/home/matthewpi/Spotify/.cache",
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    spAuth = Process(target=spotifyAuth)
    spAuth.start()
    # Start checking for remote prompts
    remote = Process(
        target=findRemotePrompts, args=(sp, pixels, lightsUsageStatus, sleepLightsState)
    )
    processes.append(remote)
    remote.start()
    # Volume control requirements
    audio = alsaaudio.Mixer("Speaker")
    audio.setvolume(
        round(math.log((50) * 25 / 19) / 0.0488)
    )  # Default volume level to 50
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
    processes.append(controlVol)
    controlVol.start()
    # Set up spotify manager
    spotifyManager = Process(target=manageSongRequests, args=(sp))
    processes.append(spotifyManager)
    spotifyManager.start()
    # Set up microphone input
    recorder = sr.Recognizer()
    # Conversation memory
    messages = []
    # Set name that chatbot listens for
    name = "Siri"
    print("Hi, my name is " + name)
    onOff = Queue()
    lights = Process(
        target=lightsControl, args=(pixels, onOff, lightsUsageStatus, sleepLightsState)
    )
    processes.append(lights)
    lightsUsageStatus.put(True)
    lights.start()
    convertToSpeech("Hi my name is " + name)
    onOff.put("lightsOff")
    lightsUsageStatus.put(False)

    while True:
        # Wait for action button to reset before continuing
        while GPIO.input(16) == GPIO.HIGH:
            time.sleep(1)
        # Listen for wakeword
        manager = Manager()
        return_dict = manager.dict()
        listen = Process(
            target=listenForKeyWord,
            args=(
                recorder,
                audio,
                pixels,
                name,
                messages,
                volLevelVerbal,
                volLevelButton,
                volQueue,
                return_dict,
                sleepLightsState,
            ),
        )
        processes.append(listen)
        listen.start()
        # Wake on action button
        physicalInput = False
        awaking = False
        while listen.is_alive():
            if GPIO.input(16) == GPIO.HIGH:
                skipInput = False
                # Check for sleep request
                tryingToSleep = False
                holdStart = time.time()
                while (
                    GPIO.input(16) == GPIO.HIGH
                    and GPIO.input(23) != GPIO.HIGH
                    and GPIO.input(24) != GPIO.HIGH
                ):
                    if time.time() - holdStart >= 1:
                        tryingToSleep = True
                    if time.time() - holdStart >= 2:
                        # Turn lights red to signify sleeping
                        listen.terminate()
                        checkSleep = False
                        print("Sleeping . . .")
                        sleep = Process(target=convertToSpeech, args=("Sleeping",))
                        processes.append(sleep)
                        sleep.start()
                        lightsUsageStatus.put("sleep")
                        sleepLightsOn = Process(
                            target=sleepLights,
                            args=(pixels, sleepLightsState, currentColor),
                        )
                        processes.append(sleepLightsOn)
                        sleepLightsOn.start()
                        sleep = True
                        while GPIO.input(16) == GPIO.HIGH:
                            time.sleep(0.1)
                        # Start sleeping
                        while sleep:
                            if GPIO.input(16) == GPIO.HIGH:
                                tryingToWake = False
                                # Check for awake request
                                if (
                                    GPIO.input(16) == GPIO.HIGH
                                    and GPIO.input(23) != GPIO.HIGH
                                    and GPIO.input(24) != GPIO.HIGH
                                ):
                                    holdStart = time.time()
                                    awake = True
                                    while time.time() - holdStart < 2:
                                        if time.time() - holdStart >= 1:
                                            tryingToWake = True
                                        if GPIO.input(16) != GPIO.HIGH:
                                            awake = False
                                            break
                                    if awake:
                                        sleepLightsState.put("off")
                                        for i in range(pixels.numPixels())[::-1]:
                                            pixels.setPixelColor(i, Color(0, 0, 0))
                                            pixels.show()
                                            time.sleep(5 / 1000.0)
                                        # Turn on lights briefly to signify awake
                                        sleep = False
                                        awaking = True
                                        print("Awake")
                                        awake = Process(
                                            target=convertToSpeech, args=("Awake",)
                                        )
                                        onOff = Queue()
                                        lights = Process(
                                            target=lightsControl,
                                            args=(
                                                pixels,
                                                onOff,
                                                lightsUsageStatus,
                                                sleepLightsState,
                                            ),
                                        )
                                        processes.append(lights)
                                        lights.start()
                                        awake.start()
                                    while GPIO.input(16) == GPIO.HIGH:
                                        time.sleep(0.1)
                                    onOff.put("lightsOff")
                                if not tryingToWake:
                                    double = False
                                    triple = False
                                    doubleClickStart = time.time()
                                    while time.time() - doubleClickStart < 0.5:
                                        time.sleep(0.1)
                                        if GPIO.input(16) == GPIO.HIGH:
                                            double = True
                                            break
                                    while GPIO.input(16) == GPIO.HIGH:
                                        time.sleep(0.1)
                                    tripleClickStart = time.time()
                                    while time.time() - doubleClickStart < 0.5:
                                        time.sleep(0.1)
                                        if GPIO.input(16) == GPIO.HIGH:
                                            triple = True
                                            break
                                    # Skip if triple clicked
                                    if triple:
                                        # auth_manager = SpotifyOAuth(
                                        #     "clientID",
                                        #     "clientSecret",
                                        #     "http://localhost:5173/callback",
                                        #     scope="user-modify-playback-state",
                                        #     cache_path="/home/matthewpi/Spotify/.cache",
                                        # )
                                        # sp = spotipy.Spotify(auth_manager=auth_manager)
                                        # try:
                                        #     sp.next_track(
                                        #         "spotifyDeviceId"
                                        #     )
                                        # except:
                                        #     pass
                                        db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                                        stateCol = db["spotifies"]
                                        state = stateCol.find_one()
                                        stateCol.update_one(state, {'$set': {'controlPlayState': 1}})
                                        print("Skipping song . . .")
                                    # Pause/Resume if double clicked
                                    elif double:
                                        try:
                                            auth_manager = SpotifyOAuth(
                                                "clientID",
                                                "clientSecret",
                                                "http://localhost:5173/callback",
                                                scope="user-modify-playback-state",
                                                cache_path="/home/matthewpi/Spotify/.cache",
                                            )
                                            sp = spotipy.Spotify(
                                                auth_manager=auth_manager
                                            )
                                            if sp.currently_playing()["is_playing"]:
                                                db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                                                stateCol = db["spotifies"]
                                                state = stateCol.find_one()
                                                stateCol.update_one(state, {'$set': {'playState': 0}})
                                                # auth_manager = SpotifyOAuth(
                                                #     "clientID",
                                                #     "clientSecret",
                                                #     "http://localhost:5173/callback",
                                                #     scope="user-modify-playback-state",
                                                #     cache_path="/home/matthewpi/Spotify/.cache",
                                                # )
                                                # sp = spotipy.Spotify(
                                                #     auth_manager=auth_manager
                                                # )
                                                # sp.pause_playback(
                                                #     "spotifyDeviceId"
                                                # )
                                                print("Pausing . . .")
                                            else:
                                                db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                                                stateCol = db["spotifies"]
                                                state = stateCol.find_one()
                                                stateCol.update_one(state, {'$set': {'playState': 1}})
                                                # auth_manager = SpotifyOAuth(
                                                #     "clientID",
                                                #     "clientSecret",
                                                #     "http://localhost:5173/callback",
                                                #     scope="user-modify-playback-state",
                                                #     cache_path="/home/matthewpi/Spotify/.cache",
                                                # )
                                                # sp = spotipy.Spotify(
                                                #     auth_manager=auth_manager
                                                # )
                                                # sp.start_playback(
                                                #     "spotifyDeviceId"
                                                # )
                                                print("Resuming . . .")
                                        except:
                                            pass
                        while GPIO.input(16) == GPIO.HIGH:
                            time.sleep(0.1)
                        onOff.put("lightsOff")
                        skipInput = True
                if not tryingToSleep:
                    double = False
                    triple = False
                    doubleClickStart = time.time()
                    while time.time() - doubleClickStart < 0.5:
                        time.sleep(0.1)
                        if GPIO.input(16) == GPIO.HIGH:
                            double = True
                            break
                    while GPIO.input(16) == GPIO.HIGH:
                        time.sleep(0.1)
                    tripleClickStart = time.time()
                    while time.time() - doubleClickStart < 0.5:
                        time.sleep(0.1)
                        if GPIO.input(16) == GPIO.HIGH:
                            triple = True
                            break
                    # Skip if triple clicked
                    if triple:
                        # auth_manager = SpotifyOAuth(
                        #     "clientID",
                        #     "clientSecret",
                        #     "http://localhost:5173/callback",
                        #     scope="user-modify-playback-state",
                        #     cache_path="/home/matthewpi/Spotify/.cache",
                        # )
                        # sp = spotipy.Spotify(auth_manager=auth_manager)
                        # try:
                        #     sp.next_track("spotifyDeviceId")
                        # except:
                        #     pass
                        db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                        stateCol = db["spotifies"]
                        state = stateCol.find_one()
                        stateCol.update_one(state, {'$set': {'controlPlayState': 1}})
                        print("Skipping song . . .")
                    # Pause/Resume if double clicked
                    elif double:
                        try:
                            auth_manager = SpotifyOAuth(
                                "clientID",
                                "clientSecret",
                                "http://localhost:5173/callback",
                                scope="user-modify-playback-state",
                                cache_path="/home/matthewpi/Spotify/.cache",
                            )
                            sp = spotipy.Spotify(auth_manager=auth_manager)
                            if sp.currently_playing()["is_playing"]:
                                db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                                stateCol = db["spotifies"]
                                state = stateCol.find_one()
                                stateCol.update_one(state, {'$set': {'playState': 0}})
                                # auth_manager = SpotifyOAuth(
                                #     "clientID",
                                #     "clientSecret",
                                #     "http://localhost:5173/callback",
                                #     scope="user-modify-playback-state",
                                #     cache_path="/home/matthewpi/Spotify/.cache",
                                # )
                                # sp = spotipy.Spotify(auth_manager=auth_manager)
                                # try:
                                #     sp.pause_playback(
                                #         "spotifyDeviceId"
                                #     )
                                # except:
                                #     pass
                                print("Pausing . . .")
                            else:
                                db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                                stateCol = db["spotifies"]
                                state = stateCol.find_one()
                                stateCol.update_one(state, {'$set': {'playState': 1}})
                                # auth_manager = SpotifyOAuth(
                                #     "clientID",
                                #     "clientSecret",
                                #     "http://localhost:5173/callback",
                                #     scope="user-modify-playback-state",
                                #     cache_path="/home/matthewpi/Spotify/.cache",
                                # )
                                # sp = spotipy.Spotify(auth_manager=auth_manager)
                                # try:
                                #     sp.start_playback(
                                #         "spotifyDeviceId"
                                #     )
                                # except:
                                #     pass
                                print("Resuming . . .")
                        except:
                            pass
                    elif not skipInput:
                        listen.terminate()
                        physicalInput = True
                        break
        # Check if the user wants to terminate the program
        try:
            if awaking:
                continue
        except:
            pass
        if not physicalInput:
            listen.join()
            messages = return_dict.values()[0]
        # Temporarily pause any songs currently playing to listen to user
        # Connect to MongoDB
        state = None
        while state == None:
            try:
                state = stateCol.find_one()
            except:
                db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                stateCol = db["spotifies"]
                state = stateCol.find_one()
        originalState = state['playState'] == 1
        try:
            stateCol.update_one(state, {'$set': {'playState': 0}})
        except:
            pass
        # Turn on lights to signify listening
        onOff = Queue()
        lights = Process(
            target=lightsControl,
            args=(pixels, onOff, lightsUsageStatus, sleepLightsState),
        )
        processes.append(lights)
        lights.start()

        # Listen for a prompt
        manager = Manager()
        return_dict = manager.dict()
        listenPrompt = Process(target=listenForPrompt, args=(recorder, sp, return_dict))
        processes.append(listenPrompt)
        listenPrompt.start()
        print("\033[KI'm listening . . .", end="\r")
        convertToSpeech("I'm listening")
        # Cancel on action button
        cancelled = False
        while listenPrompt.is_alive():
            if GPIO.input(16) == GPIO.HIGH:
                listenPrompt.terminate()
                print("\033[KCancelled", end="\r")
                convertToSpeech("Cancelling")
                cancelled = True
                break
        # Turn lights off to signify prompt recieved and generating response
        onOff.put("lightsOff")
        # Don't respond if chat cancelled through action button
        if cancelled:
            # Resume any songs that were paused while listening for prompt
            # auth_manager = SpotifyOAuth(
            #     "clientID",
            #     "clientSecret",
            #     "http://localhost:5173/callback",
            #     scope="user-modify-playback-state",
            #     cache_path="/home/matthewpi/Spotify/.cache",
            # )
            # sp = spotipy.Spotify(auth_manager=auth_manager)
            if originalState:
                state = None
                while state == None:
                    try:
                        state = stateCol.find_one()
                    except:
                        db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                        stateCol = db["spotifies"]
                        state = stateCol.find_one()
                try:
                    stateCol.update_one(state, {'$set': {'playState': 1}})
                except:
                    pass
            continue
        # Retrieve prompt in text form
        listenPrompt.join()
        text = return_dict.values()[0]
        # Don't respond if chat cancelled verbally
        if text == "cancel":
            continue
        print("\033[KMe: " + text)

        # Send prompt to ChatGPT
        client = OpenAI(api_key="OpenAIKey")
        messages.append({"role": "user", "content": text})
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", messages=messages
        )
        responseText = response.choices[0].message.content
        # Add response to conversation memory
        messages.append(response.choices[0].message)
        print(name[0].upper() + name[1:] + ": " + responseText)

        # Split response into sentences
        responseSentences = splitIntoSentences(responseText)
        # Turn lights on to signify start of response
        onOff = Queue()
        lights = Process(
            target=lightsControl,
            args=(pixels, onOff, lightsUsageStatus, sleepLightsState),
        )
        processes.append(lights)
        lights.start()
        # Start responding
        response = Process(target=respond, args=(responseSentences,))
        processes.append(response)
        response.start()
        # Stop responding on action button
        while response.is_alive():
            if GPIO.input(16) == GPIO.HIGH:
                response.terminate()
                os.system("killall mpg123")
                break
        onOff.put("lightsOff")
        # Resume any songs that were paused while listening for prompt
        # auth_manager = SpotifyOAuth(
        #     "clientID",
        #     "clientSecret",
        #     "http://localhost:5173/callback",
        #     scope="user-modify-playback-state",
        #     cache_path="/home/matthewpi/Spotify/.cache",
        # )
        # sp = spotipy.Spotify(auth_manager=auth_manager)
        if originalState:
            state = None
            while state == None:
                try:
                    state = stateCol.find_one()
                except:
                    db = MongoClient("MongoDBConnectionString", tlsCAFile=certifi.where())['test']
                    stateCol = db["spotifies"]
                    state = stateCol.find_one()
            try:
                stateCol.update_one(state, {'$set': {'playState': 1}})
            except:
                pass