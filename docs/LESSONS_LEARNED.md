# Reusable recovery lessons

## Evidence levels

Metadata exposes identities and layout; native instructions support behavior; readable code is reconstruction; inferred names and intent remain interpretation. No export, successful parse, compilation or mocked test automatically proves native equivalence. Exact original source, comments, local names and optimized-away code are generally unavailable.

## Choose the route from the binary

Inspect container, splits, runtime version, architecture and feature flags before choosing tools. Unity IL2CPP, managed assemblies, Flutter AOT, native engines and web payloads need different routes. A tool's ARM64 support says nothing about ARM32. Recheck compatible alternatives before declaring a different build necessary; record the exact tool revision tested.

## Package lessons

- A single APK is often incomplete. Ask for the XAPK/APKS with the `config.arm64_v8a` split and the asset packs or OBB; Unity data and native code frequently live in splits.
- Some games ship only an ARM32 or only an ARM64 native split. Note which one you have before choosing tools.
- Treat packages as hostile archives: refuse entries that would land outside the target folder, cap the bytes actually written (a few GB), and stop on a time budget.
- Watch memory on Unity exports. UnityPy caches a decoded atlas on each file that asks for it, so a game split into hundreds of small files that share atlases can hold one 2048x2048 copy per file, over 10 GB. Clear the cache when the export moves to the next file. On macOS check "peak memory footprint" in `/usr/bin/time -l`: compressed memory hides this from the resident size.

## Asset lessons

- Unity: load `assets/bin/Data`, `assets/aa/**` and every AssetBundle in one UnityPy environment; otherwise reading textures, audio and meshes fails with "Resource file … not found" because their `.resS` and `.resource` streams do not resolve.
- Unity values (ScriptableObjects, MonoBehaviours) read directly only when type trees exist: AssetBundles keep them, player builds usually strip them. Type trees can be generated from Mono DLLs or IL2CPP metadata, but this failed on Unity 6000.x IL2CPP in October 2026.
- Unity meshes: export by usage (MeshFilter/SkinnedMeshRenderer references), skip collider hulls and duplicates, and convert handedness (UnityPy's OBJ export already mirrors X and flips winding). Rigs, animation clips, materials and scenes need AssetRipper.
- TextMeshPro fonts are usually SDF atlases without a TTF.
- Flutter draws its UI in code: there are no UI images to extract, so study layout and colors from screenshots and video.
- Contact sheets (thumbnail grids) are the fastest way to understand a game's art set before opening single files.

## Unity IL2CPP lessons

The pinned Cpp2IL base is b5ad444b82267cb1e4b88b8b373c008105bdea52; generic changes are in toolkit/cpp2il-recovery-v2.patch.

- Preserve parameter slots and separate general/FP argument registers; handle homogeneous aggregates explicitly.
- Resolve metadata indirection, field-address aliases, FP constants and proven barrier/exception helpers.
- Preserve Boolean types and IEEE754 flags, including unordered NaN comparisons and signed zero.
- Restore attributes from metadata rather than inventing annotations.
- Async/byref state machines, aggregate returns, exception regions, interface/generic dispatch and unknown instructions remain incomplete. Default structs after lost native returns are not recovered animation/gameplay behavior.

## Flutter/Dart AOT lessons

- AOT native code is not Dart bytecode. Names and library URIs can survive, but strings alone do not recover bodies.
- Match snapshot hash, runtime epoch, pointer compression, word size and architecture. Validate cluster bounds, reference ranges, instruction tables and field layouts; preserve skipped checks.
- Distinguish source-URI string offsets, instruction-image offsets, ELF file offsets and virtual addresses. Save the base mapping and actual native range for every reconstructed method.
- ARM32 code uses target-specific argument conventions, split 64-bit integers and tagged object pointers. Do not transplant ARM64 register names, pool offsets or dispatch-table origins.
- Decode pool doubles from their actual words and constant lists through object references. Do not guess thresholds, multipliers, enum identities or units.
- Resolve indirect calls using metadata and independent witnesses. Some tool presentation fields can retain architecture assumptions even when parsing succeeds; check the instruction displacement against the table yourself.
- Raw control-flow output can mix instructions with pseudo-Dart. Keep it as evidence; do not label it executable source. Small manual translations can be useful while dependencies remain explicitly unresolved.

## Behavior and validation lessons

Preserve check order, callback order, state invalidation, save scheduling, accepted/rejected inputs and numeric edge cases. A zero quoted price does not prove a free purchase if a separate ownership guard rejects it. Similar names do not establish identical behavior. Cached income can hide modifiers outside the current method. Missing checks in one method may exist in its callers or UI.

Use compiler checks for syntax/contracts, mocks for explicit modeled cases, and native primitive tests for the exact instruction semantics they exercise. None establish whole-game equivalence. Preserve the output and scope of actual checks; do not carry a case's test count into a new recovery as proof.

## Reading lessons

- Read data before code: level files, ScriptableObjects, localization tables and constant pools give exact numbers faster than method bodies.
- When code is unreadable, measure from store screenshots and gameplay video frame by frame, and label those numbers as observed.
- Prefer what players actually see when the build and the store disagree, and note the mismatch.

## Repository boundary

This repository holds tools, method docs, blank templates and synthetic examples only: no game's files, ever. Work in `~/Desktop/apk-work/<run-id>/` outside the repository and delete it afterwards. Learn the pattern and never clone the game. Tool repositories can inform generic fixes; original game repository source must never fill recovery gaps. Keep all upstream licenses.
