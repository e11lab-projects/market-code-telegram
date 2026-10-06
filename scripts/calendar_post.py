import os
import re
import json
import time
import datetime
import requests
from image_gen import generate_image
import webpage

CAL_URLS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
]
MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
]
IMPACTS = [
    x.strip() for x in os.environ.get("CAL_IMPACTS", "High").split(",") if x.strip()
]
WINDOW_HOURS = int(os.environ.get("CAL_WINDOW_HOURS", "24"))
HISTORY_FILE = "history.json"
DOCS = "../docs"
ICT = datetime.timezone(datetime.timedelta(hours=7))

KHMER_RULES = (
    "Also write a Khmer version for readers in Cambodia: headline_km, teaser_km, "
    "paragraphs_km (a list with the SAME number of paragraphs as paragraphs) and "
    "takeaways_km (3 bullet points). Write natural, clear Khmer that everyday "
    "readers understand, not word-for-word translation. Keep exactly the same "
    "facts. Keep market abbreviations and names in Latin letters (XAU/USD, Fed, "
    "CPI, NFP, FOMC, USD). Use Arabic digits 0-9, not Khmer numerals. Use these "
    "Khmer terms: gold = មាស; inflation = អតិផរណា; interest rate = "
    "អត្រាការប្រាក់; central bank = ធនាគារកណ្តាល; US dollar = ដុល្លារអាមេរិក; "
    "market = ទីផ្សារ; traders = អ្នកជួញដូរ. For other technical terms you are "
        "not sure about, keep the English term in Latin letters. Use ONLY Khmer "
    "script, plus Latin letters for names and abbreviations. Never use Thai, "
    "Vietnamese, Chinese or any other script.\n"
)


def text_of(v):
    return str(v or "").strip()


def as_list(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [p.strip() for p in str(v or "").split("\n") if p.strip()]


def set_output(posted):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"posted={'true' if posted else 'false'}\n")


def load_history():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history, entry):
    history.append(entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-80:], f, ensure_ascii=False, indent=2)


def fetch_events():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MarketCodeBot/1.0)"}
    for attempt in range(1, 4):
        for url in CAL_URLS:
            try:
                r = requests.get(url, headers=headers, timeout=30)
            except requests.RequestException as e:
                print("Calendar network error:", e)
                continue
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    print("Calendar returned something that is not JSON")
                    continue
            print("Calendar error:", r.status_code, url)
        time.sleep(20 * attempt)
    return None


def upcoming(events):
    now = datetime.datetime.now(datetime.timezone.utc)
    end = now + datetime.timedelta(hours=WINDOW_HOURS)
    picked = []
    for e in events:
        if e.get("country") != "USD" or e.get("impact") not in IMPACTS:
            continue
        try:
            when = datetime.datetime.fromisoformat(e["date"])
        except Exception:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.timezone.utc)
        if now <= when <= end:
            picked.append((when.astimezone(ICT), e))
    picked.sort(key=lambda x: x[0])
    return picked


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


def ask_gemini(lines):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY secret is empty or missing")
    prompt = (
        "You are the editor of THE MARKET CODE by E11 Lab, writing for gold "
        "(XAU/USD) traders.\n"
        "Write a heads-up post about the high-impact US economic events coming "
        "in the next hours, listed below. Times are Phnom Penh time. Forecast is "
        "the market consensus from an economic calendar and Previous is the last "
        "reading.\n"
        "Write headline, teaser, paragraphs and takeaways in English only. Khmer "
        "goes only in the fields that end in _km.\n"
        "Rules: use ONLY the events and numbers in the list; do not predict the "
        "actual result; do not invent numbers; never say buy or sell and never "
        "give entries, stops or targets; educational, calm tone.\n"
        "Explain why these events matter for gold (the US dollar, real yields and "
        "rate expectations). Give a balanced if/then view: a result stronger than "
        "forecast typically supports the dollar and yields and can pressure gold, "
        "while a weaker result typically does the opposite. Remind traders that "
        "volatility and spreads can widen around releases.\n"
        + KHMER_RULES +
        "Return ONLY JSON with these keys:\n"
        "headline: max 10 words;\n"
        "teaser: 2 short sentences, max 260 characters;\n"
        "paragraphs: a list of 2 to 3 paragraphs (about 150 to 250 words in total);\n"
        "takeaways: a list of exactly 3 short bullet points;\n"
        "headline_km, teaser_km, paragraphs_km, takeaways_km: the Khmer versions;\n"
        "image_subject: ONE scene description in English (max 35 words) for a "
        "collage illustration with a wall calendar or an alarm clock, plain gold "
        "bars with blank unmarked surfaces, a US dollar banknote or the Federal "
        "Reserve building, and a zigzag line showing volatility instead of an "
        "arrow. Do not mention colours. No text, numbers or people.\n\n"
        "EVENTS:\n" + "\n".join(lines)
    )
    data = call_gemini(key, prompt)
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def main():
    if not webpage.SITE_URL:
        raise RuntimeError("SITE_URL is not set")

    history = load_history()
    today = datetime.datetime.now(ICT).date().isoformat()
    key_link = f"calendar:{today}"
    if any(h.get("link") == key_link for h in history):
        print("Calendar post already published today. Skipping.")
        set_output(False)
        return

    events = fetch_events()
    if events is None:
        print("Calendar feed unavailable. Skipping.")
        set_output(False)
        return

    picked = upcoming(events)
    if not picked:
        print(f"No {'/'.join(IMPACTS)} impact USD events in the next {WINDOW_HOURS} hours. Skipping.")
        set_output(False)
        return

    lines = []
    extra = []
    for when, e in picked:
        title = text_of(e.get("title")) or "Event"
        fc = text_of(e.get("forecast")) or "n/a"
        pv = text_of(e.get("previous")) or "n/a"
        stamp = when.strftime("%a %H:%M")
        lines.append(f"{stamp} (Phnom Penh) — {title} · Forecast: {fc} · Previous: {pv}")
        extra.append(f"🕒 {stamp} · {title} (Forecast {fc} | Previous {pv})")
    print("Events:", *lines, sep="\n")

    post = ask_gemini(lines)
    print("Headline:", post["headline"])
    print("Khmer headline:", text_of(post.get("headline_km")) or "(missing)")
    print("Scene:", post["image_subject"])

    img, provider = generate_image(post["image_subject"])

    slug = f"{today}-{webpage.slugify(post['headline'])}"
    os.makedirs(os.path.join(DOCS, "news"), exist_ok=True)
    with open(os.path.join(DOCS, "news", slug + ".jpg"), "wb") as f:
        f.write(img)

    heading_en = "High-impact US events coming up (Phnom Penh time):"
    heading_km = "ព្រឹត្តិការណ៍សេដ្ឋកិច្ចអាមេរិកសំខាន់ៗដែលនឹងមកដល់ (ម៉ោងភ្នំពេញ)៖"
    p_en = [heading_en] + lines + as_list(post.get("paragraphs"))
    p_km = [heading_km] + lines + as_list(post.get("paragraphs_km"))

    article = {
        "slug": slug,
        "date": today,
        "headline": text_of(post["headline"]),
        "teaser": text_of(post["teaser"]),
        "headline_km": text_of(post.get("headline_km")),
        "teaser_km": text_of(post.get("teaser_km")),
        "impact": "",
        "source_name": "Economic calendar (Forex Factory feed)",
        "source_url": "https://www.forexfactory.com/calendar",
    }
    articles = webpage.load_articles(DOCS)
    articles.insert(0, article)
    webpage.save_articles(DOCS, articles)
    webpage.write_site(
        DOCS,
        article,
        p_en,
        as_list(post.get("takeaways")),
        p_km,
        as_list(post.get("takeaways_km")),
        articles,
    )

    last = {
        "headline": article["headline"],
        "teaser": article["teaser"],
        "headline_km": article["headline_km"],
        "teaser_km": article["teaser_km"],
        "impact": "",
        "impact_line": "Event risk: ⚠ Volatility possible",
        "extra": extra[:4],
        "url": f"{webpage.SITE_URL}/news/{slug}.html",
        "image_path": f"{DOCS}/news/{slug}.jpg",
    }
    with open("last_post.json", "w", encoding="utf-8") as f:
        json.dump(last, f, ensure_ascii=False, indent=2)

    save_history(
        history,
        {
            "date": today,
            "headline": article["headline"],
            "image_subject": post["image_subject"],
            "link": key_link,
        },
    )
    set_output(True)
    print(f"Calendar article built (image via {provider}):", last["url"])


main()
