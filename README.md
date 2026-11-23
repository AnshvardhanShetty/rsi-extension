# RSI extension

I read the RSI-top write-up because I was curious about what happens when AI coding agents get stuck. In one of their experiments, several agents try to make the same program faster. Each agent writes a version, runs it, and gets a score. When the scores stop improving, four other agents look back through the attempts and suggest things to try next. [Their write-up](https://rsi-top.github.io/) · [Their code](https://github.com/RSI-top/rsi-top-wrapper)

That got me wondering about the attempts that gave the wrong answer. A program can be broken in one place and still do something clever somewhere else. Could I take just that piece and use it in a working program?

## What I tried

I used the same puzzle they did. Imagine a tree with a number at every fork. The program walks through the tree, updating a running number at each fork and using that number to decide which way to go next. The goal is to get the same final numbers in fewer ticks of a simulated computer. Those ticks are the “cycles” in the results below. [Anthropic’s original challenge](https://github.com/anthropics/original_performance_takehome)

I ran a version of their search and saved the agents’ attempts. After the run, I wrote a Python tool to compare pieces of the broken programs with pieces of a working one. When two pieces seemed to do the same thing, the tool checked whether they would agree for every possible input to that step. Then I tried building the working program with the shortcut.

On one run, an agent got the overall answer wrong but had a simpler way to make a decision. The working code checked whether a number was zero and then picked one of two values. The agent used the number directly and swapped the two choices. Same result, one less check. That also let my tool load some of the tree values ahead of time.

My tool took **1,981 cycles** with the working code alone and **1,269 cycles** when it could use the failed attempts. The faster version passed all nine original tests. I also tried giving the tool just that one rule by hand. It built the exact same program.

I wanted to see if I could find a *different* shortcut on a fresh run and give it to the next agent. Four agents wrote programs that ran but gave wrong answers. I couldn't recover a second shortcut that made a working program faster, so I stopped before handing anything over. That's where this stands: I've seen a failed attempt help once, after the run. Whether it can help the next agent while the search is still going is the part I'd like to figure out.

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
