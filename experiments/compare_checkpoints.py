"""Compare the last verified score after eight model replies on each branch."""

import json
from pathlib import Path

results = Path(__file__).resolve().parents[1] / "results/paired_checkpoints.json"


def verified_cycles(program):
    checks = program["verification"]
    cycles = program["cycles"]
    if (
        not checks["valid"]
        or checks["cycles"] != cycles
        or checks["official"] != [cycles] * 8
    ):
        raise ValueError("The simulator checks disagree for this program.")
    return cycles


def main():
    checkpoints = json.loads(results.read_text())["seeds"]
    print("seed  start  ordinary  feedback  cycles saved by feedback")
    for seed, checkpoint in checkpoints.items():
        start = verified_cycles(checkpoint["shared_best"])
        scores = {}
        for name, branch in checkpoint["arms"].items():
            if not branch["complete"] or (
                branch["slots"],
                branch["calls"],
                branch["receipts"],
            ) != (8, 8, 8):
                raise ValueError(f"Seed {seed}: {name} did not finish eight proposals.")
            scores[name] = min(start, verified_cycles(branch["best"]))
        ordinary = scores["native"]
        feedback = scores["handoff"]
        print(f"{seed:>4} {start:6} {ordinary:8} {feedback:9} {ordinary - feedback:+9}")


if __name__ == "__main__":
    main()
