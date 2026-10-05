import os
import time
import requests

MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
]


def call_gemini(key, prompt):
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    last = "no attempt made"
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(1, 4):
            try:
                r = requests.post(url, headers=headers, json=body, timeout=180)
            except requests.RequestException as e:
                last = f"{model}: {e}"
                print(f"Gemini network error ({model}, try {attempt}):", e)
                time.sleep(10 * attempt)
                continue
            if r.status_code == 200:
                print("Gemini model used:", model)
                return r.json()
            last = f"{model}: {r.status_code}"
            print(f"Gemini error ({model}, try {attempt}):", r.status_code, r.text[:300])
            if r.status_code in (400, 403, 404):
                break
            time.sleep(15 * attempt)
    raise RuntimeError("All Gemini models failed. Last: " + last)
