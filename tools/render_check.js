#!/usr/bin/env node
/* Execute the built page in jsdom and prove every section populated with zero script errors.

     npm install --no-save jsdom@24.1.0      (once, in any folder on NODE_PATH or next to this repo)
     node tools/render_check.js [index.html | https://nd.daboodah.com/]

   Why: a byte-identical push once shipped a blank IU page for ~2.5 days (a const helper used before its
   definition, a TDZ ReferenceError, killed the page script).  A page that has not been executed is not done.

   It loads the page (a file or a live URL), runs its script in light and then dark theme, opens every tab,
   and checks: no uncaught error or console.error; every QB section and every RB/WR/Team section has content;
   the compare charts have the three chip groups ("ND players", "National Top 3", "Individual player") with
   working toggles; a chart tap pins the tooltip and a tap outside dismisses it; every leaderboard is in rank
   order with unranked rows last; the manifest link is present.  It also scans the page script for const/let
   helpers whose first use at top level comes before their definition (the TDZ bug class).
   Exit 0 = pass.  Prints one line per check and a summary with the section and error counts. */
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const target = process.argv[2] || path.join(__dirname, "..", "index.html");
const results = []; let failed = 0;
const ok = (cond, what) => { results.push(`${cond ? "PASS" : "FAIL"}  ${what}`); if (!cond) failed++; return cond; };

async function load() {
  if (/^https?:/.test(target)) { const r = await fetch(target); if (!r.ok) throw new Error(`GET ${target}: ${r.status}`); return await r.text(); }
  return fs.readFileSync(target, "utf8");
}

function tdzScan(js) {
  // top-level-ish const/let definitions, then any earlier *call* of that name outside a function body we can see
  const defs = [...js.matchAll(/^\s*(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=/gm)].map(m => ({ name: m[1], at: m.index }));
  const fnDefs = new Map([...js.matchAll(/^\s*function\s+([A-Za-z_$][\w$]*)\s*\(/gm)].map(m => [m[1], m.index]));
  const issues = [];
  for (const d of defs) {
    const re = new RegExp(`(^|[^\\w$.])${d.name.replace(/\$/g, "\\$")}\\s*\\(`, "g");
    let m;
    while ((m = re.exec(js)) && m.index < d.at) {
      // a use inside a function declared before the definition is fine (it runs later); flag uses at the top level
      const before = js.slice(0, m.index);
      const depth = (before.match(/\{/g) || []).length - (before.match(/\}/g) || []).length;
      if (depth <= 1) { issues.push(`${d.name} used at offset ${m.index} before its definition at ${d.at}`); break; }
    }
  }
  return { defs: defs.length, fns: fnDefs.size, issues };
}

async function run(html, theme) {
  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => errors.push(`jsdomError: ${e.message}`));
  vc.on("error", (...a) => errors.push(`console.error: ${a.join(" ")}`));
  const dom = new JSDOM(html, {
    runScripts: "dangerously", pretendToBeVisual: true, url: "https://nd.daboodah.com/", virtualConsole: vc,
    beforeParse(w) {
      w.matchMedia = q => ({ matches: theme === "dark" && /dark/.test(q), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} });
      w.scrollTo = () => {};  // jsdom does not implement scrolling; the page calls it when a tab is opened by the user
      w.addEventListener("error", e => errors.push(`window error: ${e.message}`));
      Object.defineProperty(w.HTMLElement.prototype, "clientWidth", { get() { return 900; } });
      w.SVGElement.prototype.getBoundingClientRect = () => ({ left: 0, top: 0, width: 900, height: 360, right: 900, bottom: 360 });
      try { w.localStorage.setItem("qb-theme", theme); } catch (e) {}
    },
  });
  await new Promise(r => setTimeout(r, 300));
  return { dom, errors };
}

const nonEmpty = (doc, sel) => { const e = doc.querySelector(sel); return !!e && e.innerHTML.trim().length > 0; };

function checkRanks(doc, where) {
  let bad = 0, boards = 0;
  doc.querySelectorAll(`${where} .board table`).forEach(t => {
    boards++;
    const rk = [...t.querySelectorAll("tr:not(.gap) td.rk")].map(td => td.textContent.replace(/^T/, "").trim());
    const nums = rk.map(x => (x === "–" || x === "" ? Infinity : +x));
    for (let i = 1; i < nums.length; i++) if (nums[i] < nums[i - 1]) bad++;
  });
  return { bad, boards };
}

(async () => {
  const html = await load();
  const script = (html.match(/<script>\s*const MODEL[\s\S]*?<\/script>/) || [""])[0];
  const tdz = tdzScan(script);
  ok(tdz.issues.length === 0, `TDZ scan: ${tdz.defs} const/let definitions, ${tdz.fns} function declarations; first-call before definition: ${tdz.issues.length ? tdz.issues.join("; ") : "none"}`);
  ok(/<link rel="manifest" href="manifest\.webmanifest">/.test(html), "manifest link present in <head>");

  let sections = 0, populated = 0, errorsTotal = 0;
  for (const theme of ["light", "dark"]) {
    const { dom, errors } = await run(html, theme);
    const w = dom.window, doc = w.document, $ = s => doc.querySelector(s);
    ok(doc.documentElement.getAttribute("data-theme") === theme, `[${theme}] theme applied before paint (data-theme=${doc.documentElement.getAttribute("data-theme")})`);
    // theme toggle flips data-theme
    const before = doc.documentElement.getAttribute("data-theme"); $("#theme-toggle").click();
    ok(doc.documentElement.getAttribute("data-theme") !== before, `[${theme}] theme toggle switches to ${doc.documentElement.getAttribute("data-theme")}`);
    $("#theme-toggle").click();
    await new Promise(r => setTimeout(r, 50));

    const qb = ["#h2h-table", "#pace-tiles", "#cmp-chart", "#cmp-legend", "#logs", "#boards", "#fd-chart", "#fd-legend", "#odds-table", "#trail", "#notes", "#sources", "#scorecard", "#verdict"];
    for (const s of qb) { sections++; if (ok(nonEmpty(doc, s), `[${theme}] QB ${s} populated`)) populated++; }
    ok(!!$("#cmp-chart svg"), `[${theme}] QB compare chart drew an SVG`);
    ok(!!$("#fd-chart svg"), `[${theme}] Heisman field chart drew an SVG`);
    const fdNames = [...doc.querySelectorAll("#fd-legend .pc")].map(b => b.textContent);
    ok(fdNames.some(n => /Carr/.test(n)), `[${theme}] Heisman field includes Carr (${fdNames.length} players: ${fdNames.join(" | ")})`);
    const cats = [...doc.querySelectorAll("#cmp-legend details.cat > summary")].map(s => s.textContent.replace("▾", "").trim());
    ok(cats.join("|") === "ND players|National Top 3|Individual player", `[${theme}] QB chip groups: ${cats.join(", ")}`);
    const r0 = checkRanks(doc, "#tab-qb"); ok(r0.boards >= 5 && r0.bad === 0, `[${theme}] QB leaderboards (${r0.boards}) in rank order, unranked last`);

    // tabs
    for (const k of ["rb", "wr", "team"]) {
      doc.querySelector(`.tabs [data-tab="${k}"]`).click();
      await new Promise(r => setTimeout(r, 30));
      const host = $("#tab-" + k);
      ok(!host.hidden, `[${theme}] ${k} tab opens`);
      const ids = k === "team" ? ["h2h", "compare", "games", "method"] : ["h2h", "compare", "national", "games", "method"];
      for (const id of ids) { sections++; if (ok(nonEmpty(doc, `#${k}-${id}`), `[${theme}] ${k} #${k}-${id} populated`)) populated++; }
      ok(!!$(`#${k}-chart svg`), `[${theme}] ${k} compare chart drew an SVG`);
      if (k !== "team") {
        const kc = [...host.querySelectorAll(".panel details.cat > summary")].map(s => s.textContent.replace("▾", "").trim());
        ok(kc.join("|") === "ND players|National Top 3|Individual player", `[${theme}] ${k} chip groups: ${kc.join(", ")}`);
        const r = checkRanks(doc, `#tab-${k}`); ok(r.boards >= 4 && r.bad === 0, `[${theme}] ${k} leaderboards (${r.boards}) in rank order, unranked last`);
        // chips toggle
        const chip = host.querySelector(`#${k}-catchips .pc`); const was = chip.getAttribute("aria-pressed"); chip.click();
        ok(chip.getAttribute("aria-pressed") !== was, `[${theme}] ${k} ND-player chip toggles`); chip.click();
        // national top 3 chip draws a gray line
        const nt = host.querySelector(`#${k}-nrtop-pills .pc`);
        if (ok(!!nt, `[${theme}] ${k} National Top 3 chips present`)) { const n0 = host.querySelectorAll(`#${k}-chart path`).length; nt.click(); ok(host.querySelectorAll(`#${k}-chart path`).length > n0, `[${theme}] ${k} National Top 3 chip adds a line`); nt.click(); }
        const q = host.querySelector(`#${k}-nrq`);
        if (ok(!!q, `[${theme}] ${k} Individual player search present`)) {
          q.value = "a"; q.dispatchEvent(new w.Event("input")); const hit = host.querySelector(`#${k}-nrres [data-nradd]`);
          if (ok(!!hit, `[${theme}] ${k} search finds pool players`)) { hit.click(); ok(!!host.querySelector(`#${k}-nrpicks .nrpick`), `[${theme}] ${k} pick adds a removable pill`); host.querySelector(`#${k}-nrpicks [data-nrx]`).click(); }
        }
      } else {
        const tc = [...host.querySelectorAll("#team-catchips .pc")].map(b => b.textContent);
        ok(tc.length >= 4, `[${theme}] team chips: ${tc.join(" | ")}`);
        ok(/released/.test(host.textContent) && /AP Top 5 from the/.test(host.textContent), `[${theme}] team tab labels the AP poll week and release date`);
      }
    }
    // back to QB: chips toggle, national top 3, sticky tooltip
    doc.querySelector('.tabs [data-tab="qb"]').click(); await new Promise(r => setTimeout(r, 30));
    const chip = $("#cmp-legend .pc[data-i]"); chip.click(); ok(chip.getAttribute("aria-pressed") === "false", `[${theme}] QB ND-player chip toggles off`); chip.click();
    const nt = $("#qb-nrtop-pills .pc");
    if (ok(!!nt, `[${theme}] QB National Top 3 chips present`)) { const n0 = doc.querySelectorAll("#cmp-chart path").length; nt.click(); ok(doc.querySelectorAll("#cmp-chart path").length > n0, `[${theme}] QB National Top 3 chip adds a line`); nt.click(); }
    // all off -> friendly empty state
    const all = [...doc.querySelectorAll("#cmp-legend .pc[data-i]")]; all.forEach(b => b.click());
    ok(/toggled off/.test($("#cmp-chart").textContent), `[${theme}] all chips off shows the friendly empty state`); all.forEach(b => b.click());
    const hit = $("#cmp-chart rect[data-hit]");
    hit.dispatchEvent(new w.MouseEvent("pointerdown", { bubbles: true, clientX: 450, clientY: 100 }));
    const tip = $("#cmp-chart .tip");
    ok(tip && !tip.hidden, `[${theme}] tap in chart pins the tooltip`);
    hit.dispatchEvent(new w.MouseEvent("pointerleave", { bubbles: true }));
    ok(tip && !tip.hidden, `[${theme}] tooltip stays after pointerleave`);
    doc.body.dispatchEvent(new w.MouseEvent("pointerdown", { bubbles: true }));
    ok(tip && tip.hidden, `[${theme}] tap outside any chart dismisses the tooltip`);

    ok(errors.length === 0, `[${theme}] script errors: ${errors.length}${errors.length ? " -> " + errors.join(" | ") : ""}`);
    errorsTotal += errors.length;
    w.close();
  }
  console.log(results.join("\n"));
  console.log(`\nSUMMARY: ${populated}/${sections} sections populated across light and dark (${sections / 2} per theme), ${errorsTotal} script errors, ${failed} failed checks`);
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("render_check crashed:", e); process.exit(2); });
