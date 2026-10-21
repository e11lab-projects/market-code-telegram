import io
import re
import random

import requests

# ---- Brand colours (change these lines to restyle everything) ----
ACCENT_A = "vivid cyan (turquoise)"
ACCENT_B = "emerald green"
AVOID = "no orange and no red, except the true colors of national flags"

STYLE = (
    "Wide landscape editorial mixed-media collage illustration for a financial "
    "news article, {bg}. Desaturated black-and-white photographic cutouts and "
    "vintage ink engraving details layered like torn paper, combined with bold "
    "flat graphic shapes in " + ACCENT_A + " and " + ACCENT_B + ". Limited "
    "palette: black, charcoal grey, white, " + ACCENT_A + " and " + ACCENT_B + ". "
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
    (["singapore", "singapore-flagged"],
     "Singapore (red over white with a white crescent and five stars)"),
    (["south korea", "korean"],
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

# Story items come first. Gold is last so it only fills a free slot.
OBJECTS = [
    (["ship", "ships", "vessel", "vessels", "tanker", "tankers", "container",
      "containers", "cargo", "freighter"],
     "a cargo container ship loaded with stacked shipping containers on open water"),
    (["hormuz", "strait", "suez", "red sea", "canal"],
     "a narrow sea strait between two desert coastlines with rough waves"),
    (["sink", "sinks", "sank", "sunk", "sinking"],
     "the vessel tilting and sinking into the waves with black smoke"),
    (["missile", "missiles", "projectile", "drone", "drones", "strike", "attack"],
     "dark smoke plumes and the streak of a projectile in the sky"),
    (["tariff", "tariffs", "trade war", "port"],
     "port cranes and stacked shipping containers"),
    (["inflation", "cpi", "pce", "ppi"],
     "a shopping basket and a rising price-tag symbol with no numbers"),
    (["jobs", "payrolls", "nonfarm", "unemployment", "jobless"],
     "a factory skyline and a row of hard hats"),
    (["bitcoin", "crypto", "btc"],
     "a large metallic bitcoin coin with circuit-board lines"),
    (["bond", "bonds", "yield", "yields", "debt"],
     "a stack of bond certificates with no text"),
    (["oil", "crude", "wti", "brent", "opec"], "oil derricks and a barrel"),
    (["dollar", "usd", "dxy", "greenback"], "a stylized US dollar banknote"),
    (["silver", "xag"], "stacked silver bars"),
    (["gold", "xau", "bullion"], "stacked gold bars and a plain gold coin"),
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
    "crashes", "declines", "lower", "slips", "retreats",
]
MARKET_WORDS = [
    "price", "prices", "gold", "xau", "silver", "oil", "wti", "brent", "crude",
    "yield", "yields", "dollar", "dxy", "usd", "forex", "stocks", "equities",
    "s&p", "nasdaq", "bitcoin", "index", "futures", "markets", "market",
]


def _has(text, words):
    pat = "|".join(re.escape(w) for w in words)
    return re.search(r"(?<![a-z0-9])(?:" + pat + r")(?![a-z0-9])", text) is not None


def strip_arrows(scene):
    kept = []
    for part in re.split(r"[,;]", scene):
        p = part.strip()
        if not p:
            continue
        if re.search(r"\barrows?\b", p, re.I) and len(p.split()) <= 12:
            continue
        kept.append(p)
    return ", ".join(kept) or scene


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
    items = items[:5]
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
    scene = scene.replace("orange ", "").replace("Orange ", "").strip().rstrip(".")
    text = (headline + " " + scene).lower()
    chart = chart_text(text, impact)
    if chart:
        scene = strip_arrows(scene)
    return STYLE.format(
        bg=random.choice(BACKGROUNDS),
        scene=scene,
        subjects=subjects_text(text),
        chart=chart,
        layout=random.choice(LAYOUTS),
        extras=random.choice(EXTRAS),
    )


# ---- Public-domain portraits (Wikipedia / Wikimedia Commons) ----
WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKI_UA = {"User-Agent": "MarketCodeBot/1.0 (https://e11lab-projects.github.io/market-code-telegram)"}

# lowercase keywords in the headline -> exact Wikipedia article title
PEOPLE = [
    (["trump"], "Donald_Trump"),
]


def fetch_portrait(title):
    try:
        r = requests.get(WIKI_API, headers=WIKI_UA, timeout=30, params={
            "action": "query", "titles": title, "prop": "pageimages",
            "piprop": "name|thumbnail", "pithumbsize": 800,
            "redirects": 1, "format": "json"})
        r.raise_for_status()
        page = next(iter(r.json()["query"]["pages"].values()))
        fname = page.get("pageimage")
        thumb = page.get("thumbnail", {}).get("source")
        if not fname or not thumb:
            return None
        r = requests.get(COMMONS_API, headers=WIKI_UA, timeout=30, params={
            "action": "query", "titles": "File:" + fname, "prop": "imageinfo",
            "iiprop": "extmetadata", "format": "json"})
        r.raise_for_status()
        info = next(iter(r.json()["query"]["pages"].values())).get("imageinfo")
        if not info:
            return None
        lic = info[0].get("extmetadata", {}).get("LicenseShortName", {}).get("value", "").lower()
        if not ("public domain" in lic or "cc0" in lic or lic.startswith("pd")):
            print("Portrait skipped, license:", lic)
            return None
        r = requests.get(thumb, headers=WIKI_UA, timeout=60)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print("Portrait fetch failed:", e)
        return None


def add_person(img_bytes, text):
    text = text.lower()
    title = None
    for words, t in PEOPLE:
        if _has(text, words):
            title = t
            break
    if not title:
        return img_bytes
    face_bytes = fetch_portrait(title)
    if not face_bytes:
        return img_bytes
    try:
        from PIL import Image, ImageDraw, ImageOps

        base = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = base.size
        side = int(min(w, h) * 0.42)
        face = Image.open(io.BytesIO(face_bytes)).convert("L")
        face = ImageOps.autocontrast(face)
        face = ImageOps.fit(face, (side, side), centering=(0.5, 0.25)).convert("RGB")
        mask = Image.new("L", (side, side), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, side - 1, side - 1), fill=255)
        margin = int(side * 0.15)
        x, y = margin, h - side - margin
        pad = int(side * 0.1)
        draw = ImageDraw.Draw(base)
        draw.ellipse((x + pad, y - pad, x + side + pad, y + side - pad), fill=(16, 185, 129))
        draw.ellipse((x - 6, y - 6, x + side + 6, y + side + 6), fill=(255, 255, 255))
        base.paste(face, (x, y), mask)
        out = io.BytesIO()
        base.save(out, format="JPEG", quality=92)
        return out.getvalue()
    except Exception as e:
        print("Person overlay failed:", e)
        return img_bytes
