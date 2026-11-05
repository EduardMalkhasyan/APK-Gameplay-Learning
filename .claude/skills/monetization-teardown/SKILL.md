---
name: monetization-teardown
description: Study how mobile games earn money from their packages and write one report per game plus a cross-game summary. Use when the user wants to learn a game's or competitor's monetization, ad stack, floors, ad pacing, user tiers, offers or IAP from an APK or XAPK, or to audit their own game's monetization. Learning only, never cloning.
---

# Monetization teardown

Follow [docs/MONETIZATION.md](../../../docs/MONETIZATION.md). This is the order that worked. Everything game-specific stays outside the repository.

## 1. Get the right packages

Ask where the packages are. Check tools with `python3 toolkit/run_monetization.py --check`.

Compare every package's id, version and date with its store listing before analysing. A mirror can serve another publisher's package or a years-old build, and a wrong build wastes the whole run. Ask for the bundle with the arm64 split: ARM32 gives names without bodies. If a package must come from a third-party mirror, give the user the link and let them download it.

## 2. Build the evidence

Run in the background, one heavy tool at a time:

```sh
python3 toolkit/run_monetization.py "<folder or packages>" --run <run-id>
```

It is resumable. Read `~/Desktop/apk-work/<run-id>/INDEX.md`, then each game's `EVIDENCE.md`: warnings first, then the config files and classes it lists. Tell the user at once about any wrong or old build.

Peek at the bundled config it lists. A publisher SDK's copy of its remote config is often the richest evidence in the package, and a few specific leads make the analyst's work far better.

## 3. Gather context

Copy `templates/MONETIZATION_CONTEXT.md` to `~/Desktop/apk-work/<run-id>/CONTEXT.md` and fill it from the user and company sources: who needs this, the key questions, our games and their live setup, our benchmark, earlier teardowns (search before repeating them), and tests that must not be disturbed. Read only. Never post anywhere without asking.

Collect public facts into the run folder: store listings into `store_listings.json`, SDK added and removed history into a notes file. These show what one build cannot.

## 4. Run the analysts

By default, write the reports in this session, one game at a time, following `templates/MONETIZATION_BRIEF.md`. Use the saved workflow only when the user opts in, since it starts one analyst and one reviewer per game plus a summary:

```text
Workflow(name: "monetization-teardown", args: {
  repo: "<absolute path of this repository>",
  run: "<absolute path of ~/Desktop/apk-work/<run-id>>",
  reports: "<absolute path of a private reports folder>",
  games: [{ slug: "<folder name>", title: "<game, version, publisher, package>", report: "01-name.md",
            ours: false, leads: "<specific keys and classes worth following>" }]
})
```

Give each game real leads from step 2. Generic briefs produce generic reports.

Watch the plan usage during long runs with the session usage tool if the user set a limit.

## 5. Deliver

Read `00-SUMMARY.md` and check its main numbers against the reports. Tell the user what is new, what to do first, what could not be read and what one device session would settle. Offer to share only when asked, since reports hold competitor findings and internal figures.

For a visual summary, fill a copy of `templates/MONETIZATION_PAGE_DATA.json` per language and run `toolkit/build_monetization_page.py` (see docs/MONETIZATION.md). The page can hold internal numbers, so check who can open it before sharing.

## Rules

- Learn, never clone. Reports describe patterns in our own words. No recovered code, assets or level data go into any product.
- Never commit per-game material: packages, recovered code, values, reports or filled context.
- Mask API keys, SDK keys, tokens and ad unit ids in everything you write.
- Never run anything from a package. Contact no game server. Do not defeat protection such as PairIP or encrypted metadata.
- Add only reusable lessons and tool fixes to this repository.
