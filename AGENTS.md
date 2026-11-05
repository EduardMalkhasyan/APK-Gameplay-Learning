# Instructions for AI agents

Purpose: read how a game works from its compiled package (gameplay code, sprites, textures, 3D models, sounds, level data), then help design original games. This repository is the toolbox and the method, never a game.

- Read docs/METHOD.md first, then docs/LESSONS_LEARNED.md and docs/WORKFLOW.md. For monetization questions, also docs/MONETIZATION.md, and start from the `monetization-teardown` skill and `toolkit/run_monetization.py`.
- **Learn, never clone.** Never ship, publish or paste recovered code, assets, level data or names into the user's project, and never rebuild a specific existing game. Generalize the pattern and design fresh behavior, code and art.
- **No game files in this repository.** Work in `~/Desktop/apk-work/<run-id>/` outside the repository. Never commit packages, native libraries, recovered scripts, exported assets, per-game constants, addresses or reports. Commit only reusable tools, method docs, blank templates and synthetic examples or tests.
- Never claim exact original source recovery, in any language. Separate metadata, native evidence, reconstruction and inference.
- Identify the engine/runtime, version, architecture and actual package contents before selecting tools. Do not assume Unity or C#. Ask for the full bundle (XAPK/APKS with the arm64 split and asset packs) when splits are missing.
- Use the matching route in docs/METHOD.md and docs/ENGINE_ROUTES.md. Documentation for a route does not mean that recovery is implemented or verified here.
- Read data before code: ScriptableObjects, level files, text assets, localization tables and constant pools give exact numbers quickly.
- For gameplay, skip ad, analytics and attribution SDKs and engine code, and scope app-owned namespaces/packages explicitly. For monetization, those SDKs and their config are the target: follow docs/MONETIZATION.md.
- Never write API keys, SDK keys, tokens or ad unit ids into reports. Mask them. Do not contact a game's servers from analysis tools or defeat protection such as PairIP or encrypted metadata.
- Run a game only when the user asks for a live run, and only on an isolated emulator as in docs/LIVE_CAPTURE.md: never click ads, never buy, never hook the app or extract keys.
- Check the package name, version and date against the store listing before analysis: APK mirrors can serve another publisher's or an old build.
- Treat tool support as version- and architecture-specific. Before declaring recovery impossible, check the tool's current primary documentation and try an applicable alternative within bounded work.
- Never copy original game repository source to fill recovery gaps. Tool repositories may inform general decompiler fixes.
- Treat recovered code as untrusted and incomplete; inspect quality.json and diagnostics. Never run recovered game code.
- Compilation and mocked tests do not establish native gameplay equivalence.
- Report confirmed, likely and unknown behavior separately. Cite asset paths, class/method names and native addresses.
- Trace callers, callees, events, state transitions, serialized configuration and assets before claiming full mechanics. Never replace failed methods with invented plausible gameplay.
- Store per-run native addresses, address bases, constant provenance, tool revisions and quality status in the work folder. Never confuse string offsets, instruction-image offsets, file offsets and virtual addresses.
- Treat packages as untrusted archives: write only inside the target folder, cap bytes written and time spent.
- Bound heavy work: at most four workers, one heavy tool at a time, stop background processes, leave Unity out of play mode.
- Do not use Unicorn on this Mac: its memory mapping crashed Python with SIGILL. Use bounded native ARM64 oracle tests where appropriate.
- Preserve third-party tool licenses. Read live state before writes; preserve user edits.
