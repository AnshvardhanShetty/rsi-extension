"""Look for useful shortcuts in saved programs that ran but returned wrong answers."""

import argparse
from functools import partial
import gzip
import hashlib
from itertools import product
import json
from pathlib import Path
import random
import shutil
import sys

from compiler.read_instructions import ExpressionGraph
from compiler.rewrite_rules import arithmetic_rewrites, remove_zero_test
from compiler.prove_equivalence import EquivalentExpressions, choose_expressions
from compiler.simplify_lookups import simplify_lookups
from compiler.schedule_instructions import schedule_instructions

DATA = Path(__file__).resolve().parent / "data"
SIMULATOR_SHA256 = "fadb0f0858e2259f5759077a5544b9906dad3ceee80d37b4f0aa77da730c93c9"
# Both recorded runs used 256 input values, processed eight at a time.
BATCH_SIZE = 256


def make_input(simulator, seed):
    random.seed(seed)
    tree = simulator.Tree.generate(10)
    values = simulator.Input.generate(tree, BATCH_SIZE, 16)
    return simulator.build_mem_image(tree, values)


def read_instructions(path):
    with gzip.open(path, "rt") as stream:
        return json.load(stream)


def collect_expressions(simulator, folder, workers, known_rule):
    """Use the starter for the correct answer and look for shortcuts in the workers' code."""
    graph = ExpressionGraph(partial(make_input, simulator))
    output, starter_nodes = graph.read_program(
        read_instructions(folder / "starter.json.gz")
    )
    if output < 0:
        raise ValueError("Cannot trace the starter's output.")
    allowed = set(starter_nodes)
    for path in workers:
        _, worker_nodes = graph.read_program(read_instructions(path))
        allowed.update(worker_nodes)
    allowed.update(arithmetic_rewrites(graph, starter_nodes))
    if known_rule:
        allowed.update(remove_zero_test(graph, starter_nodes))
    groups = EquivalentExpressions(graph)
    output, expressions = choose_expressions(graph, groups, allowed, output)
    return graph, output, expressions


def find_fastest_schedule(graph, output, expressions):
    """Try 90 settings and keep the shortest program that fits in the available registers."""
    best_program = None
    for table_size in (2, 4, 8):
        root, lowered = simplify_lookups(
            output,
            expressions,
            table_size,
            graph.tree_start,
            graph.index_start,
            boolean_math=True,
        )
        for blocks_per_tile, stagger, load_weight in product(
            (16, 24, 32), (0, 1, 3, 6, 10), (1, 4)
        ):
            try:
                program = schedule_instructions(
                    root,
                    lowered,
                    graph.value_start,
                    blocks_per_tile,
                    load_weight=load_weight,
                    block_stagger=stagger,
                )
            except ValueError as error:
                if str(error) != "scratch":
                    raise
                continue
            if best_program is None or len(program) < len(best_program):
                best_program = program
    if best_program is None:
        raise ValueError("No schedule fits the simulator's scratch registers.")
    return best_program


def verify_program(simulator, program, first_seed):
    """Compare every output word to the reference on eight new trees."""
    for seed in range(first_seed, first_seed + 8):
        memory = make_input(simulator, seed)
        machine = simulator.Machine(memory, program, simulator.DebugInfo({}))
        machine.enable_pause = machine.enable_debug = False
        machine.run()
        # Run past each pause so memory holds the final answer.
        for _ in simulator.reference_kernel2(memory):
            pass
        start = memory[6]
        end = start + BATCH_SIZE
        if machine.mem[start:end] != memory[start:end] or machine.cycle != len(program):
            raise ValueError(f"Verification failed on tree {seed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=(52, 54), default=52)
    parser.add_argument("--benchmark", type=Path, default=Path("benchmark"))
    parser.add_argument("--compare-search", action="store_true", help="Replay the ordinary seed-52 search result and the offline extension.")
    args = parser.parse_args()
    if args.compare_search and args.seed != 52:
        parser.error("--compare-search uses the saved seed-52 search")
    simulator_path = args.benchmark / "tests/frozen_problem.py"
    if (
        not simulator_path.is_file()
        or hashlib.sha256(simulator_path.read_bytes()).hexdigest() != SIMULATOR_SHA256
    ):
        parser.error("Use the benchmark commit in the README.")
    if not shutil.which("z3"):
        parser.error("Install the z3 executable and make sure it is on PATH.")
    sys.path.insert(0, str(simulator_path.parent.resolve()))
    import frozen_problem as simulator

    folder = DATA / f"seed{args.seed}"
    pattern = "native_*.json.gz" if args.compare_search else "*.json.gz"
    workers = sorted(path for path in folder.glob(pattern) if path.name != "starter.json.gz")
    expected_workers = {52: 8, 54: 4}[args.seed]
    if args.compare_search:
        expected_workers = 5
    if len(workers) != expected_workers:
        raise ValueError(
            f"Expected {expected_workers} programs that returned wrong answers in {folder}"
        )

    if args.compare_search:
        first_tree = 410032
        ordinary = read_instructions(DATA / "seed52_search_best.json.gz")
        verify_program(simulator, ordinary, first_tree)
        print(f"Ordinary search: {len(ordinary):,} cycles (saved program, 8 trees passed)", flush=True)
        cases = [("failed_workers", "Same search + offline recovery", workers, False)]
    elif args.seed == 52:
        cases = [
            ("baseline", "baseline", [], False),
            (
                "failed_workers",
                "with code from programs that gave wrong answers",
                workers,
                False,
            ),
            ("known_rule", "known rule", [], True),
        ]
        first_tree = 410032
    else:
        cases = [
            ("known_rule", "known rule", [], True),
            (
                "known_rule_and_failed_workers",
                "known rule + code from programs that gave wrong answers",
                workers,
                True,
            ),
        ]
        first_tree = 542001

    # Save each program for the benchmark tests.
    output_folder = Path("output") / f"seed{args.seed}"
    output_folder.mkdir(parents=True, exist_ok=True)
    for filename, label, donors, add_rule in cases:
        graph, root, expressions = collect_expressions(
            simulator, folder, donors, add_rule
        )
        program = find_fastest_schedule(graph, root, expressions)
        verify_program(simulator, program, first_tree)
        with gzip.open(output_folder / f"{filename}.json.gz", "wt") as stream:
            json.dump(program, stream, sort_keys=True)
        print(f"{label:55s} {len(program):5d} cycles   8 trees passed", flush=True)


if __name__ == "__main__":
    main()
