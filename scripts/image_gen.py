import os
import random
import base64
import requests
from io import BytesIO

from PIL import Image, ImageDraw

from image_subjects import build_prompt, add_person

WIDTH = 1344
HEIGHT = 768


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
    if r.status_code != 200:
        print("Cloudflare schnell error:", r.status_code, r.text[:300])
    r.raise_for_status()
    return decode_image(r)


def draw_arrow(d, cx, cy, s, kind, color):
    if kind == "bullish":
        pts = [(cx, cy - s), (cx + s * 0.8, cy), (cx + s * 0.3, cy),
               (cx + s * 0.3, cy + s), (cx - s * 0.3, cy + s),
               (cx - s * 0.3, cy), (cx - s * 0.8, cy)]
    elif kind == "bearish":
        pts = [(cx, cy + s), (cx + s * 0.8, cy), (cx + s * 0.3, cy),
               (cx + s * 0.3, cy - s), (cx - s * 0.3, cy - s),
               (cx - s * 0.3, cy), (cx - s * 0.8, cy)]
    else:
        pts = [(cx + s, cy), (cx, cy - s * 0.8), (cx, cy - s * 0.3),
               (cx - s, cy - s * 0.3), (cx - s, cy + s * 0.3),
               (cx, cy + s * 0.3), (cx, cy + s * 0.8)]
    d.polygon(pts, fill=color)


def fallback_card(direction=None):
    bg = (10, 14, 19)
    cyan = (34, 211, 238)
    green = (52, 211, 153)
    img = Image.new("RGB", (WIDTH, HEIGHT), bg)
    d = ImageDraw.Draw(img)

    n = 28
    step = WIDTH // n
    for i in range(n):
        h = random.randint(60, 300)
        x = i * step + step // 4
        top = HEIGHT - 40 - h
        color = green if random.random() > 0.45 else cyan
        d.rectangle([x, top, x + step // 2, HEIGHT - 40], fill=color)
        cx = x + step // 4
        d.line([cx, top - random.randint(10, 40), cx, top], fill=color, width=3)

    arrow_color = green if direction == "bullish" else cyan
    draw_arrow(d, WIDTH - 260, 250, 150, direction, arrow_color)

    try:
        logo = Image.open(os.path.join("..", "docs", "logo.png")).convert("RGBA")
        h = 170
        w = round(logo.width * h / logo.height)
        logo = logo.resize((w, h))
        img.paste(logo, (80, 90), logo)
    except Exception as e:
        print("Fallback card: logo not found:", e)

    out = BytesIO()
    img.save(out, "JPEG", quality=88)
    return out.getvalue()


def generate_image(scene, impact=None, *args, **kwargs):
    # Accepts: (scene), (scene, impact), (scene, impact, ai_flag) and
    # (scene, impact, headline), in any of these orders.
    headline = kwargs.get("headline", "")
    ai = kwargs.get("ai", True)
    for a in args:
        if isinstance(a, bool):
            ai = a
        elif isinstance(a, str):
            headline = a
    text = headline + " " + scene

    if ai:
        prompt = build_prompt(scene, impact, headline)
        print("Image prompt:", prompt)
        providers = (
            ("Cloudflare FLUX.2", cloudflare_klein),
            ("Cloudflare FLUX.1", cloudflare_schnell),
        )
        for name, fn in providers:
            try:
                data = fn(prompt)
                print(f"Image created by {name}")
                return add_person(data, text), name
            except Exception as e:
                print(f"{name} failed: {e}")

    print("Using the branded fallback card")
    return add_person(fallback_card(impact), text), "Fallback card"
    
