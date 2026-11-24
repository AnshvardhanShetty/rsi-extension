# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. They had AI agents edit a working program to make it faster. When progress stalled, four planners looked back at earlier attempts and suggested what the agents should try next. [RSI-top write-up](https://rsi-top.github.io/)

I tried the same puzzle. In one run, an agent made its program faster mostly by changing which instructions ran together. That got me writing a small compiler to try the same thing. Then I got curious about the programs that failed. If an agent got one step right and messed up the next one, could I still use the good bit?

## My RSI-top run

- The agents were trying to finish Anthropic’s puzzle in fewer clock cycles. The fastest correct program in my saved run took **4,007 cycles**. [Puzzle](https://github.com/anthropics/original_performance_takehome)
- Five other programs ran but gave wrong answers. I kept those too. [Saved programs](data/README.md)

## My compiler

- I took the program that agent had started from and wrote a Python script to group instructions together. That alone got close to the agent’s speedup.
- I added a few rules for the processor. For example, it can multiply two numbers and add a third in one instruction. [Rules](compiler/rewrite_rules.py) · [Scheduling code](compiler/schedule_instructions.py)
- I gave the compiler Anthropic’s original program on its own. It tried 90 settings for arranging the instructions. Its best program took **1,981 cycles**.

## Back to the failed attempts

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
