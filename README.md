# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. One of their experiments used a coding task from Anthropic. Anthropic gives you a working Python function that writes instructions for a simulated processor. The processor runs those instructions on a tree of numbers. The challenge is to change the function so it produces the same answers in fewer cycles. [Anthropic’s task](https://github.com/anthropics/original_performance_takehome)

The group used AI agents to edit that Python function and test each version. When progress stalled, four planner agents looked back through earlier attempts and suggested edits for the workers to try next. In the run they describe, ordinary search got to 1,244 cycles. With the planners it got to 1,109. [Their write-up](https://rsi-top.github.io/) · [Their code](https://github.com/RSI-top/rsi-top-wrapper)

I wondered about the versions that failed the tests. An agent might have found a quicker way to do one calculation and made a mistake somewhere else. Could I take just the part it got right?

## What I tried

I ran RSI-top’s ordinary search on the same task. On seed 52, the agents’ fastest correct program took **4,007 cycles**. I also saved five attempts from that run that finished but gave wrong answers.

### What does the compiler do on its own?

I wanted to be able to take one good idea from a wrong program and try it in a working one. For that, I wrote a small compiler in Python. I give it the instructions from Anthropic’s original working program. It follows the calculations that produce the answer and writes a new set of instructions to do them.

Even with just the original program, it has a few ways to save time. For example, if the code multiplies two numbers and then adds a third, the processor has one instruction that can do both. I wrote a rule so the compiler can use it. The compiler also works out which calculations have to wait for others. If an addition needs a number from memory, it has to wait for that number. An addition using numbers that are already available can run in the same cycle as the load. [Arithmetic rules](compiler/rewrite_rules.py) · [How the compiler schedules instructions](compiler/schedule_instructions.py)

I first ran the compiler with **only the original working program**. It tried 90 combinations of settings for how to load values and arrange the work. The fastest correct program it built took **1,981 cycles**. That gave me something to compare against. How much faster could the same compiler get if it could also borrow an idea from an agent?

### What did the failed attempts add?

I gave the compiler the same working program and the same 90 settings, plus the five failed attempts. Workers 11 and 12 had each found a shorter way to choose between two values. The original used one instruction to ask “is this number zero?” and another to make the choice. The choice instruction already handles zero, so the workers could give it the number directly and swap the order of the two values.

The compiler checked that both versions always picked the same value, then used the shorter version when it rebuilt the program. That also let it load some values earlier. The result took **1,269 cycles** and passed all nine benchmark tests. As a check, I gave the compiler just that one rule by hand. It produced the exact same program. These were local runs on saved code after the agents had finished. [The check for this edit](results/zero_test.smt2)

### Did it help the next agent?

I went back to the point just after worker 11 failed and gave ordinary RSI-top four more attempts. In a second copy of the same search, I gave the workers four attempts and a note explaining the verified shortcut. Both started with a best program of 10,828 cycles. On their third try, both found the same fix for a different bug and produced the same **2,521-cycle** program. That was the best either branch got. The shortcut helped my compiler on this run. Telling the agents about it didn’t improve their final score.

## Try it

You'll need Python 3.10+ and Z3 (`brew install z3` on macOS or `sudo apt install z3` on Ubuntu). From the root of this repo, run the commands below to replay the experiment on the saved attempts. You don't need an API key.

```sh
git clone https://github.com/anthropics/original_performance_takehome.git benchmark
git -C benchmark checkout 5452f74bd977807ac2e74f3d29432b9df6f25197
python3 run_experiment.py --compare-search
```

This checks the saved 4,007-cycle program on eight fresh trees, rebuilds the 1,269-cycle program from the five ordinary-search attempts, and checks it on the same trees. [Experiment code](run_experiment.py) · [Saved inputs](data/README.md)

To reproduce the 1,981-cycle run and the check with the handwritten rule, run `python3 run_experiment.py`. That command also tries all eight saved attempts from the two search branches.

To run Anthropic’s own tests on the program you just built, copy it into the benchmark checkout and run:

```sh
cp output/seed52/failed_workers.json.gz benchmark/
cp benchmark_entry.py benchmark/perf_takehome.py
python3 benchmark/tests/submission_tests.py
git -C benchmark diff HEAD -- tests/ problem.py
```

You should see nine tests pass and an empty diff for the tests and simulator.
