# Saved instructions

Each gzip file contains a JSON list. One entry is a cycle’s instruction bundle. Its keys are the machine engines; its values are the instructions issued to each engine. The compiler uses the starter to define the correct output and the agents’ programs to look for other ways to compute the same value.

- **seed52_search_best.json.gz** is the verified 4,007-cycle output of ordinary-search worker 9 in the seed-52 replication. The two-row comparison uses this as its starting score and only the five `native_*` files as sources of shortcuts.
- **seed52** contains the scalar starter and eight programs that ran but returned wrong answers from our RSI-top/OpenEvolve adaptation. A name such as `native_11` means ordinary-search proposal 11. The `handoff` files came from the compiler-feedback branch. Native workers 11 and 12 each supplied the branch shortcut when tested separately.
- **seed54** contains the common starter with that shortcut already applied and all four wrong-output programs. Workers 10 and 21 modified verified parents. Worker 23 started from worker 21’s wrong program, then worker 24 started from worker 23’s. Each failed verification.

These are two runs on the same tree workload. The four programs from seed 54 are used together only in the offline expression replay.
