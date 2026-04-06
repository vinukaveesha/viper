import asyncio
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.base_llm import LlmRequest

async def main():
    import os
    # explicitly clear env for testing
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)

    # Use the VALID key from viper/.env so it actually succeeds if kwargs work
    valid_key = "AIzaSyC-qIF5CMiuTdbjJP-8bU9BC1nFVzjcXM8"

    llm = LiteLlm(model="gemini/gemini-2.5-flash", api_key=valid_key)
    try:
        req = LlmRequest(model="gemini/gemini-2.5-flash", messages=[{"role": "user", "content": "hi"}])
        gen = llm.generate_content_async(req)
        async for r in gen:
            print("Response:", r.text)
    except Exception as e:
        print("Error:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
