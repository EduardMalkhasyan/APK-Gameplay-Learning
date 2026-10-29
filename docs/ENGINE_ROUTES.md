# Engine and runtime routes

Code-recovery details per runtime. [METHOD.md](METHOD.md) has the engine signals, asset extraction and the reading order; this file adds limits and commands. This is a routing guide, not a promise of universal decompilation. The inventory command reports heuristic signals; inspect ambiguous or mixed packages manually. Verify current primary documentation before installing tools or relying on version/architecture support.

| Evidence in input | Route | Practical output and limits |
| --- | --- | --- |
| Unity data plus managed game DLLs | Unity Mono: ILSpy | Managed method bodies; stripped dependencies and asset wiring can remain missing. |
| libil2cpp plus global-metadata.dat | Unity IL2CPP: toolkit/recover_gameplay.py | Partial C# interpretation, diagnostics and native address map. |
| libapp.so, libflutter.so, flutter_assets | Flutter AOT: snapshot parser plus native analysis | Classes, constants, native ranges and supported pseudocode; depends on Dart epoch and ABI. |
| DEX with app-owned logic | Android Java/Kotlin: JADX | Java-like code; JNI/native and framework/plugin code require separate tracing. DEX also exists in many engine wrappers. |
| Native game libraries | Native: Ghidra/IDA/Hopper or disassembler | Native pseudocode and call/layout evidence; no guaranteed original language or names. |
| Godot payloads/resources | Godot: match engine/script format first | Text scripts may survive; compiled scripts, native extensions and packs require version-specific tools. |
| Unreal native libraries and cooked assets | Unreal: native + asset analysis | Partial native/Blueprint/config evidence; inspect shipping format and engine version. |
| Cocos `.jsc` plus libcocos*.so | Cocos: xxtea key from library strings, decrypt, gunzip | Full JS when the key is found; Cocos Creator 3.x may ship plain JS. |
| index.android.bundle | React Native: plain JS or hermes-dec for Hermes bytecode | JS or pseudo-JS; native modules need separate tracing. |
| game.droid plus libyoyo.so | GameMaker: UndertaleModTool | GML for VM builds; YYC builds are native code. |
| JavaScript, Lua, web assets or WebAssembly | Match script/bytecode/runtime | Read surviving text; inspect obfuscation, bytecode and native host boundaries separately. |
| Unknown/custom/protected runtime | Inventory and native investigation | Preserve unknown status. Do not force a Unity/Flutter pipeline onto it. |

## Unity

See toolkit/README.md. Use a new output directory, inspect quality.json and preserve logs. Explicitly select app assemblies/namespaces. The included wrapper supports Unity only.

## Flutter / Dart

An external Jadart checkout exercised during investigation was commit `25b44c378ad3d475c784d8f8833eae0d4ab5d0db`. Its observed route parsed a Dart 3.12.2 ARM32 snapshot and emitted Tier 2 control flow. This is one compatibility observation, not coverage of every Flutter app. No Flutter parser is bundled here.

Check the external checkout's license and instructions, then record its revision. Example commands after installation:

```sh
jadart info /absolute/path/libapp.so
jadart verify /absolute/path/libapp.so
jadart classes /absolute/path/libapp.so -l package:<app>/
jadart functions /absolute/path/libapp.so -l package:<app>/ -n 0
jadart disasm /absolute/path/libapp.so <native-address>
jadart export /absolute/path/libapp.so -o ~/apk-work/<run-id>/raw -t 2 -a
```

Use `--help` from the installed revision; CLI and support can change. `-a` may include non-framework vendor packages, so scope app-owned library URIs explicitly. Preserve the whole raw export but present only verified app-owned ranges as gameplay. Class listings and per-library exports can expose different subsets of functions; compare their native range inventories before calling a method absent.

Inspect pool constants, dynamic dispatch and helpers manually. Do not force a higher tier on an unsupported architecture, and never turn unresolved instructions into guessed expressions.

On arm64 snapshots Blutter is the usual first try: it prints names and assembly annotated with object-pool values.

## Primary tool references

Code:

- Cpp2IL: https://github.com/SamboyCoding/Cpp2IL
- Il2CppDumper: https://github.com/Perfare/Il2CppDumper
- Il2CppInspectorRedux: https://github.com/LukeFZ/Il2CppInspectorRedux
- ILSpy: https://github.com/icsharpcode/ILSpy
- Jadart: https://github.com/IR0NBYTE/Jadart
- Blutter: https://github.com/worawit/blutter
- JADX: https://github.com/skylot/jadx
- hermes-dec: https://github.com/P1sec/hermes-dec
- Ghidra: https://github.com/NationalSecurityAgency/ghidra

Assets:

- UnityPy: https://github.com/K0lb3/UnityPy
- AssetRipper: https://github.com/AssetRipper/AssetRipper
- GDRE Tools: https://github.com/GDRETools/gdsdecomp
- FModel: https://github.com/4sval/FModel
- UndertaleModTool: https://github.com/UnderminersTeam/UndertaleModTool
- vgmstream: https://github.com/vgmstream/vgmstream

These links identify tools to inspect, not untested claims about their latest compatibility. No target app is executed by the inventory command.
