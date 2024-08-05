import os
import sys
import copy
import zlib
import json
import base64
import certifi
from config import *
from rpi_ws281x import *
from threading import Thread
from pymongo import MongoClient
from multiprocessing import Process
from ai.aiTools import *

def webInit(sp, pixels, lightsUsageStatus, sleepLightsState):
    # Setup Caddy
    os.system("caddy stop")
    os.system("sudo systemctl restart caddy")
    # Connect to MongoDB
    db = MongoClient(MDB_CONN_STR, tlsCAFile=certifi.where())['test']
    stateCol = db["spotifies"]
    
    # Start checking for remote prompts
    remote = Process(
        target=findRemotePrompts, args=(sp, pixels, lightsUsageStatus, sleepLightsState)
    )
    remote.start()
    return stateCol

def postPromptResponse(messages, conversation, conversations):
    MAX_CONTENT_SIZE = 16000
    id = conversation["_id"]
    content = messages
    messages = copy.deepcopy(content)
    last_message = messages[-1]
    last_message_owner = last_message[0]
    if last_message_owner == "AI" and last_message[1] == "..." and conversation['respond']:
        content.pop()
        messages.pop()
        last_message = messages[-1]
        last_message_owner = last_message[0]
    # Convert content to openai format
    messages = [{"role": "assistant" if message[0] == "AI" else "user", "content": message[1]} for message in messages]
    updated_content = copy.deepcopy(content)
    updated_content.append(["AI", "..."])
    # Compress content before updating document in MongoDB
    should_compress = sys.getsizeof(json.dumps(updated_content)) > MAX_CONTENT_SIZE
    if should_compress: updated_content = compress_content(updated_content)
    if should_compress:
        conversations.update_one({"_id": id}, {"$set": {"content": [], "compressed_content": updated_content}})
    else:
        conversations.update_one({"_id": id}, {"$set": {"content": updated_content, "compressed_content": ''}})
    # Send prompt to OpenAI
    if last_message_owner == "User":
        response = sendPrompt(messages)
        updated_content = copy.deepcopy(content)
        updated_content.append(["AI", response])
    elif last_message_owner == "AI":
        response = sendPrompt(messages,
            """
            You are a helpful assistant that will answer all the user's prompts to the best of your abilities. 
            In this case, please continue the conversation in a way that expands and adds meaning to what has already been said. 
            For example, if you've been telling a story, continue the story, or if you've been discussing a topic, 
            begin discussing related more complex topics that build off what you've told the user. 
            If you asked a question in your latest message that the user has not responded to, 
            make a prediction of the user's response and continue the conversation based on that prediction.
            Do not repeat the same information you have said before and determine what to discuss next by yourself without consulting the user.
            """)
        updated_content = copy.deepcopy(content)
        updated_content[-1][1] += "\n" + response
    # Compress content before updating document in MongoDB
    should_compress = sys.getsizeof(json.dumps(updated_content)) > MAX_CONTENT_SIZE
    if should_compress: updated_content = compress_content(updated_content)
    if should_compress:
        conversations.update_one({"_id": id}, {"$set": {"content": [], "compressed_content": updated_content, "respond": False}})
    else:
        conversations.update_one({"_id": id}, {"$set": {"content": updated_content, "compressed_content": '', "respond": False}})

def findRemotePrompts(sp, pixels, lightsUsageStatus, sleepLightsState):
    # Remote conversation memory
    remoteMessages = []
    # Connect to MongoDB
    db = MongoClient(MDB_CONN_STR, tlsCAFile=certifi.where())['test']
    conversations = db["conversations"]
    
    while True:
        conversationQueue = None
        while conversationQueue == None:
            try:
                # Retrieve all conversations
                all_conversations = list(conversations.find())
                # Decompress content and filter conversations with the last message from "User"
                conversationQueue = []
                for conversation in all_conversations:
                    # Check for uncompressed conversations
                    if conversation['respond']:
                        if len(conversation['content']) > 0:
                            conversationQueue.append(conversation)
                        # Check for compressed conversations
                        elif conversation['compressed_content'] != '':
                            conversation['compressed_content'] = decompress_content(conversation['compressed_content'])
                            if conversation['compressed_content'] and len(conversation['compressed_content']) > 0:
                                conversationQueue.append(conversation)
            except:
                db = MongoClient(MDB_CONN_STR, tlsCAFile=certifi.where())['test']
                conversations = db["conversations"]
        
        try:
            # Check if each prompt has a response given
            threads = []
            for conversation in conversationQueue:
                remoteMessages = conversation['content'] if len(conversation['content']) > 0 else conversation['compressed_content']
                t = Thread(target=postPromptResponse, args=(remoteMessages, conversation, conversations))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
        except:
            pass
        
def decompress_content(content):
    try:
        compressed_content = base64.b64decode(content)
        decompressed_content = zlib.decompress(compressed_content, 15 + 32).decode('utf-8')
        return json.loads(decompressed_content)
    except:
        return []
    
def compress_content(content):
    try:
        json_content = json.dumps(content)
        compressed_content = zlib.compress(json_content.encode('utf-8'))  # Compress the content
        return base64.b64encode(compressed_content).decode('utf-8')
    except:
        return ''