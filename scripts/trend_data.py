import os
import requests

FRED = "https://api.stlouisfed.org/fred/series/observations"

# keyword in the event name -> (FRED series, label, how to read it)
SERIES = [
    ("core pce", "PCEPILFE", "Core PCE m/m %", "pct"),
    ("pce", "PCEPI", "PCE m/m %", "pct"),
    ("core cpi", "CPILFESL", "Core CPI m/m %", "pct"),
    ("cpi", "CPIAUCSL", "CPI m/m %", "pct"),
    ("non-farm", "PAYEMS", "Nonfarm payrolls monthly change (thousands)", "diff"),
    ("nonfarm", "PAYEMS", "Nonfarm payrolls monthly change (thousands)", "diff"),
    ("unemployment rate", "UNRATE", "Unemployment rate %", "level"),
    ("jobless claims", "ICSA", "Initial jobless claims", "level"),
    ("unemployment claims", "ICSA", "Initial jobless claims", "level"),
    ("retail sales", "RSAFS", "Retail sales m/m %", "pct"),
]


def _fred(series_id, limit=16):
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        return []
    r = requests.get(
        FRED,
        params={"series_id": series_id, "api_key": key, "file_type": "json",
                "sort_order": "desc", "limit": limit},
        timeout=30,
    )
    r.raise_for_status()
    obs = [(o["date"], float(o["value"]))
           for o in r.json()["observations"] if o["value"] not in (".", "")]
    return list(reversed(obs))  # oldest first


def _convert(obs, how):
    if how == "level":
        return obs
    out = []
    for i in range(1, len(obs)):
        d, v = obs[i]
        p = obs[i - 1][1]
        out.append((d, (v / p - 1) * 100 if how == "pct" else v - p))
    return out


def event_trend(event_name):
    name = event_name.lower()
    for key, sid, label, how in SERIES:
        if key in name:
            try:
                vals = _convert(_fred(sid), how)[-6:]
            except Exception as e:
                print("FRED error:", e)
                return ""
            if len(vals) < 4:
                return ""
            nums = [v for _, v in vals]
            recent = sum(nums[-3:]) / 3
            earlier = sum(nums[:3]) / 3
            move = "rising" if recent > earlier * 1.03 else "falling" if recent < earlier * 0.97 else "flat"
            line = ", ".join(f"{d[:7]}: {v:.2f}" for d, v in vals)
            return (f"{label} - last {len(vals)} readings: {line}. "
                    f"Average of the latest 3 = {recent:.2f}, earlier 3 = {earlier:.2f} ({move}). "
                    f"Source: FRED (St. Louis Fed).")
    return ""


def market_context():
    parts = []
    for sid, label in (("DGS10", "US 10-year Treasury yield %"),
                       ("T5YIE", "5-year inflation breakeven %")):
        try:
            obs = _fred(sid, 8)
        except Exception as e:
            print("FRED error:", e)
            continue
        if len(obs) >= 2:
            parts.append(f"{label}: latest {obs[-1][1]:.2f}, about a week earlier {obs[0][1]:.2f}.")
    return " ".join(parts) + (" Source: FRED." if parts else "")
