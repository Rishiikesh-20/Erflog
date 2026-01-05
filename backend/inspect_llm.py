
import inspect
try:
    from browser_use.llm import LangChainChatModel
    print("Found LangChainChatModel")
except ImportError:
    print("No LangChainChatModel")

try:
    from browser_use.llm import langchain
    print("Found browser_use.llm.langchain")
except ImportError:
    print("No browser_use.llm.langchain")

import browser_use.llm
print("browser_use.llm members:", dir(browser_use.llm))
