# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. They had AI agents edit a working program to make it faster. When progress stalled, four planners looked back at earlier attempts and suggested what the agents should try next. [RSI-top write-up](https://rsi-top.github.io/)

I wanted to try this on the same puzzle and see what I could speed up with a small Python compiler of my own. This repo has the compiler and the programs I saved from my run.

## What I ran from RSI-top

- The puzzle comes from Anthropic. You’re given Python code that writes instructions for a simulated processor. The goal is to get the right answers in fewer clock cycles. [Anthropic’s task](https://github.com/anthropics/original_performance_takehome)
- RSI-top uses a search tool called OpenEvolve. An agent edits a program, the evaluator checks and times it, and later agents can build on earlier versions. In the group’s experiment, ordinary search reached 1,244 cycles. Adding planners brought it to 1,109. [Their code](https://github.com/RSI-top/rsi-top-wrapper)
- For my run I used their ordinary search on the same puzzle. The fastest correct program the agents wrote took **4,007 cycles** (seed 52). I saved their attempts and ran my compiler afterward.

## My compiler on the original program · 1,981 cycles

- In an earlier run, an agent had sped up a program mostly by changing which instructions ran together. A small Python script almost matched that speedup just by grouping instructions. That gave me the idea for the compiler.
- My compiler reads the working program and looks for things the processor can do in one cycle. It can combine a multiply and an add, or do arithmetic while it waits for a different value to load. [Arithmetic rules](compiler/rewrite_rules.py) · [Scheduling code](compiler/schedule_instructions.py)
- I gave it Anthropic’s original program alone. It tried 90 settings for arranging the work. The fastest program it built took **1,981 cycles**.

## Same compiler with five failed attempts · 1,269 cycles

- Five programs from my RSI-top run gave wrong answers. I wondered if one had a good shortcut buried in it. I used these saved attempts to build and test a way for the compiler to borrow one calculation at a time. [Saved attempts](data/README.md)
- Workers 11 and 12 had found the same shortcut. The original program checked “is this number zero?” before choosing between two values. The choice instruction could already handle zero. The workers swapped the two choices and dropped the extra check.
- The compiler verified that both versions always picked the same value. With the shorter version, it could also load some values earlier. [The check](results/zero_test.smt2)
- Same original program, same 90 settings. With the failed attempts to borrow from, the compiler got to **1,269 cycles** and passed all nine tests. Giving it just that one shortcut by hand produced the exact same program.

## Replay the compiler experiment

Use Python 3.10+ and Z3. Install Z3 with `brew install z3` on macOS or `sudo apt install z3` on Ubuntu. Run from the repo root. No API key needed.

```sh
git clone https://github.com/anthropics/original_performance_takehome.git benchmark
git -C benchmark checkout 5452f74bd977807ac2e74f3d29432b9df6f25197
python3 run_experiment.py --compare-search
```

- `--compare-search` checks the saved agent program (4,007 cycles) and rebuilds the program using the five failed attempts (1,269 cycles). It checks both on eight fresh inputs.
- Run `python3 run_experiment.py` for the compiler alone (1,981 cycles), the handwritten shortcut check, and a replay with eight attempts from two search branches. [Experiment code](run_experiment.py)

<details>
<summary>Run Anthropic’s nine tests</summary>

```sh
cp output/seed52/failed_workers.json.gz benchmark/
cp benchmark_entry.py benchmark/perf_takehome.py
python3 benchmark/tests/submission_tests.py
git -C benchmark diff HEAD -- tests/ problem.py
```

Expect nine tests to pass and the last command to print nothing.

</details>
