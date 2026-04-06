import litellm
import os

os.environ["GOOGLE_API_KEY"] = "MY_GOOGLE_KEY"
os.environ.pop("GEMINI_API_KEY", None)

try:
    print("API Base:", litellm.get_api_base(model="gemini/gemini-2.5-flash"))
    print("API Key:", litellm.get_api_key(model="gemini/gemini-2.5-flash"))
except Exception as e:
    print(e)
