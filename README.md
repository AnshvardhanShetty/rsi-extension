# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. One of their experiments was to give a few AI agents a working program and see how fast they could make it. When they got stuck, four other agents went back through what they’d tried and suggested a few things to do next. In the run they show, letting the search carry on as usual got them to 1,244 cycles. Going back through the attempts got them to 1,109. Fewer cycles means the program ran faster. [Their write-up](https://rsi-top.github.io/) · [Their code](https://github.com/RSI-top/rsi-top-wrapper)

I thought the part about looking through old attempts was interesting. When looking through things the agents tried there may have been programs that failed but still had things that worked faster or were useful. For example, say an agent figures out how to do something in two instructions instead of five, but somewhere else it introduces a bug. So, when you run the test and the whole thing fails. How would you find the two instruction and put them back in the working version?

I also read *AI as a Compiler* from the same group. They took code written in Triton and asked a model to write the instructions for an NVIDIA GPU. On some programs the model came up with a faster way to do it than the Triton compiler did. 



## What I tried

I ran my own search on the same puzzle and saved eight programs that gave wrong answers. Once the run was over, I gave those eight and the original working program to a compiler I wrote in Python. It looked for places where an agent had done the same calculation a different way, then checked whether the two versions would agree for every input to that step. [The puzzle](https://github.com/anthropics/original_performance_takehome)

One agent had found a shorter way to choose between two values. The original checked whether a number was zero and then picked A or B. The agent used the number itself and flipped the order of A and B. Same choice either way. That little change also let my compiler load some values ahead of time. With just the working code it got 1,981 cycles. With the eight programs to look through it got 1,269 and passed all nine tests. I tried adding just the A/B trick by hand and got the exact same program back. [The shortcut](results/zero_test.smt2)

I tried it again on a fresh run because I wanted to see if I could give a shortcut like that to the next agent. This time I had four programs that gave wrong answers. None of the edits I pulled out made the working program faster, so I didn’t have anything to pass along. [The edits I tried](results/seed54_edits.json)

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
