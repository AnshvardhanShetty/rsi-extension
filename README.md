# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. One of the experiments was where they gave a few AI agents a working program and asked them to make it faster. The program follows paths through a tree of numbers. You can change how it does the calculation as long as you get the same answers. They measured how long it took in cycles. [Their write-up](https://rsi-top.github.io/) · [The original puzzle](https://github.com/anthropics/original_performance_takehome)

Thought it was interesting how they tested what to do when the agents got stuck. They took one search at the point where it stopped improving and let it continue two ways. In one, the agents kept trying as usual. In the other, four planner agents looked back at what had already been tried and suggested different things to try next. In the run they show, ordinary search finished at **1,244 cycles**. The version with the planners got to **1,109**. [Their results and code](https://github.com/RSI-top/rsi-top-wrapper)

The compiler idea came from another paper I read from the group, [AI as a Compiler](https://arxiv.org/abs/2609.36800). They gave a model code written in Triton and asked it to write the instructions an NVIDIA GPU would run. On some tasks the model found a faster way to do the calculation than Triton’s own compiler did.

That made me wonder about the RSI-top runs. Say an agent changes two things. One change saves a few instructions, the other introduces a bug, and the program runs but gives the wrong answer. Could a compiler pick out the part worth keeping? That’s what I wanted to try.

## What I tried

I ran my own search on the same puzzle and saved the programs. Afterward I wrote a small compiler in Python. I gave it a known working program and eight versions written by agents. All eight ran, but each returned a wrong value on at least one test. The compiler looked inside them for a shorter way to do a step in the working program. Before using a shortcut, it checked that the two ways of doing that step gave the same value.

One of those eight programs had a simpler way to pick between two values. The working code asked “is this number zero?” and then picked A or B. The agent tested the number directly and swapped A and B. That saved a comparison and let my compiler load some tree values ahead of time. Starting with the working program alone, my compiler built a version that took **1,981 cycles**. When it could also use code from those eight programs, it built one that took **1,269**. I gave it just that one shortcut by hand and got the exact same program. It passed all nine original tests. [The shortcut](results/zero_test.smt2)

I tried a fresh run to see if I could find a second trick and give it to the next agent. Four of the new programs ran and returned wrong answers. I tried pulling out their edits, but none made a working program faster. So the part I’ve seen work is recovering a shortcut after a run. I’m still curious whether it can help another agent *during* a run. [The edits I tried](results/seed54_edits.json)

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
