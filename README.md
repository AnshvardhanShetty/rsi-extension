# RSI extension

I read the RSI-top write-up from Azalia Mirhoseini’s group. One of their experiments was to give a few AI agents a working program and see how fast they could make it. When they got stuck, four other agents went back through what they’d tried and suggested a few things to do next. In the run they show, letting the search carry on as usual got them to 1,244 cycles. Going back through the attempts got them to 1,109. Fewer cycles means the program ran faster. [Their write-up](https://rsi-top.github.io/) · [Their code](https://github.com/RSI-top/rsi-top-wrapper)

I thought the part about going back through old attempts was interesting. I wondered what the planners could learn from a program that ran and gave the wrong answer. Suppose an agent makes two edits. It figures out how to do a calculation in two instructions instead of five. A few lines later, it reads the wrong value. The final answer is wrong, so I can’t use that version as it stands. But I’d still want those first two instructions if they really did the same job as the original five.

Could I take just those two instructions, put them in the working program, and see if it gave the right answer faster?

## What I tried

I ran my own copy of RSI-top on Anthropic’s performance take-home, the coding task the group used in their write-up. The starter program walks through a tree of numbers, updating a value at each step. The agents had to make it produce the same answers in fewer cycles on a simulated processor. I saved eight of their attempts that ran but gave the wrong answers. Then I wrote a Python tool to compare each attempt with the working program, one calculation at a time. If two calculations gave the same answer on a few examples, the tool asked Z3 a follow-up question. Could *any* input make these two calculations disagree? If Z3 proved they always agreed, the tool could use the agent’s calculation in the working program. [Anthropic’s task](https://github.com/anthropics/original_performance_takehome)

Here’s one shortcut it found. The working program needed to pick A when a number was zero and B otherwise. It used one instruction to ask “is this zero?” and another to pick A or B. One agent spotted that the machine’s pick instruction already treats zero as false. It fed the number straight into that instruction, with B as the choice for nonzero and A as the choice for zero. Same answer, one less instruction. [The check for this shortcut](results/zero_test.smt2)

Did that help the whole program? I gave my tool the same 90 tries to arrange the instructions each time. With only the working program to draw from, its best version took **1,981 cycles**. When it could also borrow from the eight wrong attempts, it found a version that took **1,269 cycles** and passed all nine tests. The shortcut also let the tool move some loads earlier, so the gain was bigger than just skipping a single check. To see how much the shortcut explained, I ran the tool once more with just the working program and that one rule. It produced the exact same 1,269-cycle program.

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
