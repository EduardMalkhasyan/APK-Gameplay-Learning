# APK Gameplay Learning

Tools and a step-by-step method for opening an Android game package (APK, XAPK, APKS, APKM) and reading how the game works: gameplay code, sprites, textures, 3D models, sounds and level data. The goal is to learn patterns and make better **original** games. [docs/MONETIZATION.md](docs/MONETIZATION.md) applies the same approach to how a game earns money.

Like Photoshop without photos: this repository holds the tools and the method, never a game. Packages, extracted files and per-game notes live in `~/Desktop/apk-work/<run-id>/`, outside the repository, and get deleted when you are done.

## Rules

1. **Learn, never clone.** Take the pattern, then build your own game with your own code, art, sound, names and numbers.
2. **No other developers' files in this repository**: no packages, recovered code, exported assets or per-game reports.
3. **Read recovered code, never run it.**

## Start

1. Read [docs/METHOD.md](docs/METHOD.md). It covers getting the right package, finding the engine, extracting assets, reading code and turning what you learned into your own design.
2. Inventory the package:

   ```sh
   python3 toolkit/inspect_package.py ~/Desktop/apk-work/<run-id>/package.xapk
   ```

3. Follow the engine's route in [docs/METHOD.md](docs/METHOD.md) and [docs/ENGINE_ROUTES.md](docs/ENGINE_ROUTES.md).
4. Record each mechanic in a copy of [templates/MECHANIC.md](templates/MECHANIC.md), kept in your work folder. A filled example based on a made-up game is in [examples/](examples/synthetic-mechanic.md).

For AI agents: [AGENTS.md](AGENTS.md) (Claude reads it via [CLAUDE.md](CLAUDE.md)).

## Contents

| Path | Purpose |
| --- | --- |
| docs/METHOD.md | The method: package → engine → assets → code → findings → your own design |
| docs/ENGINE_ROUTES.md | Code-recovery routes per engine and tool references |
| docs/WORKFLOW.md | Evidence rules for deep code work |
| docs/MONETIZATION.md | The route for reading how a game earns money: ad stack, floors, pacing, segments, offers |
| docs/LESSONS_LEARNED.md | Pitfalls we hit and how to avoid them |
| templates/ | Blank mechanic record, monetization report, analyst brief, run context, comparison page with sample data, and run quality file |
| examples/ | Synthetic filled example (made-up game) |
| toolkit/run_monetization.py | One command for the monetization route: packages in, evidence folders and `EVIDENCE.md` out |
| toolkit/build_monetization_page.py | Competitor comparison page: filled data files in, one HTML file with a language switch out |
| .claude/skills/monetization-teardown | Claude Code skill: the whole monetization route, step by step |
| .claude/workflows/monetization-teardown.js | Saved multi-agent workflow: analyst and reviewer per game, then a summary |
| toolkit/inspect_package.py | Read-only package inventory: hashes, ABIs, engine signals |
| toolkit/unpack_package.py | Unpack APK/XAPK safely: path checks, byte cap, time budget |
| toolkit/scan_monetization.py | Ad, purchase, analytics and protection stack with versions, plus searchable names and strings |
| toolkit/export_unity_assets.py | Unity sprites, textures, audio, 3D meshes, fonts, text and script values (UnityPy) |
| toolkit/recover_gameplay.py | Unity Mono/IL2CPP code export with a patched Cpp2IL + ILSpy |
| toolkit/Engine, toolkit/ILSpy | Pinned tool binaries; licenses in toolkit/*-LICENSE.txt |
| toolkit/Verification | Synthetic floating-point regression checks for the Cpp2IL patch |
| tests/ | Synthetic tests (no game files) |

## Unity code export

Requires Python 3 and .NET 10. Tested on macOS ARM64.

```sh
python3 toolkit/recover_gameplay.py ~/Desktop/apk-work/<run-id>/package.xapk \
  --output ~/Desktop/apk-work/<run-id>/unity-export
```

Exit 2 means a partial export: read its `quality.json`. A successful export shows what the tools could recover. It never proves that you have the original source.

## Tests

```sh
python3 -m unittest discover -s tests
```
