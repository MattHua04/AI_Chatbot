from config import *
from openai import OpenAI
from chatbot.web.webInterfaceSupport import *

def sendPrompt(
    messages,
    systemMessage="You are a helpful assistant that will answer all the user's prompts to the best of your abilities. If your answer contains a math equation please format it in LateX",
    useModel=MODEL
    ):
    systemMessage = [{"role": "system", "content": systemMessage}]
    messages = cropToMeetMaxTokens(messages)
    client = OpenAI(api_key=GROQ_SECRET, base_url=GROQ_BASE_URL)
    response = client.chat.completions.create(
        model=useModel,
        messages=systemMessage + messages
    )
    return response.choices[0].message.content