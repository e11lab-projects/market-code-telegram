import re
import html
import time
import calendar
import feedparser

FEEDS = [
    # Official sources
    "https://www.federalreserve.gov/feeds/press_monetary.xml",
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://www.federalreserve.gov/feeds/speeches.xml",
    "https://www.bls.gov/feed/bls_latest.rss",
    "https://www.ecb.europa.eu/rss/press.html",
    "https://www.bankofengland.co.uk/rss/news",
    "https://www.boj.or.jp/en/rss/whatsnew.xml",
    # Markets, economy and world
    "http://feeds.bbci.co.uk/news/business/rss.xml",
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
    "https://finance.yahoo.com/news/rssindex",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F&region=US&lang=en-US",
]

MAX_AGE_HOURS = 36
USER_AGENT = "Mozilla/5.0 (compatible; MarketCodeBot/1.0)"

KEYWORDS = {
    "gold": 5, "xau": 5, "bullion": 4, "safe haven": 3, "safe-haven": 3,
    "fed": 3, "fomc": 4, "powell": 3, "federal reserve": 3,
    "rate cut": 3, "rate hike": 3, "interest rate": 2, "monetary policy": 2,
    "inflation": 3, "cpi": 4, "pce": 4, "ppi": 3,
    "payroll": 4, "nonfarm": 4, "jobs report": 4, "unemployment": 2, "jobless": 2,
    "treasury": 2, "yield": 2, "bond": 1, "dollar": 2, "dxy": 3,
    "currency": 2, "currencies": 2, "forex": 2, "exchange rate": 2,
    "euro": 1, "yen": 2, "pound": 1, "sterling": 1, "yuan": 2, "franc": 1,
    "central bank": 2, "ecb": 2, "boj": 2, "boe": 2, "pboc": 3,
    "bank of england": 2, "bank of japan": 2,
    "tariff": 2, "trade war": 2, "sanction": 2, "war": 2, "ceasefire": 2,
    "iran": 2, "hormuz": 3, "israel": 1, "ukraine": 1, "russia": 1, "china": 1,
    "oil": 1, "crude": 1, "opec": 1, "recession": 2, "gdp": 2, "pmi": 2,
    "retail sales": 1, "consumer confidence": 1, "trade deficit": 1,
    "debt ceiling": 2, "shutdown": 2,
}


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def score(text):
    t = text.lower()
    total = 0
    for word, weight in KEYWORDS.items():
        if re.search(r"\b" + re.escape(word) + r"s?\b", t):
            total += weight
    return total


def is_fresh(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return True
    return (time.time() - calendar.timegm(t)) < MAX_AGE_HOURS * 3600


def get_items(history):
    posted = {h.get("link") for h in history if h.get("link")}
    items = []
    seen = set()
    for url in FEEDS:
        try:
            feed = feedparser.parse(url, agent=USER_AGENT)
        except Exception as e:
            print(f"{url} -> failed: {e}")
            continue
        print(f"{url} -> {len(feed.entries)} items")
        source = clean(feed.feed.get("title", "")) or url.split("/")[2]
        for e in feed.entries[:15]:
            title = clean(e.get("title"))
            link = e.get("link", "")
            if not title or title.lower() in seen or link in posted or not is_fresh(e):
                continue
            seen.add(title.lower())
            summary = clean(e.get("summary"))[:500]
            items.append(
                {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "source": source,
                    "score": score(title + " " + summary),
                }
            )
    items = [i for i in items if i["score"] > 0]
    items.sort(key=lambda i: i["score"], reverse=True)
    return items[:30]
