import math
import spotipy
import sounddevice
from config import *
from spotipy.oauth2 import *
from threading import Thread
import speech_recognition as sr
from multiprocessing import Manager, Process, Queue
from chatbot.lights.ringLight import *
from chatbot.audio.audioOut import *
from chatbot.ai.aiTools import *

def audioInInit():
    # Set up microphone input
    recorder = sr.Recognizer()
    return recorder

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
    lightsUsageStatus,
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
            
            # Trim text memory
            words = text.split()
            if len(words) > 10:
                text = ' '.join(words[1:])

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
                        request = text
                        text = "cancel"
                        try:
                            request = sendPrompt([{"role": "system", "content": request}], "what song or playlist does this user want to play (answer with only the song or playlist title)?", "llama-3.1-8b-instant")
                            auth_manager = SpotifyOAuth(
                                SPOTIFY_CLIENT,
                                SPOTIFY_SECRET,
                                "http://localhost:5173/callback",
                                scope="user-modify-playback-state",
                                cache_path="/home/madspi/Spotify/.cache",
                            )
                            sp = spotipy.Spotify(auth_manager=auth_manager)
                            results = sp.search(request, 10, 0, "track,playlist")
                            tracks = results['tracks']['items']
                            playlists = results['playlists']['items']
                            all = tracks + playlists
                            prompt = []
                            for i, item in enumerate(all):
                                prompt.append(" ".join([
                                    f"{i}.",
                                    f"  (type={item['type']})",
                                    f"  (title={item['name']})",
                                    f"  (artists={', '.join([artist['name'] for artist in item.get('artists', [])])})" if 'artists' in item else f"  (owner={item['owner']['display_name']})",
                                    f"  (popularity={item.get('popularity', 'N/A')})",
                                    f"  (description={item.get('description', 'N/A')})"
                                ]))
                            prompt = '\n'.join(prompt)
                            choice = sendPrompt([{"role": "system", "content": prompt}], f'which search would the user be most satisfied with given their request of "{request}" (only respond with a single numerical index)?')
                            choice = all[int(choice)]
                            name = choice['name']
                            uri = choice['uri']
                            type = choice['type']
                            if type == "track":
                                sp.shuffle(
                                    False, SPOTIFY_DEVICE_ID
                                )
                                sp.start_playback(
                                    SPOTIFY_DEVICE_ID,
                                    uris=[uri],
                                    position_ms=0,
                                )
                            elif type == "playlist":
                                sp.start_playback(
                                    SPOTIFY_DEVICE_ID,
                                    context_uri=uri,
                                    position_ms=0,
                                )
                                sp.shuffle(
                                    True, SPOTIFY_DEVICE_ID
                                )
                                sp.next_track(
                                    SPOTIFY_DEVICE_ID
                                )
                            convertToSpeech("Playing " + name)
                            sp.repeat("off", SPOTIFY_DEVICE_ID)
                        except:
                            convertToSpeech("Unable to find song")
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