"""Generate assets/stats.svg and assets/langs.svg from the GitHub GraphQL API.

Usage: GH_TOKEN=... python3 scripts/gen_stats.py [login]
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

LOGIN = sys.argv[1] if len(sys.argv) > 1 else "chethanyadav456"
TOKEN = os.environ["GH_TOKEN"]
G, BG = "#00ff41", "#0d1117"
MONO = "'SF Mono','Fira Code',Consolas,'Courier New',monospace"
LANG_COLORS = {"Python": "#3572A5", "Go": "#00ADD8", "TypeScript": "#3178C6", "JavaScript": "#f1e05a",
               "Shell": "#89e051", "Java": "#b07219", "C": "#555555", "Jupyter Notebook": "#DA5B0B",
               "HTML": "#e34c26", "CSS": "#563d7c", "Batchfile": "#C1F12E", "Dockerfile": "#384d54"}


def gql(query, **variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]


info = gql("""query($l:String!){user(login:$l){createdAt followers{totalCount}
  pullRequests(states:MERGED){totalCount} issues{totalCount}
  repositories(ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false,first:100){totalCount
    nodes{stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}""",
           l=LOGIN)["user"]
start = datetime.fromisoformat(info["createdAt"].replace("Z", "+00:00")).year
total = 0
for year in range(start, datetime.now(timezone.utc).year + 1):
    total += gql("""query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){contributionsCollection(from:$f,to:$t)
      {contributionCalendar{totalContributions}}}}""", l=LOGIN, f=f"{year}-01-01T00:00:00Z",
                 t=f"{year}-12-31T23:59:59Z")["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

repos = info["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
langs = {}
for r in repos:
    for e in r["languages"]["edges"]:
        langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
# notebooks and markup say little about what I write, so leave them out
SKIP = {"Jupyter Notebook", "EJS", "CSS", "HTML", "SCSS", "Batchfile"}
top = sorted(((k, v) for k, v in langs.items() if k not in SKIP), key=lambda kv: -kv[1])[:6]
tot_bytes = sum(v for _, v in top) or 1

# ---- stats.svg ----
cards = [("CONTRIBUTIONS", f"{total:,}"), ("PUBLIC REPOS", str(info["repositories"]["totalCount"])),
         ("STARS EARNED", str(stars)), ("PRS MERGED", str(info["pullRequests"]["totalCount"])),
         ("FOLLOWERS", str(info["followers"]["totalCount"]))]
cw = 168
parts = []
for i, (label, val) in enumerate(cards):
    x = 12 + i * (cw + 9)
    parts.append(f'''<g style="animation:up .7s ease-out {i*0.12:.2f}s both">
<rect x="{x}" y="12" width="{cw}" height="96" rx="10" fill="#0d1117" stroke="{G}" stroke-opacity=".35"/>
<text x="{x+cw/2}" y="62" text-anchor="middle" font-size="32" font-weight="700" fill="{G}">{val}</text>
<text x="{x+cw/2}" y="90" text-anchor="middle" font-size="11" letter-spacing="2" fill="#8b949e">{label}</text></g>''')
stats = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="120" viewBox="0 0 900 120" font-family="{MONO}">
<style>@keyframes up{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}</style>
{"".join(parts)}</svg>'''
open("assets/stats.svg", "w").write(stats)

# ---- langs.svg ----
rows, y = [], 52
for i, (name, size) in enumerate(top):
    pct = size / tot_bytes * 100
    col = LANG_COLORS.get(name, "#8b949e")
    w = max(4, pct / 100 * 560)
    rows.append(f'''<text x="24" y="{y+12}" font-size="13" fill="#c9d1d9">{name}</text>
<rect x="190" y="{y}" width="560" height="14" rx="7" fill="#161b22"/>
<rect x="190" y="{y}" width="{w:.0f}" height="14" rx="7" fill="{col}" style="transform-origin:190px 0;animation:grow 1.2s ease-out {i*0.1:.1f}s both"/>
<text x="768" y="{y+12}" font-size="13" fill="{G}">{pct:.1f}%</text>''')
    y += 30
height = y + 16
langs_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" font-family="{MONO}">
<style>@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}</style>
<rect x=".5" y=".5" width="899" height="{height-1}" rx="12" fill="{BG}" stroke="{G}" stroke-opacity=".35"/>
<text x="24" y="30" font-size="13" fill="{G}">$ git log --stat | top-languages --public</text>
{"".join(rows)}</svg>'''
open("assets/langs.svg", "w").write(langs_svg)
print(total, stars, top)
