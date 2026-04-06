import asyncio
import litellm
import os

os.environ.pop("GEMINI_API_KEY", None)
os.environ["GOOGLE_API_KEY"] = "fake-key"
print("Setting GOOGLE_API_KEY=fake-key, testing acompletion")
try:
    asyncio.run(litellm.acompletion(
        model="gemini/gemini-2.5-flash",
        messages=[{"role": "user", "content": "hi"}],
    ))
except Exception as e:
    print(repr(e))

os.environ.pop("GOOGLE_API_KEY", None)
os.environ["GEMINI_API_KEY"] = "fake-key"
print("\nSetting GEMINI_API_KEY=fake-key, testing acompletion")
try:
    asyncio.run(litellm.acompletion(
        model="gemini/gemini-2.5-flash",
        messages=[{"role": "user", "content": "hi"}],
    ))
except Exception as e:
    print(repr(e))
