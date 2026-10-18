#!/usr/bin/env python3
"""Per-game third-down attempts for one Notre Dame season, from every source we can read.

    python3 tools/diag_third_downs.py [--season 2024]

Prints, per game: ESPN box score (thirdDownEff), ESPN play-by-play (ND offensive scrimmage plays
that started on 3rd down, with plays wiped out by an accepted penalty listed separately), and
cfbstats.com's per-game third-down rows where its pages give them, and Notre Dame's official
stat-crew box scores (fightingirish.com); then each source's season
total (ESPN team season statistics, cfbstats team page).  Diagnosis only: it writes nothing.
Needs network (run it in GitHub Actions, like collect.py).
"""
import argparse, io, json, os, re, sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import collect as C  # noqa: E402
import collect_tabs as CT  # noqa: E402

SCRIMMAGE = {"Rush", "Pass Reception", "Pass Incompletion", "Sack", "Passing Touchdown", "Rushing Touchdown",
             "Pass Interception Return", "Interception Return Touchdown", "Fumble Recovery (Own)",
             "Fumble Recovery (Opponent)", "Fumble Return Touchdown", "Safety"}


def espn_games(season):
    out = []
    for g in CT.espn_completed(C, C.ND_ESPN, season):
        j = C.get(f"{CT.ESPN}/summary?event={g['event']}").json()
        bt = {str(t["team"]["id"]): {s["name"]: s.get("displayValue") for s in t.get("statistics", [])} for t in j["boxscore"]["teams"]}
        conv, att = (int(x) for x in str(bt[C.ND_ESPN]["thirdDownEff"]).split("-"))
        plays, nullified, other = 0, [], {}
        for d in (j.get("drives") or {}).get("previous", []):
            if str(d.get("team", {}).get("id")) != C.ND_ESPN: continue
            for p in d.get("plays", []):
                if (p.get("start") or {}).get("down") != 3: continue
                k, txt = p.get("type", {}).get("text", "?"), p.get("text", "")
                if k in SCRIMMAGE:
                    if "Notre Dame Penalty" in txt and "declined" not in txt.lower():  # an accepted ND penalty may wipe out the play
                        nullified.append(f"Q{p['period']['number']} {p['clock']['displayValue']} {txt[:110]}")
                    plays += 1
                else:
                    other[k] = other.get(k, 0) + 1
        out.append({"date": g["date"], "opp": g["opp"], "event": g["event"], "box": (conv, att), "pbp": plays, "nullified": nullified, "other": other})
    return out


def cfb_tables(url):
    try:
        html = C.get(url).text
    except Exception as e:
        print(f"  {url}: not available ({e})"); return None, None
    try:
        return html, pd.read_html(io.StringIO(html))
    except ValueError:
        return html, []


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--season", type=int, default=2024); a = ap.parse_args()
    s, cid = a.season, C.ND_CFBSTATS
    print(f"== ESPN, Notre Dame {s}: box score vs play-by-play (3rd-down scrimmage plays)")
    games = espn_games(s)
    for g in games:
        flag = "" if g["pbp"] - len(g["nullified"]) == g["box"][1] else "   <-- box and play-by-play differ"
        print(f"{g['date']} {g['opp']:22} event {g['event']}  box {g['box'][0]}-{g['box'][1]}  pbp plays {g['pbp']}"
              f" (minus {len(g['nullified'])} with an accepted ND penalty = {g['pbp'] - len(g['nullified'])}){flag}  other: {g['other']}")
        for n in g["nullified"]: print(f"      ND penalty on the play: {n}")
    print(f"ESPN box total: {sum(g['box'][1] for g in games)} attempts, {sum(g['box'][0] for g in games)} conversions, {len(games)} games")

    print(f"\n== ESPN team season statistics {s}")
    for st in (2, 3, None):
        url = f"{CT.ESPN}/teams/{C.ND_ESPN}/statistics?season={s}" + (f"&seasontype={st}" if st else "")
        try:
            j = C.get(url).json()
            cats = j.get("results", {}).get("stats", {}).get("categories", []) or j.get("splits", {}).get("categories", [])
            for c in cats:
                for x in c.get("stats", []):
                    if "third" in x.get("name", "").lower(): print(f"  seasontype={st}: {x['name']} = {x.get('displayValue', x.get('value'))}")
        except Exception as e:
            print(f"  {url}: not available ({e})")

    print(f"\n== cfbstats {s} team {cid}: season totals")
    tt = CT.cfb_team_totals(C, s, cid)
    print(f"  through {tt['through']}: games {tt['totals']['games']}, third_att {tt['totals']['third_att']}, third_conv {tt['totals']['third_conv']}")

    for path in ("thirddown/offense/split.html", "thirddown/offense/gamelog.html", "gamelog.html", "total/index.html"):
        url = f"https://cfbstats.com/{s}/team/{cid}/{path}"
        print(f"\n== cfbstats {url}")
        html, tbs = cfb_tables(url)
        if tbs is None: continue
        for i, t in enumerate(tbs):
            with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_rows", 80):
                print(f"-- table {i} ({t.shape[0]}x{t.shape[1]})"); print(t.to_string())
        links = sorted(set(re.findall(r'href="(/%d/[^"]*(?:game|log)[^"]*)"' % s, html or "")))
        if links: print("  game/log links:", links[:40])
    official(s)


def official(season):
    """Notre Dame's official stat-crew box scores (fightingirish.com, Sidearm): the third-down row of each game."""
    base = "https://fightingirish.com"
    print(f"\n== Official box scores: {base}/sports/football/schedule/{season}")
    try:
        html = C.get(f"{base}/sports/football/schedule/{season}").text
    except Exception as e:
        print(f"  schedule not available ({e})"); return
    links = []
    for h in re.findall(r'href="([^"]*boxscore[^"]*)"', html):
        u = h if h.startswith("http") else base + h
        if u not in links: links.append(u)
    print(f"  {len(links)} box score links")
    for u in links:
        try:
            t = C.get(u).text
        except Exception as e:
            print(f"  {u}: not available ({e})"); continue
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))
        hits = re.findall(r"(3rd|Third)[- ][Dd]own [Cc]onversions?[^0-9]{0,40}(\d+)\s*[-/]\s*(\d+)[^0-9]{0,40}(\d+)\s*[-/]\s*(\d+)", txt)
        print(f"  {u.rsplit('/', 3)[-3:]}: " + ("; ".join(f"{h[1]}-{h[2]} | {h[3]}-{h[4]}" for h in hits[:2]) if hits else "no third-down row found"))


if __name__ == "__main__":
    main()
