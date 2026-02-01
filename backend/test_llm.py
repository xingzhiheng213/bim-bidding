"""Test LLM call (stage 2.1): run from backend/ with venv activated.
Requires DEEPSEEK_API_KEY in .env."""
import os

# Ensure backend/ is cwd so app.config loads .env from here
_backend = os.path.dirname(os.path.abspath(__file__))
os.chdir(_backend)

from app.llm import call_llm

def main():
    print("Calling DeepSeek (deepseek-chat)...")
    content = call_llm(
        "deepseek",
        "deepseek-chat",
        [{"role": "user", "content": "你好，回复一句话"}],
    )
    print("Response:", content)
    print("OK")

if __name__ == "__main__":
    main()
