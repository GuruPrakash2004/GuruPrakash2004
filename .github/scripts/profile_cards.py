"""Build animated GitHub stats cards for the profile README.

Runs inside GitHub Actions with the built-in GITHUB_TOKEN (no extra secrets).
Writes three SVGs into the output directory:
  stats.svg      - contributions, streaks, repos, stars, followers
  activity.svg   - animated area chart of the last 31 days
  languages.svg  - animated top-languages bars
Usage: python profile_cards.py <github_user> <out_dir>
       python profile_cards.py --demo <out_dir>   (fake data, for previewing)
"""
import datetime as dt
import json
import os
import random
import sys
import urllib.request
from xml.sax.saxutils import escape

FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
BG = """<defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#07111F"/><stop offset="1" stop-color="#0B1D36"/></linearGradient>
  </defs>
  <rect x=".75" y=".75" width="{w}" height="{h}" rx="16" fill="url(#bg)" stroke="#1E3A5F" stroke-width="1.5"/>"""

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""


def fetch(user):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    u = payload["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            size, color = langs.get(n, (0, e["node"]["color"] or "#8B949E"))
            langs[n] = (size + e["size"], color)
    return {
        "total": cal["totalContributions"],
        "days": days,
        "repos": u["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "langs": langs,
    }


def demo():
    today = dt.date.today()
    random.seed(4)
    days = [((today - dt.timedelta(days=i)).isoformat(), random.choice([0, 0, 1, 2, 3, 5, 8])) for i in range(364, -1, -1)]
    return {"total": sum(c for _, c in days), "days": days, "repos": 26, "stars": 9, "followers": 14,
            "langs": {"TypeScript": (520000, "#3178c6"), "Python": (310000, "#3572A5"), "JavaScript": (190000, "#f1e05a"),
                      "Java": (120000, "#b07219"), "Vue": (60000, "#41b883"), "HTML": (30000, "#e34c26")}}


def streaks(days):
    # A streak may still be "alive" if today has no contributions yet.
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    current = 0
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    while i >= 0 and counts[i] > 0:
        current += 1
        i -= 1
    return current, longest


def stats_svg(d):
    cur, best = streaks(d["days"])
    w, h = 495, 195
    items = [
        ("Contributions (last year)", d["total"], "#00C6FF"),
        ("Current streak", f"{cur} day{'s' if cur != 1 else ''}", "#EA1D2C"),
        ("Longest streak", f"{best} day{'s' if best != 1 else ''}", "#FFB547"),
        ("Public repos", d["repos"], "#3FB950"),
        ("Stars earned", d["stars"], "#A78BFA"),
        ("Followers", d["followers"], "#1769FF"),
    ]
    rows = []
    for i, (label, val, col) in enumerate(items):
        col_x = 28 if i < 3 else 262
        y = 78 + (i % 3) * 36
        delay = 0.25 + i * 0.12
        rows.append(f'''    <g class="in" style="animation-delay:{delay:.2f}s">
      <rect x="{col_x}" y="{y - 14}" width="4" height="20" rx="2" fill="{col}"/>
      <text x="{col_x + 14}" y="{y + 1}" fill="#8B949E" font-size="12.5">{escape(label)}</text>
      <text x="{col_x + 205}" y="{y + 1}" fill="#FFFFFF" font-size="15" font-weight="700" text-anchor="end">{escape(str(val))}</text>
    </g>''')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <style>
    .in {{ opacity: 0; animation: in .6s cubic-bezier(.2,.7,.2,1) forwards; }}
    @keyframes in {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: translateX(0); }} }}
    .flame {{ animation: flame 1.4s ease-in-out infinite; transform-origin: 462px 34px; transform-box: view-box; }}
    @keyframes flame {{ 0%,100% {{ transform: scale(1); }} 50% {{ transform: scale(1.18); }} }}
  </style>
  {BG.format(w=w - 1.5, h=h - 1.5)}
  <g font-family="{FONT}">
    <text x="28" y="38" fill="#FFFFFF" font-size="17" font-weight="700">GitHub Stats</text>
    <text x="148" y="38" fill="#00C6FF" font-size="12" font-family="{MONO}">@GuruPrakash2004</text>
    <g class="flame"><path d="M462 22 C470 30 470 38 462 46 C454 38 454 30 462 22 Z" fill="#EA1D2C"/><path d="M462 32 C466 36 466 41 462 45 C458 41 458 36 462 32 Z" fill="#FFB547"/></g>
    <line x1="28" y1="52" x2="{w - 28}" y2="52" stroke="#1E3A5F"/>
{chr(10).join(rows)}
  </g>
</svg>
'''


def activity_svg(d):
    days = d["days"][-31:]
    w, h = 900, 300
    left, right, top, bottom = 60, 45, 70, 50
    pw, ph = w - left - right, h - top - bottom
    mx = max([c for _, c in days] + [4])
    step = pw / (len(days) - 1)
    pts = [(left + i * step, top + ph - c / mx * ph) for i, (_, c) in enumerate(days)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"M{left},{top + ph} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" L{left + pw},{top + ph} Z"
    length = sum(((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5 for i in range(len(pts) - 1))
    grid = []
    for k in range(5):
        v = round(mx * k / 4)
        y = top + ph - k / 4 * ph
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + pw}" y2="{y:.1f}" stroke="#1B2B44"/>'
                    f'<text x="{left - 12}" y="{y + 4:.1f}" fill="#6E86A6" font-size="11" text-anchor="end">{v}</text>')
    labels = []
    for i, (date, _) in enumerate(days):
        if i % 5 == 0 or i == len(days) - 1:
            dd = dt.date.fromisoformat(date)
            labels.append(f'<text x="{pts[i][0]:.1f}" y="{h - 22}" fill="#6E86A6" font-size="11" text-anchor="middle">{dd.strftime("%d %b")}</text>')
    dots = []
    for i, (x, y) in enumerate(pts):
        delay = 0.3 + 2.2 * i / len(pts)
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#FFFFFF" stroke="#EA1D2C" stroke-width="2" class="dot" style="animation-delay:{delay:.2f}s"/>')
    total = sum(c for _, c in days)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <style>
    .dot {{ opacity: 0; animation: dot .3s ease-out forwards; }}
    @keyframes dot {{ to {{ opacity: 1; }} }}
    .area {{ opacity: 0; animation: area 1.2s ease-out 1.6s forwards; }}
    @keyframes area {{ to {{ opacity: 1; }} }}
  </style>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#07111F"/><stop offset="1" stop-color="#0B1D36"/></linearGradient>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00C6FF" stop-opacity=".45"/><stop offset="1" stop-color="#00C6FF" stop-opacity="0"/></linearGradient>
    <linearGradient id="stroke" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#00C6FF"/><stop offset="1" stop-color="#1769FF"/></linearGradient>
  </defs>
  <rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="16" fill="url(#bg)" stroke="#1E3A5F" stroke-width="1.5"/>
  <g font-family="{FONT}">
    <text x="{left - 30}" y="38" fill="#FFFFFF" font-size="17" font-weight="700">Contribution Activity</text>
    <text x="{w - right}" y="38" fill="#8B949E" font-size="13" text-anchor="end"><tspan fill="#00C6FF" font-weight="700">{total}</tspan> contributions in the last 31 days</text>
    {''.join(grid)}
    {''.join(labels)}
    <path class="area" d="{area}" fill="url(#fill)"/>
    <polyline points="{line}" fill="none" stroke="url(#stroke)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"
      stroke-dasharray="{length:.0f}" stroke-dashoffset="{length:.0f}">
      <animate attributeName="stroke-dashoffset" from="{length:.0f}" to="0" begin=".3s" dur="2.2s" fill="freeze"/>
    </polyline>
    {''.join(dots)}
  </g>
</svg>
'''


def languages_svg(d):
    w, h = 495, 195
    top = sorted(d["langs"].items(), key=lambda kv: -kv[1][0])[:6]
    total = sum(s for _, (s, _) in top) or 1
    bar_w = w - 56
    segs, x = [], 28.0
    for i, (name, (size, col)) in enumerate(top):
        sw = bar_w * size / total
        segs.append(f'<rect x="{x:.1f}" y="62" width="{sw:.1f}" height="10" fill="{col}" class="grow" style="animation-delay:{.2 + i * .12:.2f}s"/>')
        x += sw
    legend = []
    for i, (name, (size, col)) in enumerate(top):
        cx = 28 if i % 2 == 0 else 262
        y = 108 + (i // 2) * 28
        legend.append(f'''<g class="in" style="animation-delay:{.6 + i * .1:.2f}s"><circle cx="{cx + 5}" cy="{y - 4}" r="5" fill="{col}"/>
      <text x="{cx + 18}" y="{y + 1}" fill="#E6EDF3" font-size="13">{escape(name)}</text>
      <text x="{cx + 205}" y="{y + 1}" fill="#8B949E" font-size="12.5" text-anchor="end">{size / total * 100:.1f}%</text></g>''')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <style>
    .grow {{ transform: scaleX(0); transform-origin: 28px 0; transform-box: view-box; animation: grow 1.2s cubic-bezier(.2,.7,.2,1) forwards; }}
    @keyframes grow {{ to {{ transform: scaleX(1); }} }}
    .in {{ opacity: 0; animation: in .5s ease-out forwards; }}
    @keyframes in {{ to {{ opacity: 1; }} }}
  </style>
  {BG.format(w=w - 1.5, h=h - 1.5)}
  <clipPath id="bar"><rect x="28" y="62" width="{bar_w}" height="10" rx="5"/></clipPath>
  <g font-family="{FONT}">
    <text x="28" y="38" fill="#FFFFFF" font-size="17" font-weight="700">Most Used Languages</text>
    <rect x="28" y="62" width="{bar_w}" height="10" rx="5" fill="#1B2B44"/>
    <g clip-path="url(#bar)">{''.join(segs)}</g>
    {chr(10).join(legend)}
  </g>
</svg>
'''


def main():
    if sys.argv[1] == "--demo":
        data, out = demo(), sys.argv[2]
    else:
        data, out = fetch(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for name, fn in (("stats.svg", stats_svg), ("activity.svg", activity_svg), ("languages.svg", languages_svg)):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(fn(data))
    print("wrote stats.svg, activity.svg, languages.svg to", out)


if __name__ == "__main__":
    main()
