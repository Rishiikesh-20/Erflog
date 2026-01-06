
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent, Browser
import asyncio

async def reproduction():
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key="fake")
    # PATCH: browser-use v0.11.x expects .provider and .model_name attributes
    llm.provider = "google" 
    llm.model_name = "gemini-2.0-flash"
    
    browser = Browser()
    agent = Agent(task="test", llm=llm, browser=browser)
    # The error might happen at init or run
    print("Agent init success")
    try:
        await agent.run()
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reproduction())
