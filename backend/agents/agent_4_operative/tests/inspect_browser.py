
from browser_use import Browser
import inspect
import asyncio

async def inspect_browser():
    b = Browser()
    print("Methods of Browser:")
    for m in dir(b):
        if not m.startswith('__'):
            print(m)
    
    print("\nHas close?", hasattr(b, 'close'))
    
    if hasattr(b, 'close'):
        print("Closing...")
        # await b.close() 

if __name__ == "__main__":
    asyncio.run(inspect_browser())
