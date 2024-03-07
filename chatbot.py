import os
import re
import math
import time
import spotipy
import gspread
import alsaaudio
import sounddevice
import numpy as np
from gtts import gTTS
from rpi_ws281x import *
import RPi.GPIO as GPIO
from openai import OpenAI
from mutagen.mp3 import MP3
from spotipy.oauth2 import *
import speech_recognition as sr
from difflib import SequenceMatcher
from multiprocessing import Manager, Process, Queue
from oauth2client.service_account import ServiceAccountCredentials


class Google_Sheet:
    def __init__(self, sheet):
        self.sheet = sheet

    def usheet(self, sheet):
        self.sheet = sheet


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
            # Terminate program when "shut down" is heard
            elif "shut off" in text.lower() or "shutoff" in text.lower():
                print("Shutting off . . .")
                onOff = Queue()
                lights = Process(
                    target=lightsControl,
                    args=(pixels, onOff, lightsUsageStatus, sleepLightsState),
                )
                processes.append(lights)
                lights.start()
                convertToSpeech("Shutting off")
                onOff.put("lightsOff")
                lights.join()
                print("\033c", end="\r")
                messages = "shut off"
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
                                "client_id",
                                "client_secret",
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
                                    False, "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                sp.start_playback(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f",
                                    uris=[songUri],
                                    position_ms=0,
                                )
                                convertToSpeech("Playing " + songName)
                            else:
                                sp.start_playback(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f",
                                    context_uri=albumUri,
                                    position_ms=0,
                                )
                                sp.shuffle(
                                    True, "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                sp.next_track(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                convertToSpeech("Playing " + albumName)
                            sp.repeat("off", "06c55ec62f492429c6ebbf38fc814d5a7382386f")
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


def findRemotePrompts(sp, pixels, lightsUsageStatus, sleepLightsState):
    # Remote conversation memory
    remoteMessages = []
    # Search for unanswered prompts
    while True:
        try:
            # Connect to google sheet
            promptSheet = Google_Sheet(None)
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                "key.json", scopes
            )
            file = gspread.authorize(credentials)
            promptSheet.usheet(file.open(title="Prompts"))
            prompts = promptSheet.sheet.get_worksheet(0)
            # Get all prompts and corresponding responses
            colPrompts = prompts.col_values(1)
            colResponses = prompts.col_values(2)
            # Check if each prompt has a response given
            for i in range(len(colPrompts)):
                try:
                    promptCell = colPrompts[i]
                except:
                    promptCell = ""
                try:
                    responseCell = colResponses[i]
                except:
                    responseCell = ""
                # If a prompt does not have a response then provide a response
                if promptCell != "" and responseCell == "":
                    # Reset conversation memory
                    if promptCell.lower() == "reset":
                        prompts.update_cell(i + 1, 2, "Conversation Reset")
                        remoteMessages = []
                    # Clear chat terminal
                    elif promptCell.lower() == "clear":
                        rowsToClear = prompts.row_count - 3
                        prompts.add_rows(99)
                        prompts.delete_rows(2, 2 + rowsToClear)
                        prompts.format(
                            "A2:C100",
                            {"verticalAlignment": "TOP", "wrapStrategy": "WRAP"},
                        )
                    # Reset conversation memory and clear chat terminal
                    elif promptCell.lower() == "reset and clear":
                        remoteMessages = []
                        rowsToClear = prompts.row_count - 3
                        prompts.add_rows(99)
                        prompts.delete_rows(2, 2 + rowsToClear)
                        prompts.format(
                            "A2:C100",
                            {"verticalAlignment": "TOP", "wrapStrategy": "WRAP"},
                        )
                    # Shutdown
                    elif promptCell.lower() == "shut off":
                        prompts.update_cell(i + 1, 2, "Shutting Off")
                        sleepLightsState.put("off")
                        clearLights(pixels)
                        print("\033c", end="\r")
                        os.system("sudo pkill -9 -f chatbot.py")
                    # Reboot
                    elif promptCell.lower() == "reboot":
                        prompts.update_cell(i + 1, 2, "Rebooting")
                        sleepLightsState.put("off")
                        clearLights(pixels)
                        print("\033c", end="\r")
                        os.system("sudo reboot")
                    # Play a song
                    elif promptCell.lower()[:4] == "play":
                        prompts.update_cell(i + 1, 2, "Searching . . .")
                        try:
                            if "play song" in promptCell.lower():
                                request = promptCell.lower()[9:]
                            elif "play album" in promptCell.lower():
                                request = promptCell.lower()[10:]
                            else:
                                request = promptCell.lower()[4:]
                            auth_manager = SpotifyOAuth(
                                "client_id",
                                "client_secret",
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
                            songName = song["name"]
                            albumName = album["name"]
                            songUri = song["uri"]
                            albumUri = album["uri"]
                            closestSong = SequenceMatcher(
                                None, request, songName.lower()
                            ).ratio()
                            closestAlbum = SequenceMatcher(
                                None, request, albumName.lower()
                            ).ratio()
                            if "play song" in promptCell.lower():
                                sp.shuffle(
                                    False, "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                sp.start_playback(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f",
                                    uris=[songUri],
                                    position_ms=0,
                                )
                                prompts.update_cell(i + 1, 2, "Playing " + songName)
                            elif "play album" in promptCell.lower():
                                sp.start_playback(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f",
                                    context_uri=albumUri,
                                    position_ms=0,
                                )
                                sp.shuffle(
                                    True, "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                sp.next_track(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                prompts.update_cell(i + 1, 2, "Playing " + albumName)
                            elif closestSong > closestAlbum:
                                sp.shuffle(
                                    False, "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                sp.start_playback(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f",
                                    uris=[songUri],
                                    position_ms=0,
                                )
                                prompts.update_cell(i + 1, 2, "Playing " + songName)
                            else:
                                sp.start_playback(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f",
                                    context_uri=albumUri,
                                    position_ms=0,
                                )
                                sp.shuffle(
                                    True, "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                sp.next_track(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                prompts.update_cell(i + 1, 2, "Playing " + albumName)
                            sp.repeat("off", "06c55ec62f492429c6ebbf38fc814d5a7382386f")
                        except:
                            prompts.update_cell(i + 1, 2, "Unable to find song")
                    # Pause currently playing song
                    elif promptCell.lower() == "pause":
                        auth_manager = SpotifyOAuth(
                            "client_id",
                            "client_secret",
                            "http://localhost:5173/callback",
                            scope="user-modify-playback-state",
                            cache_path="/home/matthewpi/Spotify/.cache",
                        )
                        sp = spotipy.Spotify(auth_manager=auth_manager)
                        try:
                            sp.pause_playback(
                                "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                            )
                        except:
                            pass
                        prompts.update_cell(i + 1, 2, "Paused")
                    # Resume current song
                    elif promptCell.lower() == "resume":
                        auth_manager = SpotifyOAuth(
                            "client_id",
                            "client_secret",
                            "http://localhost:5173/callback",
                            scope="user-modify-playback-state",
                            cache_path="/home/matthewpi/Spotify/.cache",
                        )
                        sp = spotipy.Spotify(auth_manager=auth_manager)
                        try:
                            sp.start_playback(
                                "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                            )
                        except:
                            pass
                        prompts.update_cell(i + 1, 2, "Resumed")
                    # Skip current song
                    elif promptCell.lower() == "next" or promptCell.lower() == "skip":
                        auth_manager = SpotifyOAuth(
                            "client_id",
                            "client_secret",
                            "http://localhost:5173/callback",
                            scope="user-modify-playback-state",
                            cache_path="/home/matthewpi/Spotify/.cache",
                        )
                        sp = spotipy.Spotify(auth_manager=auth_manager)
                        try:
                            sp.next_track("06c55ec62f492429c6ebbf38fc814d5a7382386f")
                        except:
                            pass
                        prompts.update_cell(i + 1, 2, "Skipped to next song")
                    # Return to previous song
                    elif (
                        promptCell.lower() == "back" or promptCell.lower() == "previous"
                    ):
                        auth_manager = SpotifyOAuth(
                            "client_id",
                            "client_secret",
                            "http://localhost:5173/callback",
                            scope="user-modify-playback-state",
                            cache_path="/home/matthewpi/Spotify/.cache",
                        )
                        sp = spotipy.Spotify(auth_manager=auth_manager)
                        if sp.current_playback()["progress_ms"] > 3000:
                            try:
                                sp.previous_track(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                                sp.previous_track(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                            except:
                                pass
                        else:
                            try:
                                sp.previous_track(
                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                )
                            except:
                                pass
                        prompts.update_cell(i + 1, 2, "Returned to previous song")
                    # Read prompt response
                    elif promptCell.lower()[-5:] == "-read":
                        promptCell = promptCell[:-5]
                        prompts.update_cell(i + 1, 2, "Responding . . .")
                        onOff = Queue()
                        lights = Process(
                            target=lightsControl,
                            args=(pixels, onOff, lightsUsageStatus, sleepLightsState),
                        )
                        sleepLightsState.put("pause")
                        lights.start()
                        remotePrompt = Process(
                            target=convertToSpeech,
                            args=("Remote prompt recieved: " + promptCell,),
                        )
                        remotePrompt.start()
                        client = OpenAI(api_key="open_ai_key")
                        remoteMessages.append({"role": "user", "content": promptCell})
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo", messages=remoteMessages
                        )
                        responseText = response.choices[0].message.content
                        # Add response to conversation memory
                        remoteMessages.append(response.choices[0].message)
                        # Insert response into appropriate response cell
                        prompts.format(
                            "A2:C100",
                            {"verticalAlignment": "TOP", "wrapStrategy": "WRAP"},
                        )
                        prompts.update_cell(i + 1, 2, responseText)
                        # Report the response
                        responseSentences = splitIntoSentences(responseText)
                        remoteRespond = Process(
                            target=respond, args=(responseSentences,)
                        )
                        remoteRespond.start()
                        # While the reponse is playing, check if the user wants to stop the audio
                        while remoteRespond.is_alive():
                            if GPIO.input(16) == GPIO.HIGH:
                                remoteRespond.terminate()
                                os.system("killall mpg123")
                                break
                        onOff.put("lightsOff")
                        sleepLightsState.put(False)
                    # Send prompt to ChatGPT and report the response
                    else:
                        prompts.update_cell(i + 1, 2, "Responding . . .")
                        client = OpenAI(api_key="open_ai_key")
                        remoteMessages.append({"role": "user", "content": promptCell})
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo", messages=remoteMessages
                        )
                        responseText = response.choices[0].message.content
                        # Add response to conversation memory
                        remoteMessages.append(response.choices[0].message)
                        # Insert response into appropriate response cell
                        prompts.format(
                            "A2:C100",
                            {"verticalAlignment": "TOP", "wrapStrategy": "WRAP"},
                        )
                        prompts.update_cell(i + 1, 2, responseText)
            time.sleep(3)
        except:
            time.sleep(3)


def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
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
            "client_id",
            "client_secret",
            "http://localhost:5173/callback",
            scope="user-modify-playback-state",
            cache_path="/home/matthewpi/Spotify/.cache",
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)


def volLights(pixels, volQueue, lightsUsageStatus, sleepLightsState, currentColor):
    lastRequest = time.time()
    volLightsOn = False
    while True:
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
    currentVol = -1
    volLightsProcess = Process(
        target=volLights,
        args=(pixels, volQueue, lightsUsageStatus, sleepLightsState, currentColor),
    )
    volLightsProcess.start()
    while True:
        if not volLevelVerbal.empty():
            currentVol = volLevelVerbal.get()
        # Increase volume
        if GPIO.input(23) == GPIO.HIGH and GPIO.input(24) == GPIO.LOW:
            try:
                volLightsOff.terminate()
            except:
                pass
            if currentVol == -1:
                currentVol = (
                    round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5) * 5
                )
            if round(currentVol) <= 95:
                try:
                    audio.setvolume(
                        round(math.log((currentVol + 5) * 25 / 19) / 0.0488)
                    )
                    volLevelVerbal.put(currentVol + 5)
                    volLevelButton.put(currentVol + 5)
                except:
                    audio.setvolume(100)
            currentVol = currentVol + 5 if (currentVol + 5 < 100) else 100
            volQueue.put(currentVol)
            holdStart = time.time()
            while GPIO.input(23) == GPIO.HIGH and GPIO.input(24) == GPIO.LOW:
                time.sleep(0.1)
                if time.time() - holdStart >= 1:
                    try:
                        volLightsOff.terminate()
                    except:
                        pass
                    if currentVol == -1:
                        currentVol = (
                            round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5)
                            * 5
                        )
                    if round(currentVol) <= 95:
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
                    volQueue.put(currentVol)
        # Decrease volume
        elif GPIO.input(23) == GPIO.LOW and GPIO.input(24) == GPIO.HIGH:
            try:
                volLightsOff.terminate()
            except:
                pass
            if currentVol == -1:
                currentVol = (
                    round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5) * 5
                )
            if round(currentVol) >= 5:
                try:
                    audio.setvolume(
                        round(math.log((currentVol - 5) * 25 / 19) / 0.0488)
                    )
                    volLevelVerbal.put(currentVol - 5)
                    volLevelButton.put(currentVol - 5)
                except:
                    audio.setvolume(0)
            currentVol = currentVol - 5 if (currentVol - 5 > 0) else 0
            volQueue.put(currentVol)
            holdStart = time.time()
            while GPIO.input(23) == GPIO.HIGH or GPIO.input(24) == GPIO.HIGH:
                time.sleep(0.1)
                if time.time() - holdStart >= 1:
                    try:
                        volLightsOff.terminate()
                    except:
                        pass
                    if currentVol == -1:
                        currentVol = (
                            round(0.76 * pow(math.e, 0.0488 * audio.getvolume()[0]) / 5)
                            * 5
                        )
                    if round(currentVol) >= 5:
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
                    volQueue.put(currentVol)


def volLightsCooldown(pixels, lightsInUse, sleepLightsState, currentColor):
    if not lightsInUse:
        for i in range(pixels.numPixels())[::-1]:
            pixels.setPixelColor(i, Color(0, 0, 0))
            pixels.show()
            time.sleep(5 / 1000.0)
    else:
        while not currentColor.empty():
            currentShade = currentColor.get()
        for i in range(pixels.numPixels())[::-1]:
            pixels.setPixelColor(i, currentShade)
            pixels.show()
            time.sleep(5 / 1000.0)
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
    if "”" in text:
        text = text.replace(".”", "”.")
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


if __name__ == "__main__":
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
        "client_id",
        "client_secret",
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
    lights.start()
    convertToSpeech("Hi my name is " + name)
    onOff.put("lightsOff")

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
                # Reboot if action and volume buttons are all pressed together
                if (
                    GPIO.input(16) == GPIO.HIGH
                    and GPIO.input(23) == GPIO.HIGH
                    and GPIO.input(24) == GPIO.HIGH
                ):
                    cancel = False
                    rebootStart = time.time()
                    while time.time() - rebootStart < 3:
                        time.sleep(0.1)
                        if (
                            GPIO.input(16) != GPIO.HIGH
                            and GPIO.input(23) != GPIO.HIGH
                            and GPIO.input(24) != GPIO.HIGH
                        ):
                            cancel = True
                            break
                    if not cancel:
                        for process in processes:
                            try:
                                process.terminate()
                            except:
                                pass
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
                        sleepLightsState.put("off")
                        clearLights(pixels)
                        os.system("sudo reboot")
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
                                # Check for reboot, shutdown, pause/resume, and skip requests
                                if (
                                    GPIO.input(16) == GPIO.HIGH
                                    and GPIO.input(23) == GPIO.HIGH
                                    and GPIO.input(24) == GPIO.HIGH
                                ):
                                    cancel = False
                                    rebootStart = time.time()
                                    while time.time() - rebootStart < 3:
                                        time.sleep(0.1)
                                        if (
                                            GPIO.input(16) != GPIO.HIGH
                                            and GPIO.input(23) != GPIO.HIGH
                                            and GPIO.input(24) != GPIO.HIGH
                                        ):
                                            cancel = True
                                            break
                                    if not cancel:
                                        for process in processes:
                                            try:
                                                process.terminate()
                                            except:
                                                pass
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
                                        convertToSpeech("Rebooting")
                                        onOff.put("lightsOff")
                                        lights.join()
                                        print("\033c", end="\r")
                                        sleepLightsState.put("off")
                                        clearLights(pixels)
                                        os.system("sudo reboot")
                                # Check for awake request
                                elif (
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
                                        auth_manager = SpotifyOAuth(
                                            "client_id",
                                            "client_secret",
                                            "http://localhost:5173/callback",
                                            scope="user-modify-playback-state",
                                            cache_path="/home/matthewpi/Spotify/.cache",
                                        )
                                        sp = spotipy.Spotify(auth_manager=auth_manager)
                                        try:
                                            sp.next_track(
                                                "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                            )
                                        except:
                                            pass
                                        print("Skipping song . . .")
                                    # Pause/Resume if double clicked
                                    elif double:
                                        try:
                                            auth_manager = SpotifyOAuth(
                                                "client_id",
                                                "client_secret",
                                                "http://localhost:5173/callback",
                                                scope="user-modify-playback-state",
                                                cache_path="/home/matthewpi/Spotify/.cache",
                                            )
                                            sp = spotipy.Spotify(
                                                auth_manager=auth_manager
                                            )
                                            if sp.currently_playing()["is_playing"]:
                                                auth_manager = SpotifyOAuth(
                                                    "client_id",
                                                    "client_secret",
                                                    "http://localhost:5173/callback",
                                                    scope="user-modify-playback-state",
                                                    cache_path="/home/matthewpi/Spotify/.cache",
                                                )
                                                sp = spotipy.Spotify(
                                                    auth_manager=auth_manager
                                                )
                                                sp.pause_playback(
                                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                                )
                                                print("Pausing . . .")
                                            else:
                                                auth_manager = SpotifyOAuth(
                                                    "client_id",
                                                    "client_secret",
                                                    "http://localhost:5173/callback",
                                                    scope="user-modify-playback-state",
                                                    cache_path="/home/matthewpi/Spotify/.cache",
                                                )
                                                sp = spotipy.Spotify(
                                                    auth_manager=auth_manager
                                                )
                                                sp.start_playback(
                                                    "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                                )
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
                        auth_manager = SpotifyOAuth(
                            "client_id",
                            "client_secret",
                            "http://localhost:5173/callback",
                            scope="user-modify-playback-state",
                            cache_path="/home/matthewpi/Spotify/.cache",
                        )
                        sp = spotipy.Spotify(auth_manager=auth_manager)
                        try:
                            sp.next_track("06c55ec62f492429c6ebbf38fc814d5a7382386f")
                        except:
                            pass
                        print("Skipping song . . .")
                    # Pause/Resume if double clicked
                    elif double:
                        try:
                            auth_manager = SpotifyOAuth(
                                "client_id",
                                "client_secret",
                                "http://localhost:5173/callback",
                                scope="user-modify-playback-state",
                                cache_path="/home/matthewpi/Spotify/.cache",
                            )
                            sp = spotipy.Spotify(auth_manager=auth_manager)
                            if sp.currently_playing()["is_playing"]:
                                auth_manager = SpotifyOAuth(
                                    "client_id",
                                    "client_secret",
                                    "http://localhost:5173/callback",
                                    scope="user-modify-playback-state",
                                    cache_path="/home/matthewpi/Spotify/.cache",
                                )
                                sp = spotipy.Spotify(auth_manager=auth_manager)
                                try:
                                    sp.pause_playback(
                                        "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                    )
                                except:
                                    pass
                                print("Pausing . . .")
                            else:
                                auth_manager = SpotifyOAuth(
                                    "client_id",
                                    "client_secret",
                                    "http://localhost:5173/callback",
                                    scope="user-modify-playback-state",
                                    cache_path="/home/matthewpi/Spotify/.cache",
                                )
                                sp = spotipy.Spotify(auth_manager=auth_manager)
                                try:
                                    sp.start_playback(
                                        "06c55ec62f492429c6ebbf38fc814d5a7382386f"
                                    )
                                except:
                                    pass
                                print("Resuming . . .")
                        except:
                            pass
                    elif not skipInput:
                        listen.terminate()
                        physicalInput = True
                        break
            # Shut off if both volume buttons are pressed together
            if (
                GPIO.input(23) == GPIO.HIGH
                and GPIO.input(24) == GPIO.HIGH
                and GPIO.input(16) == GPIO.LOW
            ):
                cancel = False
                shutdownStart = time.time()
                while time.time() - shutdownStart < 3:
                    time.sleep(0.1)
                    if (
                        GPIO.input(23) != GPIO.HIGH
                        and GPIO.input(24) != GPIO.HIGH
                        and GPIO.input(16) != GPIO.LOW
                    ):
                        cancel = True
                        break
                if not cancel:
                    for process in processes:
                        try:
                            process.terminate()
                        except:
                            pass
                    onOff = Queue()
                    lights = Process(
                        target=lightsControl,
                        args=(pixels, onOff, lightsUsageStatus, sleepLightsState),
                    )
                    processes.append(lights)
                    lights.start()
                    convertToSpeech("Shutting off")
                    onOff.put("lightsOff")
                    lights.join()
                    print("\033c", end="\r")
                    sleepLightsState.put("off")
                    clearLights(pixels)
                    os.system("sudo pkill -9 -f chatbot.py")
        # Check if the user wants to terminate the program
        try:
            if awaking:
                continue
        except:
            pass
        if not physicalInput:
            listen.join()
            messages = return_dict.values()[0]
            if messages == "reboot":
                sleepLightsState.put("off")
                clearLights(pixels)
                os.system("sudo reboot")
            elif messages == "shut off":
                sleepLightsState.put("off")
                clearLights(pixels)
                os.system("sudo pkill -9 -f chatbot.py")
        # Temporarily pause any songs currently playing to listen to user
        auth_manager = SpotifyOAuth(
            "client_id",
            "client_secret",
            "http://localhost:5173/callback",
            scope="user-modify-playback-state",
            cache_path="/home/matthewpi/Spotify/.cache",
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        try:
            sp.pause_playback("06c55ec62f492429c6ebbf38fc814d5a7382386f")
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
            auth_manager = SpotifyOAuth(
                "client_id",
                "client_secret",
                "http://localhost:5173/callback",
                scope="user-modify-playback-state",
                cache_path="/home/matthewpi/Spotify/.cache",
            )
            sp = spotipy.Spotify(auth_manager=auth_manager)
            try:
                sp.start_playback("06c55ec62f492429c6ebbf38fc814d5a7382386f")
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
        client = OpenAI(api_key="open_ai_key")
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
        auth_manager = SpotifyOAuth(
            "client_id",
            "client_secret",
            "http://localhost:5173/callback",
            scope="user-modify-playback-state",
            cache_path="/home/matthewpi/Spotify/.cache",
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        try:
            sp.start_playback("06c55ec62f492429c6ebbf38fc814d5a7382386f")
        except:
            pass
