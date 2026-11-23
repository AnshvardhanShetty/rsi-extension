# Saved instructions

Each gzip file contains a JSON list. One entry is a cycle’s instruction bundle. Its keys are the machine engines; its values are the instructions issued to each engine. The compiler uses the starter to define the correct output and the worker files to suggest alternative expressions.

- **seed52** contains the scalar starter and eight wrong programs from our RSI-top/OpenEvolve adaptation. A name such as `native_11` means ordinary-search proposal 11. The `handoff` files came from the compiler-feedback branch. Native workers 11 and 12 each supplied the branch shortcut when tested separately.
- **seed54** contains the common starter with that shortcut already applied and all four wrong-output programs. Workers 10 and 21 modified verified parents. Worker 23 started from worker 21’s wrong program, then worker 24 started from worker 23’s. Each failed verification.

These are two runs on the same tree workload. The four later workers are used together only in the offline expression replay.
