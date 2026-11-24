# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. They had AI agents edit a working program to make it faster. When progress stalled, four planners looked back at earlier attempts and suggested what the agents should try next. [RSI-top write-up](https://rsi-top.github.io/)

I ran their search on the same puzzle to try two ideas.

- One agent sped up a program by changing which instructions ran together. Could I write a small Python compiler to do that automatically?
- What can we learn from a program that gives the wrong answer? Maybe the agent found a shortcut and broke something else. Could I check the shortcut and use it in a working program?

## My RSI-top run

- Used a saved run on Anthropic’s puzzle. Fewer clock cycles means faster code. [Puzzle](https://github.com/anthropics/original_performance_takehome)
- Workers tried edits on their own. Fastest correct program took **4,007 cycles**.
- Five attempts gave wrong answers. Kept all five. [Saved programs](data/README.md)

## My compiler

- An earlier agent sped things up by running instructions together.
- A small Python script almost matched that speedup. That gave me the idea.
- Built a compiler to group work automatically and combine steps like multiply and add. [Rules](compiler/rewrite_rules.py) · [Scheduling code](compiler/schedule_instructions.py)
- Original program alone. Tried 90 settings and got **1,981 cycles**.

## Borrowing a shortcut

- Workers 11 and 12 found the same shortcut in programs that failed.
- Original code used two steps. Check for zero, then choose a value.
- Workers swapped the two choices and skipped the check. The choice instruction already handles zero.
- Verified both versions always pick the same value. [Proof](results/zero_test.smt2)
- Added the five saved attempts. Same 90 settings. **1,269 cycles**, all nine tests passed.
- Added just that shortcut by hand as a check. Got the same program.

## Run it

- Python 3.10+ and Z3. No API key.
- Install Z3 with `brew install z3` (macOS) or `sudo apt install z3` (Ubuntu).
- Run from the repo root.

```sh
git clone https://github.com/anthropics/original_performance_takehome.git benchmark
git -C benchmark checkout 5452f74bd977807ac2e74f3d29432b9df6f25197
python3 run_experiment.py --compare-search
```

- `--compare-search` checks the 4,007- and 1,269-cycle programs on eight fresh inputs.
- `python3 run_experiment.py` reproduces the 1,981-cycle result and the handwritten shortcut check. [Experiment code](run_experiment.py)

<details>
<summary>Run Anthropic’s nine tests</summary>

```sh
cp output/seed52/failed_workers.json.gz benchmark/
cp benchmark_entry.py benchmark/perf_takehome.py
python3 benchmark/tests/submission_tests.py
git -C benchmark diff HEAD -- tests/ problem.py
```

- Expected output is nine passing tests and an empty git diff.

</details>
