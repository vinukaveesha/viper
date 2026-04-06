import asyncio
import litellm
import os

async def main():
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)
    valid_key = "AIzaSyC-qIF5CMiuTdbjJP-8bU9BC1nFVzjcXM8"
    try:
        res = await litellm.acompletion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": "hi"}],
            api_key=valid_key
        )
        print("Response:", res)
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
