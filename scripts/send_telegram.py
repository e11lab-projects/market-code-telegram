import os
import json
import html
import time
import requests

LABELS = {
    "bullish": "▲ Bullish",
    "bearish": "▼ Bearish",
    "mixed": "◆ Mixed",
    "neutral": "● Neutral",
}


def build_caption(post):
    if post.get("impact_line"):
        impact_html = f"<b>{html.escape(post['impact_line'])}</b>"
    else:
        label = LABELS.get(post.get("impact", "mixed"), "◆ Mixed")
        impact_html = f"<b>XAU/USD impact:</b> {label}"

    extra = "\n".join(html.escape(x) for x in post.get("extra", [])[:4])
    extra_block = f"{extra}\n\n" if extra else ""
    url = html.escape(post["url"], quote=True)

    return (
        f"<b>{html.escape(post['headline'])}</b>\n\n"
        f"{html.escape(post['teaser'])}\n\n"
        f"{extra_block}"
        f"{impact_html}\n\n"
        f'<a href="{url}">Read More👈</a>'
    )


def send(post):
    with open(post["image_path"], "rb") as img:
        r = requests.post(
            f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto",
            data={
                "chat_id": os.environ["TELEGRAM_CHAT_ID"],
                "caption": build_caption(post),
                "parse_mode": "HTML",
            },
            files={"photo": ("image.jpg", img, "image/jpeg")},
            timeout=60,
        )
    if r.status_code != 200:
        print("Telegram error:", r.status_code, r.text[:300])
        r.raise_for_status()
    print("Sent to Telegram:", post["url"])


with open("last_post.json", encoding="utf-8") as f:
    data = json.load(f)

posts = data if isinstance(data, list) else [data]
for i, post in enumerate(posts):
    if i:
        time.sleep(4)
    send(post)
