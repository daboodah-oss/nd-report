# ND Football Report ("Fighting Irish 2026")

Notre Dame's current season against the earlier Freeman-era seasons, lined up by game number (Game 1 vs Game 1, and so on), on four tabs.  The site title is `site_title` in `roster.json` ("Fighting Irish {season}"), so it becomes "Fighting Irish 2027" on its own when the 2027 QB is added.

This repo is a replica of the IU Football Report (https://qb.daboodah.com/, repo `daboodah-oss/iu-qb-report`) adapted to Notre Dame: same files, same data-file names, same pipeline, same validation.  Either repo can be picked up cold from its own docs.

- **QB:** the current starter against every earlier Freeman-era starter (Carr ’26 vs Carr ’25 and Leonard 2024), plus national leaderboards, the Heisman field, and BetMGM Heisman odds.  `roster.json` has one entry per season, not per person: CJ Carr started 2025 and 2026, so his two seasons are separate entries (`carr25`, `carr26`) whose shorts ("Carr ’25", "Carr ’26") keep every legend, pill, table and game log unambiguous.
- **RB:** the current season's top 2 running backs by rushing yards (named in `roster.json`, from the collected data) against each earlier season's top 2 RBs by rushing yards.  Rushing yards, rushing TD, yards per carry, yards per game, plus national top-5 boards with both current backs' ranks.  RB position only: Leonard led the 2024 team in carries, but a QB's rushing is on the QB tab.
- **WR:** the current season's top 2 WR/TE by receiving yards against each earlier season's top 2 WR/TE by receiving yards.  Receptions, receiving yards, receiving TD, yards per catch, yards per game, plus national top-5 boards.
- **Team:** Notre Dame's current season against its earlier Freeman-era seasons and the current AP Top 5 (the poll's week and release date are shown).  Record, points scored and allowed, total, rushing and passing yards, turnover margin, third-down %.

Each compare chart (QB, RB, WR) can also draw gray national reference lines, from two collapsible sections under "ND players": **National Top 3** (the top three non-Notre Dame players at that position in the stat being viewed; the chips change with the stat and start off) and **Individual player** (search a pool of roughly the top 20 per tracked stat, then add or remove players as pills).  Every national line comes from that player's own cfbstats.com game log, linked from his leaderboard row, and is stored only if it matches his leaderboard line exactly.

Completed seasons also show full-season totals.  Colors: navy for the current season (on RB/WR, the first named player solid and the second dashed), then red, amber, teal and purple for earlier seasons, newest first (two players per season: solid then dashed).  AP Top 5 teams use dotted lines in teal, violet, green, slate and orchid by poll rank; if Notre Dame is in the Top 5 its own navy line stands in for it.  Metallic gold marks the selected tab and stat.  National reference lines are gray.

Live page: https://nd.daboodah.com/ (GitHub Pages from `main`, repo root; `CNAME` holds the domain, and the Cloudflare DNS record is a DNS-only CNAME to `daboodah-oss.github.io`).

The page follows the OS light/dark setting automatically; the sun/moon button in the header overrides it and remembers the choice (localStorage `qb-theme`, the same key as the IU page; each site keeps its own).

## Quarterbacks: roster.json

`roster.json` lists one starter per season (`key`, `name`, `short`, `season`, `espn_id`, optional `note`, and `final_totals` once a season is over).  The newest season is the current QB; every earlier season is a comparison QB.  Page headings, copy, charts, link-preview text, national ranks and the Heisman section all read from it, so nothing names a player in code.  The QB tab title drops a trailing season tag from the current QB's short, so "Carr ’26" is titled "Carr vs the Freeman era".

`final_totals` hold the published season line the stored game log must reconcile to exactly.  Notre Dame's entries carry completions and attempts as well as yards, TD and INT: Leonard 2024 is 269/403, 2,861 yards, 21 TD, 8 INT; Carr 2025 is 195/293, 2,741 yards, 24 TD, 6 INT.  `build_report.py` also holds a regression fixture for the current season: Carr's first 6 games of 2026 must stay 102/144, 1,378 yards, 16 TD, 1 INT (186.5 rating).

ESPN ids are never typed in by hand.  When an entry's `espn_id` is empty, `tools/resolve_espn_ids.py` finds candidates on ESPN's Notre Dame roster for that season and ESPN's player search (exact name), and accepts one only if that player's ESPN game log proves it: a completed season must sum exactly to `final_totals`; the current season's first N games must sum to the line given with `--current-first`.  Anything else stays empty and is reported.

To start a new season (for example 2027):
1. Add the new starter to `roster.json` with an empty `espn_id` (if he also started the year before, give both entries season-tagged shorts like "Carr ’26" / "Carr ’27"), and add `final_totals` to the season that just ended.
2. Run `python tools/resolve_espn_ids.py --write` where ESPN is reachable (GitHub Actions), then let the pipeline run: `collect.py` takes the season from the roster, tracks the new QB's games, and the previous current QB becomes a comparison QB automatically.
3. Optional: record the new QB's preseason Heisman line in `data/heisman.json` as `<key>_opening` (a hand-recorded odds snapshot, the one allowed hand edit).

A comparison QB whose game log is not stored yet is backfilled once, automatically, by the `backfill` step in `collect.py`: it reads ESPN's athlete game log for that season, checks every row against the NCAA passer-rating formula, joins it to that season's cfbstats schedule (ESPN's schedule fills any game cfbstats lacks, such as a playoff game), and stores it only if the season reconciles to `final_totals`.  It also stores that season's final opponent pass-defense ranks.  Until then the page shows the other QBs plus a Data note.

## RB, WR and Team tabs: roster.json "tabs"

- `tabs.rb.current` / `tabs.wr.current` name the current season's players by season, for example `"2026": ["First Back", "Second Back"]` (first = solid line, second = dashed).  A season with no entry uses Notre Dame's top `count` players at `positions` by yards.  Earlier seasons always use that top-by-yards rule, read from cfbstats.com's Notre Dame rushing and receiving pages.  For 2026 the names were taken from the first collected run (top 2 by yards) and written in, as the IU repo does.
- Game lines come from ESPN box scores of every Notre Dame game (`data/team.json`), so no player IDs are needed.  The player lines do not depend on the team-season cross-check: if a Notre Dame team season is refused because its team totals disagree with cfbstats (2024: ESPN's box scores give 185 third-down attempts, cfbstats 184), that run's box scores are still used for the RB and WR players, who must pass their own checks below.  The team season itself stays refused and named in the run log.  A player's games are the games he played according to his cfbstats.com game log, including games without a carry (RB) or catch (WR), which count as 0; each game's carries or catches and TD must also match that game log.  For the newest game, before cfbstats posts it, a game counts once the player has a line in ESPN's box score.
- Checks before anything is stored (`collect_tabs.py` + `update.py`): each box score's player lines must add up to that box score's team total; total yards must equal rushing plus passing; the score must match ESPN's schedule; turnovers must equal fumbles lost plus interceptions; each player's season must match his cfbstats.com season row, and each team season must match cfbstats.com's season team statistics, once cfbstats has posted the same games (completed seasons must match before they are stored at all).
- The AP Top 5 comes from ESPN's rankings feed (AP Top 25 entry).  If Notre Dame is in it, Notre Dame's own navy line stands in for it.  Teams that drop out of the top 5 are removed from `data/team.json` on the next refresh.

## How it updates

`.github/workflows/update.yml` ("Update report") runs a full refresh every Sunday and Wednesday at 10:47 Eastern (cron is UTC, with two backups) and on demand from the Actions tab ("Run workflow", optional `save_raw`).  During game windows (Thursday/Friday/Saturday, 4 PM–2 AM Eastern) it also runs a lightweight check every 20 minutes: if ESPN shows a Notre Dame game has gone final since the last update, it runs the full pipeline; otherwise it exits in seconds without publishing anything (`.nochange` gate).

1. `collect.py` pulls ESPN game logs (current QB, plus a one-time backfill of any earlier roster QB not yet stored), cfbstats.com schedule/leaderboards/pass defense (Notre Dame is cfbstats team 513, ESPN team 87), and the BetMGM Heisman odds table.  It then runs `collect_tabs.py`: the ESPN AP poll, ESPN box scores for every Notre Dame game and every AP Top 5 team's games (only games not already stored are fetched), cfbstats.com season cross-checks, and cfbstats.com national rushing and receiving leaderboards.  Finally `collect_natref.py` reads the cfbstats.com national passing, rushing and receiving leaderboards for every compare-chart stat, keeps the top 20 non-Notre Dame players at each position, and fetches each one's game log from the link on his leaderboard row (only when his leaderboard line has changed since the last run).  A log is stored only if its game count and totals equal his leaderboard line (and, for quarterbacks, every game's passer rating matches the NCAA formula); anything else is dropped and named in the run log.  Each section is independent; a failure keeps that section's last verified data.
2. `update.py` validates every row before it is stored (for example, each passer rating must match the NCAA formula).  The one tolerance: ESPN's published passer rating may differ from the formula by up to 0.15 (its one-decimal rounding), on that single comparison only.
3. `build_report.py` (with `build_tabs.py` for the RB, WR and Team tabs) recomputes everything from the stored rows and writes `index.html`.  If any check fails, nothing is published.  A tab whose data has not been collected yet shows a short notice instead.
4. Changes are committed back to `main` (as "nd-report bot"), which GitHub Pages serves.  The "Report problems" step then fails the run on purpose if any section failed, so GitHub emails the owner; `data/last_run.json` says which section.

If a source cannot be read, the run is marked failed and `data/last_run.json` names the section.  The page still publishes with the last good data and a note.

No AI or paid service is involved in the scheduled run.

## Render check

`tools/render_check.js` executes the built page in jsdom (light and dark theme), opens every tab, and fails on any script error, an empty section, a missing chip group, a broken toggle or sticky tooltip, or a leaderboard out of rank order.  It also scans the page script for const/let helpers called before their definition (the TDZ bug that once blanked the IU page for 2.5 days).  Run it after any template change, and against the live page after a merge:

    npm install --no-save jsdom@24.1.0
    node tools/render_check.js index.html
    node tools/render_check.js https://nd.daboodah.com/

## Installed app

The page can be installed from the browser menu ("Install app" or "Add to Home screen").  `manifest.webmanifest` at the repo root gives the installed app its name ("ND Football Report", short "ND Football"), its colours (`theme_color` #0C2340, ND navy, the page's theme-color; `background_color` #111216, the dark theme's `--bg`, the theme Jeff runs) and its icons in `icons/` (192, 512, maskable 512, plus the 180 apple-touch icon and the link-preview card).  `id` is "/" because the page owns its origin.  `build_report.py --standalone` refuses to publish if the manifest link, a member, or an icon does not resolve, or if `theme_color` drifts from the page's theme-color tag.  All icons are drawn by `tools/make_icons.py` from a simple navy-and-gold "ND" monogram set in Barlow Condensed (OFL, bundled in `assets/fonts/`); no Notre Dame logo is copied or hotlinked.  Rerun it if the mark changes.  There is no service worker: Chrome installs from the menu without one, and the page has no install button that would need one.  An installed copy picks up a changed manifest on Chrome's own cycle (about daily, on launch), not on publish; delete and re-add the app to force it.

## Secrets

No secret is stored in this repository, in GitHub Actions secrets, or in any file on disk.

| Credential | Where it lives | What it accesses | Scope | Owner | Expires | Renewal reminder | What breaks if it lapses |
|---|---|---|---|---|---|---|---|
| GitHub's per-run `GITHUB_TOKEN` (scheduled and on-demand "Update report" runs) | Minted by GitHub Actions for each run; never stored | `daboodah-oss/nd-report` only | `contents: write` (set in `update.yml`) | GitHub (repo setting) | At the end of each run | None needed | Nothing to renew; if the repo's Actions permissions were set to read-only, the bot could not commit and the page would stop updating |
| Pushes from Claude cloud sessions | The Claude GitHub App installation on this repo (claude.ai connector), not a token in the repo | `daboodah-oss/nd-report` feature branches | Contents write via the app; main is protected by the Tier 2 ruleset | Jeff Bandera (GitHub account `daboodah-oss`) | While the app stays installed | None | Cloud sessions cannot push code changes; scheduled runs are unaffected |

There is no fine-grained personal access token for this repository yet.  The IU repo's PAT is scoped to `daboodah-oss/iu-qb-report` only and cannot push here.  `tools/push_feature.ps1` and `tools/run_workflow.ps1` (Jeff's PC) need one before they work for this repo: create a fine-grained PAT with the same settings as the IU one but for `daboodah-oss/nd-report`, store the master copy in LastPass ("GitHub Token - nd-report"), and add a row here with its dates.  Until then, start a run from the GitHub app or website (Actions tab, "Update report", "Run workflow").

Rules: never put a token in a file in this repository or its working folders (`.gitignore` blocks the usual names as a backstop).

## Data

All data is public sports statistics (game logs, team box scores, leaderboards, published odds).  No personal or contact data is ever stored.  Data files are UTF-8, no BOM, LF, byte-exact (`.gitattributes` turns off line-ending conversion for `data/` and `roster.json`).  `data/heisman.json` was seeded with the IU repo's published-odds snapshots (BetMGM, DraftKings, FanDuel; each with its source URL), which are national data covering every contender including CJ Carr; new BetMGM snapshots are added by the pipeline.
