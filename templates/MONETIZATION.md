# <Game> monetization teardown

Package, version, publisher, engine, date studied. Keep this file outside the repository, in the work folder or a private reports folder. It is a learning record: describe patterns in your own words and mask keys and ad unit ids.

Evidence tags: **[data]** bundled config or asset value, **[code]** recovered body or disassembly, **[names]** identifiers only, **[store]** public listing, **[internal]** own company sources, **[inferred]** reasoning. Bundled config shows defaults, which remote config can override. Say so when it matters.

## 1. One-page summary

What the game sells, how it earns, the three strongest moves, the three weakest points, and the one thing most worth learning.

## 2. Snapshot

Store facts (installs, rating, IAP range, last update) and build facts (engine, architecture, what could and could not be read).

## 3. Revenue model

Ads versus purchases, with the evidence for the split. Number of rewarded surfaces, interstitial triggers, purchase surfaces.

## 4. Ad stack

Mediation, custom layers on top, demand partners with versions, in-game or house ads, ad quality, consent.

## 5. Waterfall and floors

Units per format, floor ladders with values, cold start, last-price logic, postbid, retry and no-fill handling, caching, geo or user variants. Say which numbers are bundled defaults.

## 6. Pacing and placements

First ad rules, gaps between ads, cooldown after rewarded, session and daily caps, grace windows. List interstitial triggers and rewarded surfaces with what each one pays.

## 7. Segmentation, tiers and experiments

Who the game treats differently, by what rule, and what changes for them. Remote config, A/B framework, feature flags and kill switches.

## 8. Purchases and offers

Catalog families, price points if known, triggers, timers, discount ladders, repeat rules, payer and non-payer variants, no-ads and subscriptions, passes, piggy banks, web shop.

## 9. How ads and purchases interact

What buying does to ads, what ad behaviour does to offers.

## 10. Economy and live-ops hooks

Currencies, sinks, events, passes, leaderboards, notifications: only what feeds monetization.

## 11. Measurement and UA feedback

Attribution, ad-revenue events, conversion events sent back to networks.

## 12. Protection and quality

Anti-cheat, integrity checks, ad review, pinning, and what these tell you about priorities.

## 13. Strengths and weak points

| Area | Strength or weakness | Evidence | Why it matters |
| --- | --- | --- | --- |

## 14. Lessons for our games

The general pattern, not their implementation. Each lesson: what to test, primary metric and guardrail, effort, risk. Note what is dark-pattern or policy risk and should not be done.

## 15. Confirmed, likely, unknown

Three separate lists, with sources. End with what a device session or remote config capture would settle.
