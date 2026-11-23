# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. One of their experiments used a coding task from Anthropic. Anthropic gives you a working Python function that writes instructions for a simulated processor. The processor runs those instructions on a tree of numbers. The challenge is to change the function so it produces the same answers in fewer cycles. [Anthropic’s task](https://github.com/anthropics/original_performance_takehome)

The group used AI agents to edit that Python function and test each version. When progress stalled, four planner agents looked back through earlier attempts and suggested edits for the workers to try next. In the run they describe, ordinary search got to 1,244 cycles. With the planners it got to 1,109. [Their write-up](https://rsi-top.github.io/) · [Their code](https://github.com/RSI-top/rsi-top-wrapper)

I wondered about the versions that failed the tests. An agent might have found a quicker way to do one calculation and made a mistake somewhere else. Could I take just the part it got right?

## What I tried

1. I ran my own RSI-top search and saved the instructions from eight versions that gave wrong answers. This is where the agents’ part of the experiment ended. [The eight attempts](data/README.md)
2. I wrote a Python compiler that reads the instructions from the working program, works out what they calculate, and writes a new set of instructions for the same job. It has a few rules of its own. For example, it can group eight inputs together so one instruction does the same arithmetic on all eight. Using only the working program, it produced a version that took **1,981 cycles**.
3. I then let the same compiler read the eight saved attempts too. In the instructions from workers 11 and 12, it found a shorter way to do one of the calculations. It verified that the shortcut gave the same result as the original calculation.
4. The compiler could now use that shortcut when building the working program. With the same settings as before, the program it produced took **1,269 cycles** and passed all nine benchmark tests.
5. I wanted to know whether that one shortcut explained the difference. I took the eight attempts away and gave the tool just the original program and the shortcut by hand. It built the exact same 1,269-cycle program.

<details>
<summary>What was the shortcut?</summary>

Workers 11 and 12 skipped a redundant check. The original code checked whether a number was zero, then used the answer to choose between two values. The instruction that makes the choice already handles zero, so the workers could use the number directly and swap the order of the two values. Skipping the check also let the tool move some later instructions earlier. [The check for this edit](results/zero_test.smt2)

</details>

## Try it

You'll need Python 3.10+ and Z3 (`brew install z3` on macOS or `sudo apt install z3` on Ubuntu). From the root of this repo, run the commands below to replay the experiment on the saved attempts. You don't need an API key.

```sh
git clone https://github.com/anthropics/original_performance_takehome.git benchmark
git -C benchmark checkout 5452f74bd977807ac2e74f3d29432b9df6f25197
python3 run_experiment.py  # replay the seed 52 example
```

You should see 1,981 cycles for the working program alone, 1,269 with the eight attempts, and 1,269 with just the shortcut added by hand. Each run tries the same 90 ways of arranging the instructions and checks the answers on eight fresh trees. To follow the code, start with `collect_expressions` in [run_experiment.py](run_experiment.py). The part that checks whether two calculations agree is in [prove_equivalence.py](compiler/prove_equivalence.py).

To run Anthropic’s own tests on the program you just built, copy it into the benchmark checkout and run:

```sh
cp output/seed52/failed_workers.json.gz benchmark/
cp benchmark_entry.py benchmark/perf_takehome.py
python3 benchmark/tests/submission_tests.py
git -C benchmark diff HEAD -- tests/ problem.py
```

You should see nine tests pass and an empty diff for the tests and simulator.
