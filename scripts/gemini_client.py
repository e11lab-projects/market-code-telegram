import os
import json
import time
import requests

MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
]


def parse_json(text):
    text = (text or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("No JSON object found")


def call_gemini_json(key, prompt):
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    last = "no attempt made"
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(1, 3):
            try:
                r = requests.post(url, headers=headers, json=body, timeout=180)
            except requests.RequestException as e:
                last = f"{model}: {e}"
                print(f"Gemini network error ({model}, try {attempt}):", e)
                time.sleep(10 * attempt)
                continue
            if r.status_code == 200:
                try:
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    data = parse_json(text)
                    print("Gemini model used:", model)
                    return data
                except Exception as e:
                    last = f"{model}: unreadable answer ({e})"
                    print(f"Gemini answer unreadable ({model}, try {attempt}):", e)
                    time.sleep(5)
                    continue
            last = f"{model}: {r.status_code}"
            print(f"Gemini error ({model}, try {attempt}):", r.status_code, r.text[:300])
            if r.status_code in (400, 403, 404):
                break
            if r.status_code == 429 and "perday" in r.text.lower().replace(" ", ""):
                print("Daily quota used up for", model, "- trying the next model")
                break
            time.sleep(20 * attempt)
    raise RuntimeError("All Gemini models failed. Last: " + last)
