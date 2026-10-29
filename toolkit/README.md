# Practical recovery toolkit

## Inventory any new input first

```sh
python3 toolkit/inspect_package.py ~/Desktop/apk-work/<run-id>/package.xapk
```

Standard-library-only, read-only inventory for ZIP-based APK/XAPK/AAB/IPA packages and direct ELF libraries. APK splits are inspected one level deep without extracting their filenames. Outputs hashes, observed ABI paths/ELF architecture, payload locations and heuristic runtime signals. It does not recover code, infer gameplay, parse every engine version, detect every custom runtime or resolve encrypted assets. Keep its output in the work folder, outside the repository.

See ../docs/METHOD.md for assets and the next tool to select. The remaining command is Unity-specific.

## Unity Mono / IL2CPP export

Requires Python 3 and .NET 10. The bundled patched engine was exercised on macOS ARM64; other host/target combinations remain unverified.

```sh
python3 toolkit/recover_gameplay.py ~/Desktop/apk-work/<run-id>/package.xapk \
  --output ~/Desktop/apk-work/<run-id>/unity-export
```

Select application namespaces explicitly when known:

```sh
python3 toolkit/recover_gameplay.py ~/Desktop/apk-work/<run-id>/package.xapk \
  --output ~/Desktop/apk-work/<run-id>/unity-export \
  --include-namespace YourGame
```

Existing outputs are rejected. APK/XAPK are supported by this wrapper; AAB/IPA inventory support does not imply export support. Managed Unity inputs use ILSpy; IL2CPP uses the patched native body recovery and metadata attributes. Use --unity-version only when established independently, and --assemblies for game-specific managed assemblies beyond Assembly-CSharp.

Exit 2 means partial export with a blocked gate. Read quality.json and all diagnostics. Namespaces without vendor prefixes are not automatically game-owned; vendor filtering is heuristic. Files with no warnings remain unverified. Native address maps and input/tool hashes are retained when available.

## Tool provenance

Engine contains pinned Cpp2IL development.1743 dependencies and rebuilt Core. Base commit: b5ad444b82267cb1e4b88b8b373c008105bdea52. ILSpy contains official ilspycmd 11.1.0.9782 tools. cpp2il-recovery-v2.patch records generic changes; the patched Core reads `TOOLKIT_RECOVERY_*` environment variables. Licenses: Cpp2IL-LICENSE.txt and ILSpy-LICENSE.txt (MIT plus third-party notices). Preserve upstream licenses/notices.

## Unity assets

`export_unity_assets.py` exports sprites, textures, audio, meshes, fonts, text assets and script values with UnityPy; see ../docs/METHOD.md step 3. The output folder must be outside this repository.

- https://github.com/SamboyCoding/Cpp2IL
- https://github.com/icsharpcode/ILSpy

See RESEARCH.md for known gaps. Verification/ contains synthetic native FP checks, not gameplay samples. No per-game script or quality report belongs in the tracked toolkit.
