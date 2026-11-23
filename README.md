# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. One of their experiments was to give a few AI agents a working program and see how fast they could make it. When they got stuck, four other agents went back through what they’d tried and suggested a few things to do next. In the run they show, letting the search carry on as usual got them to 1,244 cycles. Going back through the attempts got them to 1,109. Fewer cycles means the program ran faster. [Their write-up](https://rsi-top.github.io/) · [Their code](https://github.com/RSI-top/rsi-top-wrapper)

I thought the part about going back through old attempts was interesting. I wondered what the planners could learn from a program that ran and gave the wrong answer. Suppose an agent makes two edits. It figures out how to do a calculation in two instructions instead of five. A few lines later, it reads the wrong value. The final answer is wrong, so I can’t use that version as it stands. But I’d still want those first two instructions if they really did the same job as the original five.

Could I take just those two instructions, put them in the working program, and see if it gave the right answer faster?

## What I tried

I ran my own search on the same puzzle and saved eight programs that ran but gave wrong answers. After the run, I wrote a compiler in Python to look for shortcuts in those programs. It ran the calculations on a few sample inputs to find possible matches, then used Z3 to check that a shortcut held for every 32-bit input to that step. [The puzzle](https://github.com/anthropics/original_performance_takehome)

One agent had found a shorter way to choose between two values. The original checked whether a number was zero and then picked A or B. The agent used the number itself and flipped the order of A and B. Same choice either way. That little change also let my compiler load some values ahead of time. With just the working code it got 1,981 cycles. With the eight programs to look through it got 1,269 and passed all nine tests. I tried adding just the A/B trick by hand and got the exact same program back. [The shortcut](results/zero_test.smt2)

## Try it

You'll need Python 3.10+ and Z3 (`brew install z3` on macOS or `sudo apt install z3` on Ubuntu). These commands use the saved attempts, so you can run them without an API key.

```sh
git clone https://github.com/anthropics/original_performance_takehome.git benchmark
git -C benchmark checkout 5452f74bd977807ac2e74f3d29432b9df6f25197
python3 run_experiment.py  # replay the seed 52 example
```

You should see 1,981 cycles with the working code alone, 1,269 with the saved attempts, and 1,269 with the A/B shortcut added by hand. Each version gets the same 90 tries at arranging its instructions, and the tool checks every answer on eight fresh trees. [Experiment code](run_experiment.py)

To run Anthropic’s own tests on the program you just built, copy it into the benchmark checkout and run:

```sh
cp output/seed52/failed_workers.json.gz benchmark/
cp benchmark_entry.py benchmark/perf_takehome.py
python3 benchmark/tests/submission_tests.py
git -C benchmark diff HEAD -- tests/ problem.py
```

You should see nine tests pass and an empty diff for the tests and simulator.

## Further directions

What I’d like to know next is whether another agent can build on a shortcut like this. I’d split a search in two at the same point. On one side, RSI-top would keep going as usual. On the other, the next agent would get the working program with the shortcut already in it. I’d give both sides the same number of attempts and see which one finishes with the fastest program that passes the tests.

Anshvardhan Shetty · Independent project, built with AI assistance.
