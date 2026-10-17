#!/usr/bin/env python3
"""Find and prove the ESPN athlete id of every roster.json quarterback whose espn_id is empty.

    python3 tools/resolve_espn_ids.py [--write] [--current-first N:CMP/ATT/YDS/TD/INT]

Candidates come only from ESPN itself, exact name matches: the Notre Dame roster
for that season (site API, teams/87/roster?season=YYYY; empty for past seasons),
ESPN's player search, and the passing tables of ESPN's box scores of Notre Dame's
first games that season.  A candidate is accepted only if his ESPN game log for that season
(collect.espn_gamelog, so every row also passes the passer-rating check) proves it:
  - a completed season must sum exactly to the entry's final_totals;
  - the current season's first N games must sum exactly to --current-first, when given.
Exactly one candidate must pass; otherwise the entry is reported and left empty, and
the script exits 1.  --write stores the proven ids in roster.json.  Needs network
(run it in GitHub Actions, like collect.py).  Run once when a QB is added.
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import collect as C  # noqa: E402


def roster_ids(season, name):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{C.ND_ESPN}/roster?season={season}"
    out = set()
    try:
        j = C.get(url).json()
    except Exception as e:
        print(f"  roster {season}: not available ({e})"); return out
    for grp in j.get("athletes", []):
        for a in grp.get("items", []) if isinstance(grp, dict) and "items" in grp else [grp]:
            if (a.get("displayName") or a.get("fullName", "")).lower() == name.lower(): out.add(str(a["id"]))
    print(f"  roster {season}: {sorted(out) or 'no exact match'}")
    return out


def search_ids(name):
    url = "https://site.web.api.espn.com/apis/common/v3/search"
    out = set()
    try:
        j = C.get(url, params={"query": name, "type": "player", "sport": "football", "league": "college-football", "limit": 10}).json()
    except Exception as e:
        print(f"  search: not available ({e})"); return out
    for it in j.get("items", []) + [x for g in j.get("results", []) for x in g.get("contents", [])]:
        nm = it.get("displayName") or it.get("name")
        if nm and nm.lower() == name.lower():
            out.add(str(it.get("id") or it.get("uid", "").split("~a:")[-1]))
    print(f"  search: {sorted(out) or 'no exact match'}")
    return out


def boxscore_ids(season, name, games=4):
    """ESPN box scores of Notre Dame's first completed games that season: passers whose name matches exactly.
    Used because ESPN's roster endpoint returns empty lists for past seasons."""
    import collect_tabs as CT
    out = set()
    try:
        done = CT.espn_completed(C, C.ND_ESPN, season)[:games]
    except Exception as e:
        print(f"  box scores {season}: schedule not available ({e})"); return out
    for g in done:
        try:
            j = C.get(f"{CT.ESPN}/summary?event={g['event']}").json()
        except Exception as e:
            print(f"  box score {g['date']}: not available ({e})"); continue
        for side in j.get("boxscore", {}).get("players", []):
            if str(side.get("team", {}).get("id")) != C.ND_ESPN: continue
            for st in side.get("statistics", []):
                if st.get("name") != "passing": continue
                for a in st.get("athletes", []):
                    if a["athlete"].get("displayName", "").lower() == name.lower(): out.add(str(a["athlete"]["id"]))
    print(f"  box scores {season} ({len(done)} games): {sorted(out) or 'no exact match'}")
    return out


def proves(q, pid, first):
    try:
        rows = C.espn_gamelog(pid, season=q["season"])
    except Exception as e:
        return False, f"game log unreadable or failed the rating check ({e})"
    seen = set(); rows = [r for r in rows if not (r["espn_event"] in seen or seen.add(r["espn_event"]))]
    keys = ["cmp", "att", "yds", "td", "int"]
    if q.get("final_totals"):
        got = {k: sum(r[k] for r in rows) for k in q["final_totals"]}
        return got == q["final_totals"], f"{len(rows)} games, totals {got} vs final_totals {q['final_totals']}"
    if first:
        n, want = first
        got = [sum(r[k] for r in rows[:n]) for k in keys]
        rest = [sum(r[k] for r in rows) for k in keys]
        return len(rows) >= n and got == want, f"first {n} of {len(rows)} games {got} vs {want}; all games {rest}"
    return bool(rows), f"{len(rows)} games (no totals to reconcile; give --current-first)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--current-first", help="N:CMP/ATT/YDS/TD/INT the current QB's first N games must sum to")
    a = ap.parse_args()
    first = None
    if a.current_first:
        n, line = a.current_first.split(":"); first = (int(n), [int(x) for x in line.split("/")])
    path = os.path.join(ROOT, "roster.json")
    roster = json.load(open(path, encoding="utf-8"))
    cur_season = max(q["season"] for q in roster["qbs"])
    bad = []
    for q in roster["qbs"]:
        if q.get("espn_id"): print(f"{q['key']}: espn_id {q['espn_id']} already set"); continue
        print(f"{q['key']} ({q['name']} {q['season']}):")
        cands = roster_ids(q["season"], q["name"]) | search_ids(q["name"]) | boxscore_ids(q["season"], q["name"])
        ok = []
        for pid in sorted(cands):
            good, why = proves(q, pid, first if q["season"] == cur_season else None)
            print(f"  candidate {pid}: {'PROVEN' if good else 'rejected'}: {why}")
            if good: ok.append(pid)
        if len(ok) == 1: q["espn_id"] = ok[0]; print(f"  -> {q['key']} espn_id = {ok[0]}")
        else: bad.append(q["key"]); print(f"  -> NOT RESOLVED ({len(ok)} candidates proven)")
    if a.write:
        open(path, "w", encoding="utf-8").write(json.dumps(roster, indent=1, ensure_ascii=False) + "\n")
        print("roster.json written")
    if bad: print("UNRESOLVED: " + ", ".join(bad)); sys.exit(1)


if __name__ == "__main__":
    main()
