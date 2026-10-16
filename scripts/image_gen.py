import os
import re
import random
import base64
import requests
from urllib.parse import quote

# ---- Brand colours (change these three lines to restyle everything) ----
ACCENT_A = "vivid cyan (turquoise)"
ACCENT_B = "emerald green"
AVOID = "no orange and no red, except the true colors of national flags"

STYLE = (
    "Editorial mixed-media collage illustration for a financial news article, "
    "{bg}. Desaturated black-and-white photographic cutouts and vintage ink "
    "engraving details layered like torn paper, combined with bold flat graphic "
    "shapes in " + ACCENT_A + " and " + ACCENT_B + ". Limited palette: black, "
    "charcoal grey, white, " + ACCENT_A + " and " + ACCENT_B + ". "
    "Scene: {scene}. {subjects}{chart}{layout}. {extras}. "
    "Torn paper edges, subtle paper grain, clean layered composition. "
    + AVOID + ", no readable text, no letters, no numbers, no logos, "
    "no watermark, no axis labels. Any human figure is an anonymous faceless "
    "silhouette, never a portrait of a real person. Any banknote or coin is "
    "stylized with no printed text"
)

BACKGROUNDS = [
    "on a cream off-white paper background",
    "on a cream off-white paper background",
    "on a cream off-white paper background",
    "on a deep charcoal-black paper background, with white and light-grey line art",
]

LAYOUTS = [
    "A large " + ACCENT_A + " circle behind the main subject and a smaller " + ACCENT_B + " circle at the edge",
    "Main subject on the left, secondary elements overlapping in the center, a big " + ACCENT_A + " brush-stroke shape on the right",
    "Main subject centered over a wide " + ACCENT_B + " paint smear with black ink splatter below",
    "Two overlapping torn paper layers with a block of " + ACCENT_A + " behind and green ink drips",
    "Main subject in the lower half with a huge " + ACCENT_A + " disc rising behind it",
    "Symmetrical composition with the subject in the middle and " + ACCENT_A + " and " + ACCENT_B + " shapes on both sides",
]

EXTRAS = [
    "A halftone dot pattern in one corner",
    "Thin radiating lines fanning out from behind the subject",
    "Ink splatter dots scattered around",
    "Small torn paper strips along one edge",
    "A faint grid of thin lines in the background",
]

# ---- Subject detection ----
COUNTRIES = [
    (["us", "u.s.", "usa", "united states", "american", "washington", "white house",
      "trump", "treasury", "wall street", "fed", "federal reserve", "fomc", "dollar"],
     "the United States (red and white stripes, white stars on a blue corner)"),
    (["japan", "japanese", "boj", "yen", "tokyo"],
     "Japan (a red circle on a white field)"),
    (["eurozone", "euro", "ecb", "european union", "eu"],
     "the European Union (a circle of yellow stars on blue)"),
    (["uk", "britain", "british", "boe", "bank of england", "pound", "sterling"],
     "the United Kingdom (the Union Jack)"),
    (["china", "chinese", "pboc", "yuan", "beijing"],
     "China (yellow stars on a red field)"),
    (["russia", "russian", "moscow", "kremlin"],
     "Russia (white, blue and red horizontal stripes)"),
    (["ukraine", "ukrainian", "kyiv"],
     "Ukraine (blue stripe above a yellow stripe)"),
    (["iran", "iranian", "tehran"],
     "Iran (green, white and red horizontal stripes)"),
    (["israel", "israeli", "gaza"],
     "Israel (a blue star between two blue stripes on white)"),
    (["saudi", "riyadh", "aramco"],
     "Saudi Arabia (a white sword under white script on green)"),
    (["yemen", "houthi", "houthis"],
     "Yemen (red, white and black horizontal stripes)"),
    (["australia", "australian", "aussie", "rba"],
     "Australia (Union Jack corner with white stars on blue)"),
    (["canada", "canadian", "loonie"],
     "Canada (a red maple leaf between two red bars)"),
    (["switzerland", "swiss", "snb", "franc"],
     "Switzerland (a white cross on a red square)"),
    (["india", "indian", "rupee"],
     "India (saffron, white and green stripes with a blue wheel)"),
    (["germany", "german", "berlin"],
     "Germany (black, red and gold horizontal stripes)"),
    (["france", "french", "paris"],
     "France (blue, white and red vertical stripes)"),
    (["new zealand", "kiwi", "rbnz"],
     "New Zealand (Union Jack corner with red stars on blue)"),
    (["norway", "norwegian", "krone"],
     "Norway (a blue cross outlined in white on red)"),
    (["singapore", "mas"],
     "Singapore (red over white with a white crescent and five stars)"),
    (["south korea", "korean", "won"],
     "South Korea (a red and blue circle on white with black trigrams)"),
    (["mexico", "mexican", "peso"],
     "Mexico (green, white and red vertical stripes)"),
    (["turkey", "turkish", "lira"],
     "Turkey (a white crescent and star on red)"),
]

BANKS = [
    (["fed", "federal reserve", "fomc"],
     "the Federal Reserve building with classical columns"),
    (["ecb", "european central bank"], "the European Central Bank tower"),
    (["boj", "bank of japan"], "the Bank of Japan building"),
    (["boe", "bank of england"], "the Bank of England stone facade"),
    (["pboc", "people's bank of china"], "the People's Bank of China building"),
]

OBJECTS = [
    (["gold", "xau", "bullion"], "stacked gold bars and a plain gold coin"),
    (["silver", "xag"], "stacked silver bars"),
    (["oil", "crude", "wti", "brent", "opec"], "oil derricks and a barrel"),
    (["dollar", "usd", "dxy", "greenback"], "a stylized US dollar banknote"),
]

ROLE_WORDS = [
    "chair", "governor", "president", "minister", "speech", "speaks", "says",
    "said", "warns", "signals", "testimony", "testifies", "press conference",
    "official", "policymaker", "secretary",
]

UP_WORDS = [
    "rise", "rises", "rising", "rally", "rallies", "climbs", "jumps", "surges",
    "soars", "gains", "rebounds", "recovers", "higher", "record high", "advances",
]
DOWN_WORDS = [
    "falls", "fall", "drops", "slides", "slumps", "tumbles", "plunges", "sinks",
    "crashes", "declines", "lower", "slips", "retreats", "slides",
]
MARKET_WORDS = [
    "price", "prices", "gold", "xau", "silver", "oil", "wti", "brent", "crude",
    "yield", "yields", "dollar", "dxy", "usd", "forex", "stocks", "equities",
    "s&p", "nasdaq", "bitcoin", "index", "futures", "markets", "market",
]


def _has(text, words):
    pat = "|".join(re.escape(w) for w in words)
    return re.search(r"(?<![a-z0-9])(?:" + pat + r")(?![a-z0-9])", text) is not None


def subjects_text(text):
    items = []
    flags = [f for words, f in COUNTRIES if _has(text, words)][:2]
    if flags:
        items.append(" and ".join("a large flag of " + f for f in flags))
    for words, desc in BANKS:
        if _has(text, words):
            items.append(desc)
            break
    if _has(text, ROLE_WORDS):
        items.append(
            "an anonymous suited official shown only as a black halftone "
            "silhouette at a podium, face hidden in shadow"
        )
    for words, desc in OBJECTS:
        if _has(text, words):
            items.append(desc)
    items = items[:4]
    if not items:
        return ""
    return "Include " + ", ".join(items) + ". "


def chart_text(text, impact=None):
    up = sum(1 for w in UP_WORDS if _has(text, [w]))
    down = sum(1 for w in DOWN_WORDS if _has(text, [w]))
    if not (up or down or _has(text, MARKET_WORDS)):
        return ""
            if up == down and isinstance(impact, str):
        if impact.lower() == "bullish":
            up += 1
        elif impact.lower() == "bearish":
            down += 1
    if up > down:
        return (
            "A large hand-drawn candlestick chart fills the background with a clear "
            "upward trend, rising candles in " + ACCENT_B + " and a bold "
            + ACCENT_B + " upward arrow. "
        )
    if down > up:
        return (
            "A large hand-drawn candlestick chart fills the background with a clear "
            "downward trend, falling candles in " + ACCENT_A + " and a bold "
            + ACCENT_A + " downward arrow. "
        )
    return (
        "A large hand-drawn candlestick chart fills the background with choppy "
        "sideways movement and a thin line chart curve. "
    )


def build_prompt(scene, impact=None, headline=""):
    scene = scene.replace("orange ", "").replace("Orange ", "")
    text = (headline + " " + scene).lower()
    return STYLE.format(
        bg=random.choice(BACKGROUNDS),
        scene=scene,
        subjects=subjects_text(text),
        chart=chart_text(text, impact),
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


def generate_image(scene, impact=None, headline=""):
    prompt = build_prompt(scene, impact, headline)
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
