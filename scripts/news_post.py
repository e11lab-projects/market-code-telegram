import os
import json
import datetime
from io import BytesIO

from PIL import Image

from feeds import get_items
from gemini_client import call_gemini
from image_gen import generate_image
import webpage

LANG = os.environ.get("POST_LANGUAGE", "English")
ALERT_MIN = int(os.environ.get("ALERT_MIN_IMPACT", "6"))
SITE_MIN = int(os.environ.get("SITE_MIN_IMPACT", "3"))
STORIES_PER_RUN = int(os.environ.get("STORIES_PER_RUN", "2"))
MAX_SITE_PER_DAY = int(os.environ.get("MAX_SITE_PER_DAY", "20"))
MAX_ALERTS_PER_DAY = int(os.environ.get("MAX_ALERTS_PER_DAY", "8"))
HISTORY_FILE = "history.json"
DOCS = "../docs"

KHMER_RULES = (
    "Also write a Khmer version for readers in Cambodia: headline_km, teaser_km, "
    "article_km (a list with the SAME number of paragraphs as article) and "
    "takeaways_km (3 bullet points). Write natural, clear Khmer that everyday "
    "readers understand, not word-for-word translation. Keep exactly the same "
    "facts: add nothing and remove nothing. Keep market abbreviations and names in "
    "Latin letters (XAU/USD, Fed, CPI, NFP, FOMC, USD). Use Arabic digits 0-9, not "
    "Khmer numerals. Use these Khmer terms: gold = មាស; inflation = អតិផរណា; "
    "interest rate = អត្រាការប្រាក់; central bank = ធនាគារកណ្តាល; US dollar = "
    "ដុល្លារអាមេរិក; market = ទីផ្សារ; traders = អ្នកជួញដូរ. For other technical "
    "terms you are not sure about, keep the English term in Latin letters. "
    "Use ONLY Khmer script, plus Latin letters for names and abbreviations. "
    "Never use Thai, Vietnamese, Chinese or any other script.\n"
)


def as_list(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [p.strip() for p in str(v or "").split("\n") if p.strip()]


def text_of(v):
    return str(v or "").strip()


def set_output(posted, alert):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"posted={'true' if posted else 'false'}\n")
            f.write(f"alert={'true' if alert else 'false'}\n")


def load_history():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history, entry):
    history.append(entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-120:], f, ensure_ascii=False, indent=2)


def compress(data):
    try:
        im = Image.open(BytesIO(data)).convert("RGB")
        im.thumbnail((1024, 1024))
        out = BytesIO()
        im.save(out, "JPEG", quality=82, optimize=True)
        return out.getvalue()
    except Exception:
        return data


def build_prompt(items, history):
    recent = "\n".join(
        f"- {h['headline']} | image: {h['image_subject']}" for h in history[-14:]
    ) or "- (none yet)"
    listing = "\n".join(
        f"[{i}] (relevance {it['score']}) {it['title']} -- {it['summary']} ({it['source']})"
        for i, it in enumerate(items)
    )
    return (
        "You are the editor of THE MARKET CODE by E11 Lab, writing for gold "
        "(XAU/USD) traders. The website covers ALL news that can affect gold, "
        "including currencies and the wider economy. Telegram alerts are only "
        "for the biggest stories, so score honestly.\n"
        "Below are fresh news items from public feeds, each with an index, a "
        "keyword relevance score, a title and a short summary.\n"
        "Pick the ONE item with the biggest likely effect on gold (XAU/USD). "
        "Relevant topics: US data and Fed policy; inflation; the US dollar and "
        "major currencies (EUR, JPY, GBP, CNY and others) and exchange rates; "
        "Treasury and global bond yields; other central banks' policy and gold "
        "buying; oil and commodities; trade and tariffs; stock market stress; "
        "geopolitical or safe-haven events; gold-specific news. It must NOT be "
        "similar to the recently posted ones.\n"
        "impact_score guide (1 to 10): 8-10 = market-moving right now (Fed "
        "decisions, big CPI or jobs surprises, major geopolitical escalation, big "
        "gold-specific news); 5-7 = clearly relevant for gold today; 3-4 = useful "
        "background (non-US data, central bank speeches, currency moves with a "
        "modest link to gold); 1-2 = little or no link to gold. If an item has no "
        "concrete event or figure (it only says data was released), score it 4 "
        "or lower.\n"
        "Write ORIGINAL commentary in " + LANG + ". Use ONLY facts found in the "
        "chosen item's title and summary. Do not invent numbers, quotes, dates, "
        "events or price levels. Never copy sentences from the source.\n"
        "The article must cover: (1) what happened, facts only; (2) the "
        "transmission channel to gold, such as the US dollar, real yields and "
        "rate expectations, safe-haven demand, inflation hedging or central bank "
        "demand; (3) a balanced if/then view of what would typically support "
        "gold and what would pressure it; (4) what traders should watch next. "
        "Educational only: never say buy or sell, never give entries, stops or "
        "price targets, and never present a prediction as certain. Calm, "
        "professional tone.\n"
        + KHMER_RULES +
        "Return ONLY JSON with these keys:\n"
        "headline: max 10 words, news style;\n"
        "teaser: 2 short sentences, max 260 characters; the second sentence "
        "says why it matters for gold;\n"
        "article: a list of 4 to 6 paragraphs (about 250 to 400 words in total);\n"
        "takeaways: a list of exactly 3 short bullet points;\n"
        "headline_km, teaser_km, article_km, takeaways_km: the Khmer versions;\n"
        "gold_impact: one of bullish, bearish, mixed, neutral (the likely effect "
        "on gold);\n"
        "impact_score: integer from 1 to 10;\n"
        "image_subject: ONE scene description in English (max 35 words) for a "
        "collage illustration with these elements: plain gold bars with blank "
        "unmarked surfaces, the main subject of the story (for example the "
        "Federal Reserve building, a country map, coins or banknotes of the "
        "currencies involved, an oil rig, a factory), and ONE arrow showing the "
        "likely effect on gold: pointing up if bullish, down if bearish, "
        "sideways if mixed or neutral. Do not mention colours. Make the main "
        "subject look clearly different from the recent images listed below. No "
        "text, numbers or people;\n"
        "source_index: the integer index of the chosen item.\n\n"
        "RECENTLY POSTED (avoid repeating):\n" + recent + "\n\n"
        "FRESH ITEMS:\n" + listing
    )


def ask_gemini(items, history):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY secret is empty or missing")
    data = call_gemini(key, build_prompt(items, history))
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def make_image(scene, impact):
    try:
        return generate_image(scene, impact)
    except TypeError:
        return generate_image(scene)


def main():
    if not webpage.SITE_URL:
        raise RuntimeError("SITE_URL is not set")

    history = load_history()
    today = datetime.date.today().isoformat()
    site_today = sum(1 for h in history if h.get("date") == today)
    alerts_today = sum(
        1 for h in history if h.get("date") == today and h.get("alert")
    )
    if site_today >= MAX_SITE_PER_DAY:
        print(f"Daily site limit reached ({site_today}/{MAX_SITE_PER_DAY}). Skipping.")
        set_output(False, False)
        return

    items = get_items(history)
    if not items:
        print("No fresh relevant items found. Skipping.")
        set_output(False, False)
        return

    articles = webpage.load_articles(DOCS)
    alerts = []
    published = 0
    used = set()

    for _ in range(STORIES_PER_RUN):
        if site_today + published >= MAX_SITE_PER_DAY:
            break
        pool = [i for i in items if i["link"] not in used]
        if not pool:
            break

        post = ask_gemini(pool, history)
        try:
            score = int(post.get("impact_score", 0))
        except Exception:
            score = 0
        if score < SITE_MIN:
            print(f"Stopped: best remaining story scored {score} (below {SITE_MIN}).")
            break

        try:
            idx = int(post.get("source_index", 0))
        except Exception:
            idx = 0
        if not 0 <= idx < len(pool):
            idx = 0
        src = pool[idx]
        used.add(src["link"])

        impact = text_of(post.get("gold_impact", "mixed")).lower()
        if impact not in ("bullish", "bearish", "mixed", "neutral"):
            impact = "mixed"

        is_alert = score >= ALERT_MIN and alerts_today + len(alerts) < MAX_ALERTS_PER_DAY
        print("Story:", post["headline"], "| score:", score, "| impact:", impact,
              "| alert:", is_alert)
        print("Khmer headline:", text_of(post.get("headline_km")) or "(missing)")

        img, provider = make_image(post["image_subject"], impact)
        img = compress(img)

        slug = f"{today}-{webpage.slugify(post['headline'])}"
        os.makedirs(os.path.join(DOCS, "news"), exist_ok=True)
        with open(os.path.join(DOCS, "news", slug + ".jpg"), "wb") as f:
            f.write(img)

        article = {
            "slug": slug,
            "date": today,
            "headline": text_of(post["headline"]),
            "teaser": text_of(post["teaser"]),
            "headline_km": text_of(post.get("headline_km")),
            "teaser_km": text_of(post.get("teaser_km")),
            "impact": impact,
            "source_name": src["source"],
            "source_url": src["link"] or "#",
        }
        articles.insert(0, article)
        webpage.save_articles(DOCS, articles)
        webpage.write_site(
            DOCS,
            article,
            as_list(post["article"]),
            as_list(post["takeaways"]),
            as_list(post.get("article_km")),
            as_list(post.get("takeaways_km")),
            articles,
        )

        if is_alert:
            alerts.append(
                {
                    "headline": article["headline"],
                    "teaser": article["teaser"],
                    "headline_km": article["headline_km"],
                    "teaser_km": article["teaser_km"],
                    "impact": impact,
                    "url": f"{webpage.SITE_URL}/news/{slug}.html",
                    "image_path": f"{DOCS}/news/{slug}.jpg",
                }
            )

        save_history(
            history,
            {
                "date": today,
                "headline": article["headline"],
                "image_subject": post["image_subject"],
                "link": src["link"],
                "alert": is_alert,
            },
        )
        published += 1
        print(f"Published (image via {provider}):", slug)

    if alerts:
        with open("last_post.json", "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)

    set_output(published > 0, bool(alerts))
    print(f"Done: {published} stories on the site, {len(alerts)} Telegram alerts.")


main()
