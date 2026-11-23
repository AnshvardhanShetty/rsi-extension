# RSI extension

Can a worker write a wrong program that still contains an optimization worth keeping? I tried this on the tree kernel from Anthropic’s performance take-home, using programs saved from an adaptation of RSI-top’s OpenEvolve search.

On seed 52, the compiler found a simpler branch in a failed worker. In pseudocode, `choose(x == 0, a, b)` gives the same answer as `choose(x, b, a)`. Removing the extra comparison let the compiler preload more of the tree. The resulting program took **1,269 simulated cycles**, down from **1,981**. Giving the compiler that rule by hand produced the same instructions. On fresh seed 54, the failed workers added no improvement.

## Run the experiment

Use Python 3.10+ and the Z3 command-line solver (`brew install z3` on macOS or `sudo apt install z3` on Ubuntu). Run these commands from the root of this repo.

```sh
git clone https://github.com/anthropics/original_performance_takehome.git benchmark
git -C benchmark checkout 5452f74bd977807ac2e74f3d29432b9df6f25197
python3 run_experiment.py
python3 run_experiment.py --seed 54
```

Each row tries the same 90 schedules and checks all 256 output values on eight fresh trees. The replay runs locally. It reads saved machine instructions and needs no model key.

| Run | What the compiler gets | Expected cycles |
| --- | --- | ---: |
| 52 | Starter and ordinary arithmetic rules | 1,981 |
| 52 | Same inputs plus eight wrong programs | 1,269 |
| 52 | Starter and rules, including the branch shortcut | 1,269 |
| 54 | Starter and rules, including the branch shortcut | 1,269 |
| 54 | Same inputs plus four wrong programs | 1,269 |

The compiler traces one input lane through each program. Matching values on sample trees suggest two expressions might be interchangeable. Z3 checks that local identity over 32-bit words before the compiler can use it. Running the whole program against the reference checks the final output.

## Run the original submission tests

After replaying seed 52, copy the saved instructions and their small loader into the benchmark checkout created above. This replaces its example submission.

```sh
cp output/seed52/failed_workers.json.gz benchmark/
cp benchmark_entry.py benchmark/perf_takehome.py
python3 benchmark/tests/submission_tests.py
git -C benchmark diff HEAD -- tests/ problem.py
```

Expected: 1,269 cycles, nine passing tests, and an empty diff. To check the branch identity by itself, run `z3 results/zero_test.smt2`. It prints `unsat` if there is no counterexample.

## Code

| File | What it does |
| --- | --- |
| [run_experiment.py](run_experiment.py) | Read the workers, compile each version, and check the outputs |
| [read_instructions.py](compiler/read_instructions.py) | Follow one value through the worker’s instructions |
| [rewrite_rules.py](compiler/rewrite_rules.py) | List the arithmetic shortcuts the baseline already knows |
| [prove_equivalence.py](compiler/prove_equivalence.py) | Check matching expressions and choose how to compute the output |
| [simplify_lookups.py](compiler/simplify_lookups.py) | Replace small tree lookups with preloaded values |
| [schedule_instructions.py](compiler/schedule_instructions.py) | Choose which operations run together in each cycle |

## What happened with live workers?

The 1,269-cycle program was built **after** the search. Seed 54 tested whether a useful edit could be recovered in time to give it to another worker. Ordinary search reached 2,260 verified cycles in 24 attempts. Four workers returned wrong answers. The frozen screen tried 32 edits from the two whose parents were correct. None improved its parent, so we stopped before the handoff. A later offline check tried 128 grouped edits and also found no improvement. [Edit results](results/seed54_edits.json)

An earlier experiment asked a different question: does telling workers how the compiler packs their instructions help? Both branches started from the same checkpoint and got eight model replies. The feedback branch won one pair by one cycle and lost the other two. To read the scores and check the recorded verifier results, run `python3 experiments/compare_checkpoints.py`. [Paired checkpoints](results/paired_checkpoints.json)

Independent, AI-assisted project by Anshvardhan Shetty. The benchmark and search harness are upstream projects. [Anthropic benchmark](https://github.com/anthropics/original_performance_takehome) · [RSI-top](https://github.com/RSI-top/rsi-top-wrapper)
