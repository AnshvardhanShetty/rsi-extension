# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. One of the experiments was where they gave a few AI agents a working program and asked them to make it faster. The program follows paths through a tree of numbers. You can change how it does the calculation as long as you get the same answers. They measured how long it took in cycles. [Their write-up](https://rsi-top.github.io/) · [The original puzzle](https://github.com/anthropics/original_performance_takehome)

Thought it was interesting how they tested what to do when the agents got stuck. They took one search at the point where it stopped improving and let it continue two ways. In one, the agents kept trying as usual. In the other, four planner agents looked back at what had already been tried and suggested different things to try next. In the run they show, ordinary search finished at **1,244 cycles**. The version with the planners got to **1,109**. [Their results and code](https://github.com/RSI-top/rsi-top-wrapper)

I thought it was really cool but was curious as to whether the . What if an agent broke the program but also figured out a faster way to do one part of it? Could I keep that part?

## What I tried

I ran my own search on the same puzzle and saved the programs. Afterward I wrote a small compiler in Python. It looks for pieces of a failed program that could replace a step in the working one. It checks that the two pieces give the same answer, then tries building the working program with the replacement.

In one run, a failed agent had written a simpler way to pick between two values. The working code asked “is this number zero?” and then picked A or B. The agent tested the number directly and swapped A and B. That saved a comparison and let my compiler load some tree values ahead of time. My compiler got **1,981 cycles** on its own and **1,269** with the failed attempts. I gave it just that one shortcut by hand and got the exact same program. It passed all nine original tests. [The shortcut](results/zero_test.smt2)

I tried a fresh run to see if I could find a second trick and give it to the next agent. Four programs got wrong answers. I tried pulling out their edits, but none made a working program faster. So the part I’ve seen work is recovering a shortcut after a run. I’m still curious whether it can help another agent *during* a run. [The edits I tried](results/seed54_edits.json)

There’s a related paper from the group called *AI as a Compiler*. They gave a model a program written in Triton and asked it to write the low-level instructions for an NVIDIA GPU. The connection for me is who comes up with a better set of instructions. In their paper the model writes them directly. Here the model came up with one useful shortcut inside a broken program, and my Python compiler checked it and built the final program for the simulator. [AI as a Compiler](https://arxiv.org/abs/2609.36800)

## Try it

You'll need Python 3.10+ and Z3 (`brew install z3` on macOS or `sudo apt install z3` on Ubuntu). These commands use the saved attempts, so you can run them without an API key.

```sh
git clone https://github.com/anthropics/original_performance_takehome.git benchmark
git -C benchmark checkout 5452f74bd977807ac2e74f3d29432b9df6f25197
python3 run_experiment.py            # first run (seed 52)
python3 run_experiment.py --seed 54  # fresh run, with the old shortcut already included
```

The first run should print 1,981, 1,269, and 1,269 cycles. The fresh run should print 1,269 twice. Each version gets the same 90 tries at arranging its instructions, and the tool checks every answer on eight fresh trees. [Experiment code](run_experiment.py)

To run Anthropic’s own tests on the program you just built, copy it into the benchmark checkout and run:

```sh
cp output/seed52/failed_workers.json.gz benchmark/
cp benchmark_entry.py benchmark/perf_takehome.py
python3 benchmark/tests/submission_tests.py
git -C benchmark diff HEAD -- tests/ problem.py
```

You should see nine tests pass and an empty diff for the tests and simulator.

Anshvardhan Shetty · Independent project, built with AI assistance.
