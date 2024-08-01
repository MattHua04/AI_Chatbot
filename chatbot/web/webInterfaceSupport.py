import os
import sys
import copy
import zlib
import json
import base64
import certifi
import tiktoken
from config import *
from rpi_ws281x import *
from threading import Thread
from pymongo import MongoClient
from chatbot.ai.aiTools import *
from multiprocessing import Process

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
    response = sendPrompt(messages)
    updated_content = copy.deepcopy(content)
    updated_content.append(["AI", response])
    # Compress content before updating document in MongoDB
    should_compress = sys.getsizeof(json.dumps(updated_content)) > MAX_CONTENT_SIZE
    if should_compress: updated_content = compress_content(updated_content)
    if should_compress:
        conversations.update_one({"_id": id}, {"$set": {"content": [], "compressed_content": updated_content}})
    else:
        conversations.update_one({"_id": id}, {"$set": {"content": updated_content, "compressed_content": ''}})

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
                    if len(conversation['content']) > 0:
                        last_message_owner = conversation['content'][-1][0]
                        if last_message_owner == "User":
                            conversationQueue.append(conversation)
                    # Check for compressed conversations
                    elif conversation['compressed_content'] != '':
                        conversation['compressed_content'] = decompress_content(conversation['compressed_content'])
                        if conversation['compressed_content'] and len(conversation['compressed_content']) > 0:
                            last_message_owner = conversation['compressed_content'][-1][0]
                            if last_message_owner == "User":
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
                
def count_tokens(messages):
    encoder = tiktoken.encoding_for_model(TOKENIZER_MODEL)
    total_tokens = 0
    for message in messages:
        message_tokens = encoder.encode(message["content"])
        total_tokens += len(message_tokens) + len(encoder.encode(message["role"]))
    return total_tokens

def cropToMeetMaxTokens(messages):
    # Maximum tokens for the gpt-4o-mini model
    MAX_TOKENS = 16385 * 0.8
    # Count tokens and remove oldest messages if needed
    while count_tokens(messages) > MAX_TOKENS:
        messages.pop(0)
    return messages