# Mechanic: <name>

## Input and scope

- Input hash / run ID:
- Runtime / version / architecture:
- App-owned package, assembly or library:
- Tool revision, commands and raw export:
- Requested behavior and current coverage:

## Evidence

| Method / data | Native range or asset path | Address basis | Supporting instructions / references | Unresolved parts |
| --- | --- | --- | --- | --- |
| <entry point> | <range> | <VA, file offset, image base> | <evidence file> | <gap> |

## Behavior trace

Trigger → guards → calls → state mutations → outputs → persistence.

Record timing, inclusivity, arithmetic/callback order, constants and configuration provenance. Follow callers, events, consumers, scene/asset wiring and cancellation/reset paths.

## Confirmed

Only rules directly supported by recorded evidence.

## Likely interpretation

Inferred names, intent and integration choices, with their reasons.

## Unknown

Missing methods, unknown instructions, dependencies, serialized data and untraced callers.

## Readable reconstruction

File links, method-to-native mapping and explicit assumptions. Explain external contracts and whether this is standalone. Never fill gaps with invented behavior.

## Validation

Actual checks run, failures/skips and the exact scope they establish. Explicitly state whether compilation, engine execution and native-equivalence checks were performed.

## Original design lesson

General pattern and a distinct design/application. Keep original implementation separate from recovered material.
