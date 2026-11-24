# RSI extension

- I read the RSI-top write-up from Azalia Mirhoseini’s group. They gave AI agents a working Python function that writes instructions for a simulated processor. The goal was to get the same answers in fewer clock cycles. [Anthropic’s task](https://github.com/anthropics/original_performance_takehome)
- When the agents got stuck, four planners looked through earlier attempts and suggested what to try next. In the group’s run, ordinary search reached 1,244 cycles. With the planners it reached 1,109. [RSI-top write-up](https://rsi-top.github.io/) · [Code](https://github.com/RSI-top/rsi-top-wrapper)
- I ran their ordinary search on the same task. In my run (seed 52), the fastest correct program the agents wrote took **4,007 cycles**.

## A small compiler for the same task

- I wanted to see how fast I could make Anthropic’s original program with a few rules of my own. I wrote a compiler in Python that reads the original instructions, follows the calculations, and writes a shorter instruction list for the processor.
- One rule looks for a multiply followed by an add. This processor can do both in one instruction. [Arithmetic rules](compiler/rewrite_rules.py)
- The compiler also decides what can run together. While the processor loads a number from memory, it can add two numbers it already has. An addition that needs the number being loaded has to wait. [Scheduling code](compiler/schedule_instructions.py)
- I gave the compiler just Anthropic’s original program. It tried 90 settings for loading values and arranging the instructions. The fastest correct program it built took **1,981 cycles**.

## Could the agents teach it another shortcut?

- Five attempts from my RSI-top run had finished but given wrong answers. I wondered if an agent had sped up one calculation and broken something elsewhere. [Saved attempts](data/README.md)
- I used those saved programs to develop and test a way for the compiler to borrow individual calculations. I gave it the same original program and the same 90 settings, this time with the five attempts to look through as well.
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
