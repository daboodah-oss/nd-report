# AGENTS.md — working conventions for nd-report

This repo is a self-running pipeline. It must keep working with no human or AI
in the loop: GitHub Actions does everything on a schedule, and the validation
in `build_report.py` is the quality gate. Follow these rules so any helper
(human, Claude, or otherwise) can safely contribute.

It is a replica of `daboodah-oss/iu-qb-report` (the IU Football Report) for
Notre Dame.  File names, data-file names and the pipeline are the same, so a
fix in one repo usually ports to the other; port it deliberately, by diff, and
keep the ND-only differences listed at the end of this file.

## Pipeline

1. `collect.py` pulls ESPN game logs, cfbstats.com leaderboards, and sportsbook
   Heisman odds into `data/*.json`. The quarterbacks come from `roster.json`
   (one entry per season; newest season = current QB, earlier seasons =
   comparison QBs). An earlier QB with no stored season is backfilled once from
   ESPN and must reconcile to his `final_totals`. Each section is independent;
   a failed section keeps its last verified data and is recorded in
   `data/last_run.json`.
2. `update.py` validates every row before it is stored (e.g. each passer rating
   must match the NCAA formula).
3. `build_report.py` recomputes everything from the stored rows and writes
   `index.html` from `template.html`. **If any validation check fails, nothing
   is published** — this is the rule that lets strangers contribute safely.
4. `.github/workflows/update.yml` commits the result back to `main`, which
   GitHub Pages serves at https://nd.daboodah.com/.

No AI or paid service is involved in the scheduled run. Keep it that way.

## Schedule

- Full refresh: Sunday and Wednesday, 10:47 AM Eastern (plus backups).
- Game-window quick checks: every 20 minutes, Thu/Fri/Sat 4 PM–2 AM Eastern.
  Each check exits in seconds unless ESPN shows a new ND final, then runs the
  full pipeline. A run with no new data changes nothing.

## Lanes and change control (Tier 2 repo)

- `main` is protected by a ruleset: no force pushes, branch deletions
  restricted, no pull-request requirement (the Actions bot commits straight to
  `main`).  Any merge to `main` deploys.
- **Pipeline (collect, update, build, workflows, roster, template logic) is
  Claude's lane**, worked through Claude cloud sessions on a feature branch
  (`claude/...`), merged only after Jeff approves in chat.
- **Small display-only fixes** (copy, a colour, a CSS tweak) may be pushed to
  `main` by Budzilla (Muse) at Jeff's request.  Anything that changes what is
  collected, validated or computed goes through Claude's lane.
- `data/`, `index.html`, `logs/` are written by "nd-report bot" (the workflow)
  only.  Shared files (README.md, AGENTS.md): Claude owns them; Budzilla may
  fix wording at Jeff's request.
- Commit identities: Claude as `Claude <noreply@anthropic.com>`; Muse as
  `Budzilla <budzilla@noreply.github.com>`; the workflow as `nd-report bot`.
- Anything that changes what the page shows its readers: Jeff's OK first, in
  BEFORE / AFTER form.

## Rules for contributors

1. **Pull before pushing.** The bot commits on schedule; push with
   `git pull --rebase` first to avoid collisions.
2. **Never hand-edit `data/*.json`.** To add a quarterback or season, edit
   `roster.json` and let the pipeline collect the games. Data comes from `collect.py`. The one
   exception is Heisman odds snapshots, which are recorded by hand from
   published reports — each snapshot must carry `book`, `as_of`, `outlet`,
   and `url`.
3. **Never type an ESPN id.**  Leave `espn_id` empty and run
   `tools/resolve_espn_ids.py --write` where ESPN is reachable; it accepts an id
   only if that player's game log reconciles to the published totals.
4. **Run the build and the render check locally before pushing** template or
   build changes: `python3 build_report.py --standalone --out /tmp/test.html`
   must print `OK`, and `node tools/render_check.js /tmp/test.html` must pass
   (0 script errors, every section populated).  A build that has not been
   executed is not done (see Lessons).
5. **Update this file and README.md when behavior changes.**
6. **Do not remove or let any step overwrite the `CNAME` file.** It holds the
   custom domain (`nd.daboodah.com`). The workflow only stages
   `data/`, `index.html`, and `logs/` — keep it that way.
7. **Keep page output deterministic.** No live API calls, no AI-generated
   text in the scheduled build. Editorial judgment (discrepancy writeups,
   caveats) is added by a human as data/notes, and the page renders them.
8. **No secrets in files.** The scheduled workflow uses its own temporary
   `GITHUB_TOKEN`. See the Secrets section of README.md.
9. The output check in `build_report.py` rejects `TODO`, `lorem`,
   `PLACEHOLDER`, and anything looking like a credential. Don't add those.
10. **Leaderboards are always sorted by rank ascending, unranked last.**

## File map

- `roster.json` — Freeman-era starters, one entry per season (Leonard 2024, Carr ’25, Carr ’26); drives every name on the page
- `collect.py` — data fetching (network), including the one-time season backfill
- `collect_tabs.py` — RB, WR and Team tab data (ESPN AP poll and box scores, cfbstats cross-checks and national boards); run by `collect.py`
- `collect_natref.py` — national reference players for the QB, RB and WR compare charts (cfbstats national boards plus each listed player's linked game log); run by `collect.py`
- `build_tabs.py` — RB, WR and Team tab models, the national reference model (`natref`) and the site title; run by `build_report.py`
- `update.py` — row validation before storage
- `build_report.py` — validation + model + render (no network)
- `template.html` — page; the model is injected at `/*__MODEL__*/null`
- `data/` — stored rows: `games.json`, `national.json`, `heisman.json`,
  `cohort.json`, `freshness.json`, `last_run.json`, `team.json`, `skill.json`,
  `skill_national.json`, `national_logs.json`
- `icons/`, `assets/fonts/` — PWA icons and link-preview card; the OFL fonts they are drawn with
- `manifest.webmanifest` — web app manifest (installed-app name, colours, icons); checked by `build_report.py --standalone`
- `tools/make_icons.py` — draws every icon and `icons/og.png` from a navy/gold "ND" monogram (one-time, needs Pillow)
- `tools/resolve_espn_ids.py` — finds and proves ESPN athlete ids for roster entries with an empty `espn_id` (network)
- `tools/render_check.js` — executes the built page in jsdom; fails on any script error or empty section
- `tools/gh_status.py`, `tools/push_feature.ps1`, `tools/run_workflow.ps1` — Jeff's PC helpers (need an nd-report PAT; see README Secrets)
- `logs/` — per-run logs, force-added to git

## Page behavior notes

- The page is "Fighting Irish {season}" (`roster.json` `site_title`) with four tabs: QB, RB, WR, Team.  The tab shows in the URL hash (`#rb`, `#team`; section links are `#rb-h2h` and so on), so links can open a tab directly.  Charts draw only for the visible tab and redraw when a tab opens.
- The QB title is the current QB's short with any trailing season tag removed ("Carr ’26" → "Carr vs the Freeman era"), in the full-width `.mast-head` row styled like every tab's `.tabhead h2`.  Everywhere else the season-tagged short is used, so the two Carr seasons never read the same.
- RB/WR/Team colors: navy for the current season (second current player dashed), predecessor slots `--p1`.. newest first (second player dashed), AP Top 5 teams dotted in `--a1`..`--a5` by rank.  `--accent` (metallic gold) marks the selected tab and stat chip only.
- Compare charts (QB, RB, WR) have three collapsible sections, in order: "ND players" (open), "National Top 3" and "Individual player" (both collapsed).  National Top 3 chips are the first 3 non-Notre Dame players at the tab's positions on the cfbstats national leaderboard for the viewed stat; they change with the stat and start off (opening the section draws nothing until a chip is tapped; a chip that is on stays on for the new stat's player in that slot).  Individual player searches a pool = union of the top 20 per tracked stat; a pick adds a removable pill (x).  National lines are gray (`--field` for Top 3, `--muted` for picks; solid/dashed/dotted by slot), labeled at the line end, and lined up by each player's own games played.  QB Total TD and INT have no national leaderboard ("No national leaderboard for this stat."); Total TD cannot be drawn for national QBs because the passing log has no rushing TD.
- Chips and pills show the player name only, underlined in the line's colour and style (`.un` / `.pu`); ON is full opacity, OFF is dimmed; all off shows a friendly empty state.  Tables keep their line swatches.
- Chart tooltips are sticky: a tap or click in a chart pins the pop-up; a tap outside any chart dismisses it (one shared tip element and a guide registry in `lineChart()`; pointerleave does not hide it).
- National reference data (`data/national_logs.json`, written only by `collect_natref.py` through `update.py natref`): a player is stored only if the game log his leaderboard row links to has exactly his leaderboard G games and sums exactly to his leaderboard line (QBs: every game's listed rating must also match the NCAA formula).  Failures are dropped and named in the run log and in the file's `dropped` list, never estimated; a dropped Top 3 player is named on the page, not replaced by #4.  A stored log is reused until that player's leaderboard line changes.  Each tab is its own section (`natref_qb`, `natref_rb`, `natref_wr`).
- ESPN game-log passer ratings (collect.py `espn_gamelog`) may differ from the formula by up to 0.15 (ESPN's one-decimal rounding, found on the IU page 2026-10-10: 152.7 vs 152.6).  Every other rating check stays at 0.06.  Do not widen any other check.
- RB/WR player lines are decoupled from the team-season cross-check (`collect_tabs.BOX`): a Notre Dame team season refused for a team-total disagreement with cfbstats (2024 third-down attempts, 185 vs 184) still supplies that run's box scores to `players()`.  Player checks are unchanged and no tolerance was widened.  The team season stays refused, so the `team` section fails and the run is marked failed on every full refresh until the sources agree.  Not yet ported to the IU repo.
- `data/team.json` (box-score rows by ESPN team id and season, plus the AP poll), `data/skill.json` (RB and WR players' game lines), `data/skill_national.json` (RB and WR national boards and weekly rank history) are written only by `collect_tabs.py` through `update.py`.
- Comparisons always line seasons up by game number through the current QB's
  game count (N). Completed seasons also show full-season totals. A comparison
  QB whose season was shorter than N shows his full season, is marked, and is
  left out of the leader boxes.
- Data field names `cur_row`, `cur_rank` (national.json) and `<key>_opening`
  (heisman.json) mean "the current QB".  (The IU repo still calls the first two
  `hoover_row` / `hoover_rank`; port by renaming.)  The national top-5 boards
  and the Heisman sections are scoped to the current QB only.
- Colors: CSS slots `--cur` (current QB) and `--p1`..`--p4` (earlier starters,
  newest first), defined for light and dark themes.  Dark `--cur` is a light
  navy (#8fb0ea) because ND navy is unreadable on the dark background.
- Theme: the page follows `prefers-color-scheme` unless the reader picks the
  header sun/moon toggle, which sets `data-theme` on `:root` and persists in
  localStorage (`qb-theme`). Charts redraw on `data-theme` changes via a
  MutationObserver. An inline head script applies the saved theme before first
  paint to avoid a flash.

## ND-only differences from the IU template

Team Notre Dame (ESPN 87, cfbstats 513); coach Marcus Freeman ("the Freeman
era"); roster entries per season with season-tagged shorts; navy #0C2340
primary and metallic gold #AE9142 accent (IU: crimson); manifest name "ND
Football Report", short "ND Football", theme #0C2340; CNAME nd.daboodah.com;
workflow bot "nd-report bot"; `final_totals` include completions and attempts;
the build fixture is Carr's first 6 games of 2026; icons are drawn from an "ND"
monogram, not a logo file; `cur_row`/`cur_rank` field names;
`.gitattributes` keeps data byte-exact; RB/WR player lines do not depend on the team-season cross-check; the head carries the iOS
`apple-mobile-web-app-status-bar-style` tag (ai-build-standards v5.3).

## Lessons learned the hard way (inherited from the IU repo)

- A byte-identical push once shipped a blank IU page for about 2.5 days: a
  `const` helper was used before its definition (TDZ ReferenceError) and killed
  the page script.  The build passed; only executing the page shows it.  Run
  `tools/render_check.js` on every template change and against the live page
  after every merge.
- Never estimate a missing national line.  Match or drop, and name the drop.
- The schedule change of 2026-10-04 was almost missed because docs went stale.
