# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. They had AI agents try to speed up a working program. In one experiment, four agents looked back through earlier attempts and suggested what to try next. Continuing the search as usual got them to 1,244 cycles. With those suggestions, they got to 1,109. Fewer cycles means the program ran faster. [Their write-up](https://rsi-top.github.io/) · [Their code](https://github.com/RSI-top/rsi-top-wrapper)

That got me wondering about the attempts that gave a wrong answer. An agent might speed up one part of a program and break something else. Could I keep the good edit?

## What I tried

I ran RSI-top on the same coding task and saved eight programs that gave wrong answers. I wrote a Python tool to look through them for shorter ways to do parts of the working program. Before borrowing a piece, the tool checked that it would give the same answer as the original piece for every possible input. [Anthropic’s coding task](https://github.com/anthropics/original_performance_takehome) · [The eight saved attempts](data/README.md)

Two of the eight programs had the same useful edit. Workers 11 and 12 had each found a way to make a choice in one instruction where the working program used two. I ran my tool twice to see how much that mattered.

| What I gave the tool | Best time |
| --- | ---: |
| The working program alone | 1,981 cycles |
| The working program and the eight wrong attempts | 1,269 cycles |

The 1,269-cycle program passed all nine tests. To check whether that one edit explained the difference, I gave the tool just the working program and the shortcut by hand. It built the exact same program.

<details>
<summary>What was the shortcut?</summary>

The program needed to choose A for zero and B for any other number. The original code first checked whether its input was zero, then used the answer to choose A or B. The processor in this coding task can already choose between two values based on whether a number is zero. The workers used that instruction directly. With B as its first choice and A as its second, it picks A for zero and B for everything else. Skipping the separate check also let the tool move some later instructions earlier. [The check for this edit](results/zero_test.smt2)

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

## Further directions

In a separate offline replay, I passed worker 11’s exact edit to the next attempt. It sped up the program it was applied to, but the search already had a faster one. The question I’d try next is whether I can find an edit that helps the best program the agents have so far.

Anshvardhan Shetty
