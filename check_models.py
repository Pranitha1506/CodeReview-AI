
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Gemini API key is missing.")
    raise SystemExit(1)

client = genai.Client(api_key=api_key)

print("\nAvailable Gemini models:\n")

try:
    for model in client.models.list():
        supported = getattr(model, "supported_actions", []) or []

        if "generateContent" in supported:
            print(model.name)

except Exception as error:
    print("Error:", error)
