import os
import re
import random
import base64
import requests
from urllib.parse import quote

WIDTH = 1344
HEIGHT = 768

STYLE = (
    "Wide panoramic editorial mixed-media collage illustration for a financial "
    "news article, on a warm cream paper background with subtle paper grain. "
    "Black-and-white ink engraving and pen-sketch drawings in the style of a "
    "vintage newspaper illustration showing: {scene}. {layout}. "
    "Soft watercolor washes in cyan and emerald green behind the subject, black "
    "ink splatter and dry-brush texture, and a row of thin vertical candlestick "
    "bars in cyan and green fading downward in the lower third like a "
    "reflection. Limited palette: cream, black, grey, cyan, emerald green, plus "
    "small realistic gold bars as a signature detail. Flags and national "
    "symbols keep their real colors. Clean composition with empty space around "
    "the subject. No orange, no readable text, no letters, no numbers, no "
    "logos, no watermark, no people"
)

LAYOUTS = [
    "The main subject is large in the center with related landmarks sketched on the left and right",
    "The main subject sits on the left third and a wide landscape or sea stretches to the right",
    "The main subject sits on the right third and a wide landscape or sea stretches to the left",
    "The main subject is centered and mirrored skylines or coastlines frame both sides",
]

DIRECTIONS = {
    "bullish": "a single bold emerald green arrow pointing diagonally upward",
    "bearish": "a single bold cyan arrow pointing diagonally downward",
    "mixed": "a single bold cyan horizontal arrow pointing sideways",
    "neutral": "a single bold cyan horizontal arrow pointing sideways",
}


def strip_arrows(scene):
    kept = []
    for part in re.split(r"[,;]", scene):
        p = part.strip()
        if not p:
            continue
        if re.search(r"\barrows?\b", p, re.I) and len(p.split()) <= 12:
            continue
        kept.append(p)
    return ", ".join(kept)


def build_prompt(scene, direction=None):
    scene = scene.replace("orange ", "").replace("Orange ", "").strip().rstrip(".")
    if direction in DIRECTIONS:
        scene = strip_arrows(scene) + ", " + DIRECTIONS[direction]
    return STYLE.format(scene=scene, layout=random.choice(LAYOUTS))


def decode_image(r):
    ctype = r.headers.get("content-type", "")
    if ctype.startswith("image"):
        return r.content
    data = r.json()
    result = data.get("result", data)
    img = result.get("image") if isinstance(result, dict) else None
    if not img:
        raise RuntimeError("No image in response: " + str(data)[:200])
    return base64.b64decode(img)


def cloudflare_klein(prompt):
    account = os.environ["CF_ACCOUNT_ID"]
    token = os.environ["CF_API_TOKEN"]
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account}"
        "/ai/run/@cf/black-forest-labs/flux-2-klein-4b"
    )
    files = {
        "prompt": (None, prompt),
        "width": (None, str(WIDTH)),
        "height": (None, str(HEIGHT)),
        "seed": (None, str(random.randint(1, 999999))),
    }
    r = requests.post(
        url, headers={"Authorization": f"Bearer {token}"}, files=files, timeout=150
    )
    if r.status_code != 200:
        print("Cloudflare klein error:", r.status_code, r.text[:300])
    r.raise_for_status()
    return decode_image(r)


def cloudflare_schnell(prompt):
    account = os.environ["CF_ACCOUNT_ID"]
    token = os.environ["CF_API_TOKEN"]
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account}"
        "/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": prompt, "steps": 6},
        timeout=90,
    )
    r.raise_for_status()
    return decode_image(r)


def pollinations_image(prompt):
    url = "https://image.pollinations.ai/prompt/" + quote(prompt)
    r = requests.get(
        url,
        params={
            "width": WIDTH,
            "height": HEIGHT,
            "model": "flux",
            "nologo": "true",
            "seed": random.randint(1, 999999),
        },
        timeout=120,
    )
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image"):
        raise RuntimeError("Pollinations did not return an image")
    return r.content


def generate_image(scene, direction=None):
    prompt = build_prompt(scene, direction)
    print("Image prompt:", prompt)
    providers = (
        ("Cloudflare FLUX.2", cloudflare_klein),
        ("Cloudflare FLUX.1", cloudflare_schnell),
        ("Pollinations", pollinations_image),
    )
    for name, fn in providers:
        try:
            data = fn(prompt)
            print(f"Image created by {name}")
            return data, name
        except Exception as e:
            print(f"{name} failed: {e}")
    raise RuntimeError("All image providers failed")
