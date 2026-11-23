# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. They had AI agents try to speed up a working program. In one experiment, four agents looked back through earlier attempts and suggested what to try next. Continuing the search as usual got them to 1,244 cycles. With those suggestions, they got to 1,109. Fewer cycles means the program ran faster. [Their write-up](https://rsi-top.github.io/) · [Their code](https://github.com/RSI-top/rsi-top-wrapper)

That got me wondering about the attempts that gave a wrong answer. An agent might speed up one part of a program and break something else. Could I keep the good edit?

## What I tried

1. I gave the RSI-top agents a program that already worked and asked them to speed it up. I kept eight versions that ran but gave wrong answers. [The original program](https://github.com/anthropics/original_performance_takehome) · [The eight attempts](data/README.md)
2. First I wanted to know how fast my tool could make the program on its own. I gave it only the original code. The version it built finished the task in **1,981 cycles** on the simulator. That was the time to beat.
3. I ran the tool again, this time letting it look through the eight attempts for shorter ways to do individual calculations. Workers 11 and 12 had each used one instruction where the original used two. The tool verified that their shortcut gave the same result for that calculation.
4. I gave the tool the same settings as before. With the shortcut available, it built a program that finished in **1,269 cycles** and passed all nine benchmark tests.
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
