#!/usr/bin/env python3
"""
Wausau 7-Day Forecast card -> snapshots/weather-today.png
Source: National Weather Service (free, no key). Rendered with Playwright/Chromium.

Run locally:   python -m playwright install chromium && python generate_weather_card.py
In CI:         see .github/workflows/weather-widget.yml
"""
import json, urllib.request, datetime as dt, pathlib
from playwright.sync_api import sync_playwright

LAT, LON = 44.9591, -89.6301
UA = "WausauPilotReview-weather-widget (editor@wausaupilotandreview.com)"
OUT = pathlib.Path("snapshots/weather-today.png")

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/geo+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

# --- fetch (fail fast: any error stops the run, no stale fallback) ---
fc_url = get(f"https://api.weather.gov/points/{LAT},{LON}")["properties"]["forecast"]
periods = get(fc_url)["properties"]["periods"]
alerts = get(f"https://api.weather.gov/alerts/active?point={LAT},{LON}")["features"]

# --- pair day/night into 7 calendar days ---
nights = {p["startTime"][:10]: p for p in periods if not p["isDaytime"]}
days = [(p["startTime"][:10], p, nights.get(p["startTime"][:10])) for p in periods if p["isDaytime"]][:7]
today = dt.date.fromisoformat(days[0][0])

def classify(text):
    t = text.lower(); light = "slight chance" in t or "chance" in t
    if "thunder" in t: return ("scattered", "Scattered storms") if light else ("storm", "Storms")
    if "shower" in t or "rain" in t: return ("rain", "Chance of rain") if light else ("rain", "Showers")
    if "snow" in t: return ("snow", "Snow")
    if "sunny" in t or "clear" in t:
        if "mostly sunny" in t: return ("partly", "Mostly sunny")
        if "partly sunny" in t: return ("partly", "Partly sunny")
        return ("sun", "Sunny")
    if "cloud" in t: return ("partly", "Partly cloudy") if "partly" in t else ("cloud", "Cloudy")
    return ("partly", text.split(" then ")[0][:18])

def icon(kind):
    rays = lambda cx, cy, r, ln: "".join(
        f'<rect x="{cx-1.3}" y="{cy-r-ln}" width="2.6" height="{ln}" rx="1.3" fill="#F6A623" transform="rotate({a} {cx} {cy})"/>'
        for a in range(0, 360, 45))
    sun = f'<circle cx="32" cy="32" r="13" fill="#F6A623"/>' + rays(32, 32, 14, 8)
    cloud = '<path d="M20 44a11 11 0 0 1 1-21 15 15 0 0 1 28 4 9 9 0 0 1-1 17z" fill="#AEB7BF"/>'
    smallsun = '<circle cx="23" cy="23" r="9" fill="#F6A623"/>' + rays(23, 23, 10, 6)
    bolt = '<path d="M34 44l-7 10h6l-3 8 10-12h-6l3-6z" fill="#F6A623"/>'
    if kind == "sun": body = sun
    elif kind == "cloud": body = cloud
    elif kind == "partly": body = smallsun + '<path d="M24 47a10 10 0 0 1 1-19 13 13 0 0 1 25 4 8 8 0 0 1-1 15z" fill="#AEB7BF"/>'
    elif kind == "rain": body = cloud + "".join(f'<line x1="{x}" y1="46" x2="{x-3}" y2="56" stroke="#3A6EA5" stroke-width="3" stroke-linecap="round"/>' for x in (24, 33, 42))
    elif kind == "storm": body = cloud + bolt
    elif kind == "scattered": body = smallsun + '<path d="M24 47a10 10 0 0 1 1-19 13 13 0 0 1 25 4 8 8 0 0 1-1 15z" fill="#AEB7BF"/>' + bolt
    elif kind == "snow": body = cloud + "".join(f'<circle cx="{x}" cy="52" r="2.4" fill="#7FA8C9"/>' for x in (24, 33, 42))
    else: body = cloud
    return f'<svg viewBox="0 0 64 64" width="32" height="32">{body}</svg>'

drop = '<svg width="13" height="15" viewBox="0 0 13 15" style="vertical-align:-2px;"><path d="M6.5 1C3 6 1 8.5 1 10.5a5.5 5.5 0 0 0 11 0C12 8.5 10 6 6.5 1z" fill="#3A6EA5"/></svg>'

rows = ""
for n, (d, dp, np_) in enumerate(days):
    date = dt.date.fromisoformat(d)
    lab = "TODAY" if date == today else date.strftime("%a").upper()
    hi = dp["temperature"]; lo = np_["temperature"] if np_ else "--"
    pop = dp.get("probabilityOfPrecipitation", {}).get("value")
    kind, label = classify(dp["shortForecast"])
    bg = "#f1ece0" if n % 2 else "#f8f4ea"
    pcell = f'{drop}<span style="color:#3A6EA5;font-weight:700;margin-left:3px;">{pop}%</span>' if pop else ""
    rows += f'''<tr style="background:{bg};">
      <td style="padding:7px 0 7px 16px;font-family:Oswald,sans-serif;font-weight:700;letter-spacing:1px;font-size:15px;color:#1a1a1a;width:78px;">{lab}</td>
      <td style="width:44px;text-align:center;">{icon(kind)}</td>
      <td style="font-family:'Source Sans 3',Arial,sans-serif;font-size:14px;color:#5b5b5b;">{label}</td>
      <td style="font-family:'Source Sans 3',Arial,sans-serif;font-size:13px;text-align:right;width:62px;white-space:nowrap;">{pcell}</td>
      <td style="padding-right:16px;text-align:right;width:96px;font-family:Merriweather,Georgia,serif;"><span style="font-size:21px;font-weight:700;color:#1a1a1a;">{hi}&deg;</span> <span style="font-size:15px;color:#9a9384;">{lo}&deg;</span></td>
    </tr>'''

banner = ""
if alerts:
    p = alerts[0]["properties"]; ends = p.get("ends", ""); endtxt = ""
    if ends:
        try: endtxt = " &middot; through " + dt.datetime.fromisoformat(ends).strftime("%a, %b %-d")
        except Exception: pass
    banner = (f'<div style="background:#b3261e;color:#fff;padding:9px 16px;font-family:Oswald,sans-serif;'
              f'font-size:15px;font-weight:700;letter-spacing:.5px;">'
              f'<svg viewBox="0 0 24 24" width="16" height="16" style="vertical-align:-3px;">'
              f'<path d="M12 2L1 21h22L12 2z" fill="#fff"/><path d="M12 9v6M12 17.5v.4" stroke="#b3261e" stroke-width="2.4" stroke-linecap="round"/></svg>'
              f'&nbsp;{p["event"].upper()}{endtxt}</div>')

start = today.strftime("%a, %b %-d"); end = dt.date.fromisoformat(days[-1][0]).strftime("%a, %b %-d")
html = f'''<!doctype html><html><head><meta charset="utf-8">
<style>@import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@700&family=Oswald:wght@600;700&family=Source+Sans+3:wght@400;600;700&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;}} body{{width:536px;}}
.card{{width:536px;background:#f8f4ea;border:1px solid #e3dccb;border-radius:8px;overflow:hidden;}}
table{{width:100%;border-collapse:collapse;}}</style></head>
<body><div class="card">
  <div style="height:5px;background:#3A867C;"></div>
  <div style="padding:13px 16px 9px;">
    <div style="font-family:Oswald,sans-serif;letter-spacing:2px;font-size:11px;font-weight:700;color:#3A867C;">WEATHER &middot; WAUSAU, WISCONSIN</div>
    <div style="font-family:Merriweather,Georgia,serif;font-size:26px;font-weight:700;color:#1a1a1a;line-height:1.1;margin-top:2px;">7-Day Forecast</div>
    <div style="font-family:'Source Sans 3',Arial,sans-serif;font-size:13px;color:#9a9384;margin-top:2px;">{start} &ndash; {end}</div>
  </div>
  {banner}
  <table>{rows}</table>
  <div style="display:flex;justify-content:space-between;align-items:center;padding:9px 16px 11px;border-top:1px solid #e3dccb;">
    <div style="font-family:'Source Sans 3',Arial,sans-serif;font-size:10px;color:#9a9384;">Source: National Weather Service &middot; Updated {today.strftime('%b %-d, %Y')}</div>
    <div style="text-align:right;font-family:'Source Sans 3',Arial,sans-serif;font-size:9px;color:#9a9384;">Weather sponsored by<br><img src="https://wausaupilotandreview.com/wp-content/uploads/2024/02/PK_butterfly-2024-336x137.jpg" width="110" style="margin-top:2px;"></div>
  </div>
</div></body></html>'''

OUT.parent.mkdir(parents=True, exist_ok=True)
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_context(device_scale_factor=2, viewport={"width": 536, "height": 900}).new_page()
    pg.set_content(html, wait_until="networkidle")
    pg.locator(".card").screenshot(path=str(OUT))
    b.close()
print(f"wrote {OUT}  ({len(days)} days, alert={bool(alerts)})")
