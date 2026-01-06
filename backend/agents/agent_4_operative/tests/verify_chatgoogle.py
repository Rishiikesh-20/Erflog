
import os
import inspect
from browser_use.llm.google import ChatGoogle

print("Init args:", inspect.signature(ChatGoogle.__init__))

try:
    llm = ChatGoogle(model="gemini-2.0-flash-exp", api_key="test")
    print("Success with api_key")
except TypeError:
    print("Failed with api_key")

try:
    llm = ChatGoogle(model="gemini-2.0-flash-exp", google_api_key="test")
    print("Success with google_api_key")
except TypeError:
    print("Failed with google_api_key")
