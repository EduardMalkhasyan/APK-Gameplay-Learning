# Evidence workflow for deep code work

[METHOD.md](METHOD.md) is the practical route: package, engine, assets, code, findings, your own design. This file adds the evidence rules for tracing gameplay through recovered code.

## 1. Inventory before choosing tools

Read AGENTS.md and LESSONS_LEARNED.md. Inspect the exact supplied bytes with `toolkit/inspect_package.py`. Record hashes, container/split names, engine/runtime signals, architecture and versions actually established. Missing signals mean unknown, not proof of another runtime. Multiple engines can coexist.

Do not infer source language from the game genre. Do not assume a downloaded split contains ARM64. Follow ENGINE_ROUTES.md; check current primary documentation when compatibility is uncertain. Choose tools based on architecture, runtime version and expected output depth: names, native ranges, control flow, or expressions.

## 2. Create an isolated work folder

Use `~/Desktop/apk-work/<run-id>/`, outside the repository, and delete it when you are done. Next to METHOD.md's `package.xapk`, `unzipped/` and `assets/`, keep these areas separate:

- `input/`: unchanged input or a reference to its original path and hash.
- `evidence/`: tool revisions, commands, logs, address maps, disassembly and decoded constants.
- `raw/`: untouched tool exports and diagnostics.
- `readable/`: manual reconstructions with source addresses and explicit assumptions.
- `findings/`: mechanic records and original design lessons.

Copy templates/quality.json and templates/MECHANIC.md into the run. Do not overwrite previous exports. Keep failed attempts and record why a tool was rejected. Never commit per-game material.

## 3. Establish what the export can support

Verify metadata/snapshot structure before trusting object graphs. Record each passed, failed and skipped check. Parser success validates structure only. A method name without a native range does not recover a body; strings alone do not prove execution or a mechanic.

Scope application code using assembly, package/library URI, native ownership and asset references. Preserve vendor output as evidence where needed, but do not present it as gameplay. Keep filtering rules explicit.

## 4. Trace one mechanic end to end

Start with an input, timer, collision, event, UI action or state transition. Follow callers, callees, subscriptions, ownership checks, mutations, outputs and persistence. Inspect models and serialized configuration; recover constant arrays and enum selectors rather than guessing values from labels.

For each method record the native range, virtual/file/image address mapping, relevant branches, field layout and unresolved calls. Resolve dynamic dispatch using the target architecture's actual slot width and table origin. Cross-check helpers before naming their operation.

## 5. Produce a small readable reconstruction

Translate only supported instructions and conditions. Preserve call order, arithmetic order, boundary inclusivity, rolling windows, time units and floating-point edge cases. Name inferred fields explicitly. Leave unresolved dependencies external; explain that the file is partial and not standalone. Never replace a failed method with plausible gameplay.

Trace consumers and assets before calling a cached field's meaning or a modifier formula complete. Inspect UI and callers before concluding a missing check is absent from the whole game.

## 6. Validate at the claimed level

Use static evidence checks, compilation, focused simulations and bounded native primitive checks as applicable. State which were actually run. Compilation and mocks do not prove target behavior. Do not execute recovered app code directly. Limit heavy work to four workers, stop background processes and leave Unity out of play mode. Do not use Unicorn on this Mac.

If blocked, record the exact incompatibility, attempted alternatives and smallest next input/action. A tool limitation is not proof that the binary cannot be analyzed. Prefer a reviewable, bounded result over either fabricated completeness or repeated unsupported promises.

## 7. Deliver and generalize

Link actual readable files and evidence. Report confirmed behavior, likely interpretation and unknowns separately. Explain the result's usable scope. For original game development, describe the general pattern and design fresh behavior/code separately from the reconstruction.

Update this repository only with reusable process/tool improvements. Keep case constants, scripts, addresses and reports in the work folder.

## Suggested AI prompt

Read AGENTS.md, docs/METHOD.md, docs/WORKFLOW.md, docs/LESSONS_LEARNED.md and docs/ENGINE_ROUTES.md. Inventory the supplied package in ~/Desktop/apk-work/<run-id>/. Select a compatible route. Read data before code, then trace the requested mechanic across callers, state, data and persistence. Preserve raw evidence; produce small readable reconstructions only where supported. Cite asset paths, method paths and native addresses, separate confirmed/inferred/unknown behavior, and never invent missing methods or copy original game repository source. Finish with the general pattern for an original design: never clone the game.
