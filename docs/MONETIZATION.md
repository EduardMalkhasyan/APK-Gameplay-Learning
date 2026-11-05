# Method: read how a game earns money

[METHOD.md](METHOD.md) reads gameplay and skips ad SDKs. This route does the opposite: the ad stack, offers, pacing and segments are the target. The purpose is the same: learn the pattern, then design your own. Nobody copies code, assets, names or numbers into a product.

Everything game-specific stays outside this repository, in `~/Desktop/apk-work/<run-id>/` and a private reports folder.

## Quick start

```sh
python3 toolkit/run_monetization.py --check                                 # which tools are installed
python3 toolkit/run_monetization.py "<folder or packages>" --run <run-id>   # evidence for every package
```

The command unpacks, scans, exports script values, recovers code and decompiles publisher Java, one heavy tool at a time, and can resume. Read `~/Desktop/apk-work/<run-id>/INDEX.md`, then each game's `EVIDENCE.md`, which lists warnings, the stack and where to start.

Then fill `templates/MONETIZATION_CONTEXT.md` into `<run-id>/CONTEXT.md`. With Claude Code, the `monetization-teardown` skill walks through the whole route, and the saved `monetization-teardown` workflow runs one analyst and one adversarial reviewer per game, using `templates/MONETIZATION_BRIEF.md`, then writes a cross-game summary. The steps below explain what each part does and how to do it by hand.

## 1. Check you have the right build

An APK mirror's search can hand you a different publisher's listing or an old build. Before any analysis, compare three things with the store listing: package name, version and last update date.

```sh
python3 toolkit/unpack_package.py package.xapk ~/Desktop/apk-work/<run-id>/<game>
python3 toolkit/scan_monetization.py ~/Desktop/apk-work/<run-id>/<game>/unzipped ~/Desktop/apk-work/<run-id>/<game>/evidence/scan
```

The scan prints the package and version. A mediator that no longer exists (MoPub, for example) or a low target SDK means the build is old. Prefer an XAPK with the arm64 split: ARM32 builds give names but few method bodies.

The scan writes `scan.json` (manifest, SDK class counts, mediation adapters with versions from `BuildConfig`, endpoints, config files) and searchable lists of DEX strings, IL2CPP identifiers and string literals, each with a `_money` filtered copy. It reads metadata versions up to 39. Keys in manifest meta-data are masked.

## 2. Read data before code

Look at top-level files in `assets/` first. Publisher SDKs often bundle a full copy of their remote config: ad groups, every placement, floor ladders, offer tables, segment rules. Treat those numbers as defaults that the server can override, and as far better evidence than any class name.

Then export script values:

```sh
dotnet toolkit/Engine/Cpp2IL.dll \
  --force-binary-path <game>/unzipped/lib/arm64-v8a/libil2cpp.so \
  --force-metadata-path <game>/unzipped/assets/bin/Data/Managed/Metadata/global-metadata.dat \
  --force-unity-version <version> \
  --use-processor attributeanalyzer,attributeinjector \
  --output-as dummydll --output-to <game>/raw/dummydll

~/.venvs/unitypy/bin/python -I toolkit/export_unity_assets.py <game>/unzipped <game>/raw/values \
  --only TextAsset,MonoBehaviour --dll-folder <game>/raw/dummydll
```

The attribute processors matter: without `[SerializeField]` on the fields, generated type trees stop at the base class. This route read nearly every script value on Unity 6000.0 and 6000.3 IL2CPP builds where loading the binary directly failed. Each exported JSON starts with `_script`, the class name, so you can find offers with `rg -l '"_script": "SpecialOfferProduct"' raw/values/MonoBehaviour`. Follow `{m_FileID, m_PathID}` references through the file name suffix.

Prices are rarely in the build: the store supplies them at runtime. Use the store's price range and label it.

## 3. Read code for names, then bodies

```sh
python3 toolkit/recover_gameplay.py package.xapk --output <game>/raw/code \
  --assemblies Assembly-CSharp,<publisher assemblies> --budget 1500
```

List the assemblies from `assets/bin/Data/ScriptingAssemblies.json`. Publisher layers usually live in their own assemblies. Names, enums, constants and attributes are reliable; bodies are partial. A missing assembly is reported in `quality.json` and does not stop the others. Use `objdump -d --start-address=<rva> --stop-address=<end>` on the arm64 library when a body matters. ARM32 is the weak spot: Cpp2IL needs native Capstone (`brew install capstone`, `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`) and did not finish building its model within 40 minutes on an 82 MB library. Ask for the arm64 split first. Without it, the scan's `il2cpp_types.jsonl` lists every type, field and method from v31 metadata with no binary, and `export_unity_assets.py --raw-strings` saves printable strings from script values it cannot decode, which is enough to read bundled JSON and ids but loses numbers.

Publisher SDKs keep logic in Java. `jadx --no-res --no-imports --show-bad-code -d out classesN.dex` on the DEX files holding their packages is much faster than the whole app. Obfuscated classes still show strings.

## 4. What to find

| Area | Questions |
| --- | --- |
| Stack | Mediation, custom layer, networks with versions, in-game ads, consent, ad quality, attribution, analytics, A/B |
| Floors | Units per format, ladder values and steps, cold start, last price, postbid, retries, no-fill memory, geo or user variants, per-network coefficients, kill switches |
| Pacing | First ad, gaps, cooldown after rewarded, session and day rules, caps; every interstitial trigger; every rewarded surface and what it pays |
| Segments | Rule engine, thresholds, ML, source and geo, payer status, and above all what actually changes per segment |
| Purchases | Catalog families, rewards, discount ladders, timers, triggers, repeat rules, payer variants, no-ads, subscription, pass, piggy bank, web shop |
| Interplay | What buying does to ads, how no-ads is sold, what ad behaviour triggers an offer |
| Measurement | Revenue events, conversion events to networks, thresholds |

Add history from outside the package: an SDK tracker such as MixRank shows which adapters a publisher added and dropped over time, which one build can never show. Store reviews show what players resent.

## 5. Write it up

Copy [templates/MONETIZATION.md](../templates/MONETIZATION.md). Tag every claim: data, code, names, store, internal or inferred. A flag that exists may be off, so report its state. Bundled values may be overridden remotely, so say so. Mask keys and ad unit ids. Keep recovered code out of the report.

### Comparison page

For people who will not read every report, build one page that shows only where rivals are ahead, ranked by the team's goals:

```sh
cp templates/MONETIZATION_PAGE_DATA.json <reports>/page.en.json   # then fill it
python3 toolkit/build_monetization_page.py <reports>/page.html <reports>/page.en.json <reports>/page.ru.json
```

Give one data file per language and the page shows a language switch; keep the numbers identical across languages. The build stops on unknown game ids, missing strings and anything shaped like a key or ad unit id. Icons are local images, inlined into the page. The page can hold internal goals and numbers, so check who can open it before sharing the link.

## 6. Limits

Static reading shows capability and defaults. It cannot show live floors, real prices per country, the server's segment assignment or actual ad frequency. A device session settles those. Do not contact a game's servers from analysis tools. Do not defeat protection such as PairIP or encrypted metadata: note the limit and use the other evidence.
