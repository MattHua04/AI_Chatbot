import os
import re
import time
from config import *
from gtts import gTTS
from mutagen.mp3 import MP3
from multiprocessing import Process

def audioOutInit(buttonPresses):
    actionButtonPlayer = Process(target=buttonPlayer, args=(buttonPresses,))
    actionButtonPlayer.start()

def buttonSound():
    os.system("mpg123 button_sound.mp3")
    
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
        
def splitIntoSentences(text):
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