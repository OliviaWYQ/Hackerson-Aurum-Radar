"""Smoke test for the DashScope key + base URL in .env.

Mirrors how app/services/llm/dashscope.py uses the OpenAI-compatible
endpoint, so a pass here implies the backend should authenticate too.

Usage (from backend/):  python testApi.py
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY", "")
base_url = os.getenv("DASHSCOPE_BASE_URL", "")

# Show the target without exposing any part of the key.
print(f"base_url = {base_url}")
print(f"api_key_configured = {bool(api_key)}")
print()

if not api_key:
    raise SystemExit("DASHSCOPE_API_KEY missing — check backend/.env")
if not base_url:
    raise SystemExit("DASHSCOPE_BASE_URL missing — check backend/.env")

client = OpenAI(api_key=api_key, base_url=base_url)
resp = client.chat.completions.create(
    model="qwen-plus",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你是谁？一句话回答。"},
    ],
)
print(resp.choices[0].message.content)
print()
print(f"usage: prompt={resp.usage.prompt_tokens}  completion={resp.usage.completion_tokens}")
