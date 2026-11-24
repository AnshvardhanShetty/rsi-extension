# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. They gave AI agents a coding puzzle from Anthropic. The Python code already works. The goal is to make it produce instructions that finish in fewer clock cycles. [Anthropic’s puzzle](https://github.com/anthropics/original_performance_takehome)

The workers edit the code and test each version. When they get stuck, four planners look through earlier attempts and suggest what to try next. [RSI-top write-up](https://rsi-top.github.io/)

I ran the workers on the same puzzle and saved their attempts. The scores told me which programs were faster. To see where the speedups came from, I looked at the instructions before and after a worker’s edit. I kept the attempts that failed, too. A wrong final answer didn’t tell me which part had gone wrong.

## RSI-top run

- The workers tried edits on their own. Their fastest correct program took **4,007 cycles**.
- Five other programs ran but gave wrong answers. [Saved programs](data/README.md)

## Compiler

- In an earlier run, a worker sped up a program by grouping instructions. The processor could do two things in the same clock cycle instead of doing one and then the other.
- I tried that on the program the worker had started from. A short Python script grouped the instructions automatically and got close to the worker’s speedup.
- That script grew into a small compiler. It also looks for steps the processor can combine, like a multiply and an add in one instruction. [Rules](compiler/rewrite_rules.py) · [Scheduling code](compiler/schedule_instructions.py)
- Given only Anthropic’s original program, it tried 90 ways to arrange the work. The fastest took **1,981 cycles**.

## Shortcut from a failed attempt

- I went back to the five failed attempts. Had any worker found a quicker way to do one calculation, even if the whole program was wrong? I gave the compiler those attempts to check against the original.
- Workers 11 and 12 had both skipped a step. The original checked for zero before choosing a value. The choice instruction already handled zero.
- The workers swapped the two choices and dropped the extra check. The compiler verified that both versions always picked the same value. [The check](results/zero_test.smt2)
- With the same 90 settings, the rebuilt program took **1,269 cycles** and passed all nine tests.
- Giving the compiler just that shortcut by hand produced the same program.

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
