import os
import random
import base64
import requests
from urllib.parse import quote

STYLE = (
    "Editorial mixed-media collage illustration for a financial news article, "
    "{bg}. Vintage ink-engraving and pen-sketch line art of the scene elements, "
    "as if cut from an old etching book and layered together like a collage. "
    "Limited palette: black, charcoal grey, white, vivid cyan (turquoise) and "
    "emerald green. Scene: {scene}. {layout}. {extras}. "
    "Hand-drawn candlestick chart bars rising from the bottom edge like paint "
    "drips, rising bars in emerald green and falling bars in cyan. "
    "Cyan and emerald watercolor splashes, black ink splatter, torn paper edges, "
    "grainy paper texture, lots of empty space, clean composition. "
    "Any coin or banknote is plain with no inscription. "
    "no orange, no red, no readable text, no letters, no numbers, no logos, "
    "no watermark, no people"
)

BACKGROUNDS = [
    "on a cream off-white paper background",
    "on a cream off-white paper background",
    "on a cream off-white paper background",
    "on a deep charcoal-black paper background, with white and light-grey line art instead of black",
]

LAYOUTS = [
    "Engraved landmarks across the upper half, one large plain coin in the center as the focal object, candlestick drips below",
    "Main landmark on the left, a second landmark on the right, a plain coin overlapping both in the middle",
    "Symmetrical skyline with the main subject in the middle and a wide cyan watercolor wash behind it",
    "Main subject in the lower half with a huge cyan disc rising behind it and green candlestick drips in front",
    "Two overlapping torn paper layers, engraved scene on top, a block of cyan behind and green ink drips",
    "A reflected skyline: the engraved scene above and its ink-splatter reflection below turning into candlestick bars",
]

EXTRAS = [
    "Emerald green watercolor splashes in one corner",
    "Cyan halftone dot pattern near one edge",
    "Cyan and green ink splatter dots scattered around the subject",
    "A faint grid of thin lines in the background with a thin green line chart curve",
    "Small torn cyan and green paper strips along one edge",
]


def build_prompt(scene):
    scene = scene.replace("orange ", "").replace("Orange ", "")
    return STYLE.format(
        bg=random.choice(BACKGROUNDS),
        scene=scene,
        layout=random.choice(LAYOUTS),
        extras=random.choice(EXTRAS),
    )


def cloudflare_image(prompt):
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
    return base64.b64decode(r.json()["result"]["image"])


def pollinations_image(prompt):
    url = "https://image.pollinations.ai/prompt/" + quote(prompt)
    r = requests.get(
        url,
        params={
            "width": 1344,
            "height": 768,
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


def generate_image(scene):
    prompt = build_prompt(scene)
    print("Image prompt:", prompt)
    providers = (("Cloudflare", cloudflare_image), ("Pollinations", pollinations_image))
    for name, fn in providers:
        try:
            data = fn(prompt)
            print(f"Image created by {name}")
            return data, name
        except Exception as e:
            print(f"{name} failed: {e}")
    raise RuntimeError("All image providers failed")
