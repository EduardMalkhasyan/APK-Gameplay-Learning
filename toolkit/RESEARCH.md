# Generic recovery research

## Preserved Unity tooling changes

The Cpp2IL base is b5ad444b82267cb1e4b88b8b373c008105bdea52. The patch retains generic fixes for ARM64 argument/aggregate handling, field aliases, metadata indirection, attributes, Boolean typing and floating comparison flags. Existing generic code and upstream licenses remain intact.

The FP regression harness models NZCV and condition lowering across normal values, infinities, NaNs and signed zero. It is a primitive test, not a game behavior test. Run reports belong in ignored local runs. The committed compare/branch fixture is synthetic and has no game method/address attached.

A bounded native call-chain check recognizes proven exception raisers before interpreting synthetic return registers as values. Stop inspection at conditional/indirect control flow, returns, traps and bounds. This does not recover complete exception regions.

Remaining gaps include async/byref state machines, field-address generation, aggregate returns, exception/unwind regions and some interface/generic/delegate dispatch. Improved diagnostics do not establish full semantic correctness.

## Cross-runtime findings

Flutter analysis reinforced engine/ABI detection, snapshot validation, exact native range mapping, constant-pool decoding and architecture-specific dispatch checking. General instructions are in docs/ENGINE_ROUTES.md and docs/LESSONS_LEARNED.md. Per-game scripts, names, native addresses and measured run reports are deliberately excluded from tracked material.

## Primary research references

- https://github.com/SamboyCoding/Cpp2IL
- https://github.com/morluto/rea/blob/main/docs/native-investigation.md
- https://github.com/syzozpro/Cpp2iL/tree/507dd2503d216d9316ef5803365f536b5e6f06f4
- https://github.com/LukeFZ/Il2CppInspectorRedux
- https://github.com/IR0NBYTE/Jadart

Tool source can explain generic fixes. Do not copy original game repository source to repair recovered gameplay.
