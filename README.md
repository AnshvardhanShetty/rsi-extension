# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. One of their experiments used a coding task from Anthropic. Anthropic gives you a working Python function that writes instructions for a simulated processor. The processor runs those instructions on a tree of numbers. The challenge is to change the function so it produces the same answers in fewer cycles. [Anthropic’s task](https://github.com/anthropics/original_performance_takehome)

The group used AI agents to edit that Python function and test each version. When progress stalled, four planner agents looked back through earlier attempts and suggested edits for the workers to try next. In the run they describe, ordinary search got to 1,244 cycles. With the planners it got to 1,109. [Their write-up](https://rsi-top.github.io/) · [Their code](https://github.com/RSI-top/rsi-top-wrapper)

I wondered about the versions that failed the tests. An agent might have found a quicker way to do one calculation and made a mistake somewhere else. Could I take just the part it got right?

## What I tried

1. I ran the ordinary OpenEvolve search from RSI-top on Anthropic’s task. On seed 52, its fastest correct program came from worker 9. I saved that program and five attempts from the same search that gave wrong answers.
2. After the search finished, I ran my Python tool on the original working code and those five attempts. Workers 11 and 12 had a shortcut that computed the same value in fewer instructions. The tool verified the shortcut and used it to build a new program.

| Seed 52, same agent attempts | Best verified time |
| --- | ---: |
| RSI-top ordinary search | 4,007 cycles |
| Same search + offline recovery from its failed attempts | 1,269 cycles |

That’s about **68% fewer cycles** on this run. The recovery step used extra local computation and made no further model calls. The resulting program passed all nine benchmark tests.

<details>
<summary>What was the shortcut?</summary>

Workers 11 and 12 skipped a redundant check. The original code checked whether a number was zero, then used the answer to choose between two values. The instruction that makes the choice already handles zero, so the workers could use the number directly and swap the order of the two values. Skipping the check also let the tool move some later instructions earlier. [The check for this edit](results/zero_test.smt2)

</details>

## Try it

You'll need Python 3.10+ and Z3 (`brew install z3` on macOS or `sudo apt install z3` on Ubuntu). From the root of this repo, run the commands below to replay the experiment on the saved attempts. You don't need an API key.

```sh
git clone https://github.com/anthropics/original_performance_takehome.git benchmark
git -C benchmark checkout 5452f74bd977807ac2e74f3d29432b9df6f25197
python3 run_experiment.py --compare-search
```

This checks the saved 4,007-cycle program on eight fresh trees, rebuilds the 1,269-cycle program from the five ordinary-search attempts, and checks it on the same trees. [Experiment code](run_experiment.py) · [Saved inputs](data/README.md)

<details>
<summary>How much did borrowing the shortcut help?</summary>

The tool also has its own compiler optimizations. With the original working code alone, it reached 1,981 cycles. Giving it just the recovered shortcut by hand reproduced the same 1,269-cycle program. Run `python3 run_experiment.py` for the original checks, including the replay with all eight saved attempts from the two branches.

</details>

To run Anthropic’s own tests on the program you just built, copy it into the benchmark checkout and run:

```sh
cp output/seed52/failed_workers.json.gz benchmark/
cp benchmark_entry.py benchmark/perf_takehome.py
python3 benchmark/tests/submission_tests.py
git -C benchmark diff HEAD -- tests/ problem.py
```

You should see nine tests pass and an empty diff for the tests and simulator.
