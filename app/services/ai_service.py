import requests

API_KEY = "sk-59addf63a8bd464c92242421db666aa1"
BASE_URL = "https://ai-gen.sundaebytestt.com/"
MODEL = "meta/llama-3.2-3b-instruct"


def ask_ai(prompt: str):
    url = f"{BASE_URL}/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=10
        )

        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]

    except Exception as e:
        print("AI Error:", e)
        return "AI server unavailable. Try again later."