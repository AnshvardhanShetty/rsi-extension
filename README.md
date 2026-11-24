# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. One experiment used a puzzle from Anthropic. You get a working Python function that writes instructions for a simulated processor. The challenge is to get the same answers in fewer clock cycles. [Anthropic’s puzzle](https://github.com/anthropics/original_performance_takehome)

The group had AI agents edit the function and test each version. When progress stalled, four planners looked back through earlier attempts and suggested what the workers should try next. [RSI-top write-up](https://rsi-top.github.io/)

I ran their search on the same puzzle and came away with two questions.

- One worker had sped up its program by changing which instructions ran together. Could a small Python compiler do that automatically?
- Some programs ran all the way through and gave the wrong answer. Could the compiler pick out a step one of those workers did well and reuse it in a working program?

## My RSI-top run

- I used a saved run where the workers tried edits on their own. Their fastest correct program took **4,007 cycles**.
- I kept five programs that ran but failed the tests. [Saved programs](data/README.md)

## My compiler

- In the earlier scheduling example, I took the program the worker started from and wrote a Python script to group instructions together. That alone got close to the agent’s speedup.
- I added a few rules for the processor. For example, it can multiply two numbers and add a third in one instruction. [Rules](compiler/rewrite_rules.py) · [Scheduling code](compiler/schedule_instructions.py)
- I gave the compiler Anthropic’s original program on its own. It tried 90 settings for arranging the instructions. Its best program took **1,981 cycles**.

## Borrowing a shortcut

- I gave the same compiler the five wrong programs to see if any had a shortcut it had missed.
- Two did. Workers 11 and 12 both skipped a check for zero. The next instruction could already choose between two values based on whether the number was zero.
- They swapped the two choices and saved an instruction. I checked that it still picked the right value for every possible input to that step. [The check](results/zero_test.smt2)
- Same 90 settings as before. This time the compiler got **1,269 cycles** and passed all nine tests.
- I tried giving it just that one shortcut by hand. It built the exact same program.

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
