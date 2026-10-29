# Synthetic FP regression harness

This directory tests ARM64 floating comparison flags and branch-condition lowering. The fixture is a synthetic `fcmp s0,s1` plus an LT branch; it contains no game address or recovered gameplay.

On an Apple Silicon Mac, from the repository root:

```sh
mkdir -p ~/apk-work/fp-check
clang -O0 -arch arm64 toolkit/Verification/native-fp-oracle.c \
  toolkit/Verification/native-fp-oracle.s -o ~/apk-work/fp-check/oracle
~/apk-work/fp-check/oracle > ~/apk-work/fp-check/result.json
```

The C model includes normal values, infinities, NaNs and signed zero. Passing validates only these primitives and sampled values, not whole methods or any gameplay equivalence. No recovered game code or Unicorn is executed.

`build_native_oracle.py` can regenerate the model from a compatible patched InstructionLowerer source using --source and --output. The source must match the patterns it asserts; do not ignore failures. The generated fixture is copied from fp-branch-fixture.json into the chosen output. Keep generated reports and executables outside tracked directories.
