import tiktoken
from config import *
from openai import OpenAI

def sendPrompt(
    messages,
    systemMessage="You are a helpful assistant that will answer all the user's prompts to the best of your abilities. If your answer contains a math equation please format it in LateX",
    useModel=MODEL
    ):
    systemMessage = [{"role": "system", "content": systemMessage}]
    messages = cropToMeetMaxTokens(messages)
    client = OpenAI(api_key=OPENAI_SECRET)
    # client = OpenAI(api_key=GROQ_SECRET, base_url=GROQ_BASE_URL)
    response = client.chat.completions.create(
        model=useModel,
        messages=systemMessage + messages
    )
    return response.choices[0].message.content

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