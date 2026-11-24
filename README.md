# RSI extension

- I read the RSI-top write-up from Azalia Mirhoseini’s group. They gave AI agents a working Python function that writes instructions for a simulated processor. The goal was to get the same answers in fewer clock cycles. [Anthropic’s task](https://github.com/anthropics/original_performance_takehome)
- When the agents got stuck, four planners looked through earlier attempts and suggested what to try next. In the group’s run, ordinary search reached 1,244 cycles. With the planners it reached 1,109. [RSI-top write-up](https://rsi-top.github.io/) · [Code](https://github.com/RSI-top/rsi-top-wrapper)
- I wondered about the attempts that gave wrong answers. What if an agent sped up one calculation but broke something else? Could I keep the bit it got right?

## My run

- I ran RSI-top’s ordinary search on the same task. In my run (seed 52), the agents’ fastest correct program took **4,007 cycles**.
- I saved five programs from that run that gave wrong answers. After the agents finished, I used those programs to develop and test a small compiler in Python. [Saved attempts](data/README.md)

## What my compiler does on its own

- I give it Anthropic’s original working program. It follows the calculations and writes a new set of instructions to get the same answer.
- I wrote a few rules for this processor. For example, it can multiply two numbers and add a third in one instruction. The compiler looks for places to use that. [Arithmetic rules](compiler/rewrite_rules.py)
- It also decides which instructions can run together. While the processor loads a number from memory, it can do an addition that only needs numbers it already has. [Scheduling code](compiler/schedule_instructions.py)
- With just the original program, the compiler tried 90 settings for loading values and arranging instructions. Its fastest correct program took **1,981 cycles**. That’s how far it got before I gave it any of the agents’ code.

## What the failed attempts added

- I ran the same compiler with the same 90 settings, this time letting it borrow calculations from the five failed programs.
- Workers 11 and 12 had each found the same shortcut. The original used one instruction to check if a number was zero, then another to pick a value. The instruction that picks the value can already tell zero from nonzero.
- The workers skipped the check and swapped the two choices. My tool verified that this always picked the same value as the original. [The check](results/zero_test.smt2)
- With the shortcut, the compiler could also load some values earlier. The rebuilt program took **1,269 cycles** and passed all nine tests. Giving the compiler just that shortcut by hand produced the exact same program.

## Try it

- Use Python 3.10+ and Z3. To install Z3, run `brew install z3` on macOS or `sudo apt install z3` on Ubuntu.
- From the root of this repo, replay the saved run locally. No API key needed.

```sh
git clone https://github.com/anthropics/original_performance_takehome.git benchmark
git -C benchmark checkout 5452f74bd977807ac2e74f3d29432b9df6f25197
python3 run_experiment.py --compare-search
```

- This checks the agents’ 4,007-cycle program and the compiler’s 1,269-cycle program on eight fresh inputs. [Experiment code](run_experiment.py)
- Run `python3 run_experiment.py` to reproduce the 1,981-cycle compiler-only result and the handwritten shortcut check. This also replays all eight saved attempts from both search branches.
- To run Anthropic’s own tests on the rebuilt program, use the commands below. Expect nine tests to pass and the final command to print nothing.

```sh
cp output/seed52/failed_workers.json.gz benchmark/
cp benchmark_entry.py benchmark/perf_takehome.py
python3 benchmark/tests/submission_tests.py
git -C benchmark diff HEAD -- tests/ problem.py
```
