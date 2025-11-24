from dotenv import load_dotenv; load_dotenv()
from openai import OpenAI

client = OpenAI()
resp = client.responses.create(model="gpt-4o-mini", input="ok")
print("API key OK:", bool(resp.output_text))
