# Mechanic: tap income with an upgrade multiplier (synthetic example)

A made-up game, "Pocket Bakery", invented to show how to fill [templates/MECHANIC.md](../templates/MECHANIC.md). Every name, path and number below is fictional; nothing comes from a real package.

## Input and scope

- Input hash / run ID: `sha256:<hash>` / `2026-10-29-pocket-bakery`
- Runtime / version / architecture: Unity 2022.3 IL2CPP, arm64-v8a
- App-owned code: namespace `PocketBakery` (ads and analytics SDKs ignored)
- Tools: UnityPy 1.25.4 for data; Cpp2IL for names and RVAs; Ghidra for the tap method body
- Requested behavior: how much one tap earns, and how upgrades change it

## Evidence

| Method / data | Where | Address basis | Supports | Unresolved |
| --- | --- | --- | --- | --- |
| `TapButton.OnTap` | RVA `0x1A2B3C` | libil2cpp.so image base | calls `Economy.AddCoins(TapValue())` | none |
| `Economy.TapValue` | RVA `0x1A2C10` | same | `baseTap * multiplier`, rounded down | one helper call not named |
| `UpgradeConfig` ScriptableObject | `assets/aa/.../upgrades.bundle` | type tree in the bundle | `baseTap = 1`, `multiplier` per level `[1, 2, 3, 5, 8]` | none |

## Behavior trace

Tap → `TapButton.OnTap` → guard: not paused and the tutorial step is done → `Economy.TapValue()` → `AddCoins` → coin counter animates → save scheduled (2 s, inferred).

## Confirmed

- `Economy.TapValue` computes `floor(baseTap × multiplier[level])` before one unnamed helper call (Ghidra at RVA `0x1A2C10` + bundle values). Whether that helper changes the result is unknown, so the full tap formula is not confirmed yet.
- Taps are ignored while paused (guard in `TapButton.OnTap`, RVA `0x1A2B3C`).

## Likely interpretation

- The 2 s save delay batches fast tapping (inferred from a timer field name, no caller seen yet).

## Unknown

- The unnamed helper inside `TapValue`: possibly a temporary boost.

## Readable reconstruction

None needed; the rule fits in one line above.

## Validation

Static reading only. Nothing was compiled or executed.

## Original design lesson

The pattern: a tiny base value, multipliers that grow a little faster than linearly, and visible feedback on every tap. In my own game I use it for watering plants. Each tool tier speeds up growth, and the values, art and names are my own. I also add a short combo window, an idea the studied game did not have.
