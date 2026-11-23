"""Propose equalities by execution fingerprint, then check bounded bit-vector identities with Z3."""

import shutil
import subprocess
from collections import defaultdict

BV = {
    "+": "bvadd",
    "-": "bvsub",
    "*": "bvmul",
    "^": "bvxor",
    "&": "bvand",
    "|": "bvor",
    "<<": "bvshl",
    ">>": "bvlshr",
    "%": "bvurem",
    "//": "bvudiv",
}


def hex_word(node):
    return f"#x{node:08x}"


class EquivalentExpressions:
    """Matching sample values suggest a pair. A proof lets both nodes share a group."""

    def __init__(self, graph):
        self.group_of_node = []
        self.recipes = []
        self.prover = subprocess.Popen(
            [shutil.which("z3"), "-in"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.send(
            "(set-option :timeout 50)\n(declare-fun mem ((_ BitVec 32)) (_ BitVec 32))"
        )
        self.declared = set()
        groups_by_samples = defaultdict(list)
        known_recipes = {}
        for i, node in enumerate(graph.nodes):
            operator_name = node[0]
            recipe = (
                node
                if operator_name in ("x", "c")
                else (operator_name, *(self.group_of_node[a] for a in node[1:]))
            )
            group_id = known_recipes.get(recipe)
            if group_id is None:
                for candidate in groups_by_samples[graph.values[i]]:
                    if self.prove(recipe, candidate):
                        group_id = candidate
                        break
                if group_id is None:
                    group_id = len(self.recipes)
                    self.recipes.append(recipe)
                    groups_by_samples[graph.values[i]].append(group_id)
                known_recipes[recipe] = group_id
            self.group_of_node.append(group_id)
        self.prover.stdin.close()
        self.prover.wait(timeout=5)

    def send(self, command):
        self.prover.stdin.write(command + "\n")
        self.prover.stdin.flush()

    def prove(self, candidate, previous_group):
        def dependencies(node, depth):
            if depth == 0 or node[0] in ("c", "x"):
                return set()
            result = set(node[1:])
            for child_id in node[1:]:
                result.update(dependencies(self.recipes[child_id], depth - 1))
            return result

        previous = self.recipes[previous_group]
        common = dependencies(candidate, 3) & (
            dependencies(previous, 3) | {previous_group}
        )
        variables = set()

        def variable(i):
            variables.add(i)
            return "v" + str(i)

        def solver_expression(node, depth):
            operation = node[0]
            if operation == "x":
                return variable(0)
            if operation == "c":
                return hex_word(node[1])
            args = [
                variable(i + 1)
                if self.recipes[i][0] not in ("x", "c") and (depth == 0 or i in common)
                else solver_expression(self.recipes[i], depth - 1)
                for i in node[1:]
            ]
            if operation == "sel":
                return f"(ite (= {args[0]} {hex_word(0)}) {args[2]} {args[1]})"
            if operation in ("<", "=="):
                return f"(ite ({'bvult' if operation == '<' else '='} {args[0]} {args[1]}) {hex_word(1)} {hex_word(0)})"
            if operation == "fma":
                return f"(bvadd (bvmul {args[0]} {args[1]}) {args[2]})"
            return (
                "("
                + ("mem" if operation == "mem" else BV[operation])
                + " "
                + " ".join(args)
                + ")"
            )

        a = solver_expression(candidate, 3)
        b = (
            variable(previous_group + 1)
            if previous_group in common and previous[0] not in ("c", "x")
            else solver_expression(previous, 3)
        )
        if a == b:
            return True
        declarations = "\n".join(
            f"(declare-const v{i} (_ BitVec 32))" for i in variables - self.declared
        )
        self.declared |= variables
        self.send(
            declarations
            + "\n(push)\n(assert (distinct "
            + a
            + " "
            + b
            + "))\n(check-sat)\n(pop)"
        )
        result = self.prover.stdout.readline().strip()
        assert result in ("sat", "unsat", "unknown"), result
        return result == "unsat"


def choose_expressions(graph, groups, available_nodes, output_node):
    """Pick the cheapest way to compute each value needed by the starter output."""
    choices = defaultdict(set)
    pending = list(available_nodes) + [output_node]
    visited = set()
    while pending:
        i = pending.pop()
        if i in visited:
            continue
        visited.add(i)
        node = graph.nodes[i]
        group_id = groups.group_of_node[i]
        if node[0] in ("x", "c"):
            choices[group_id].add(node)
            continue
        pending.extend(node[1:])
        recipe = (node[0], *(groups.group_of_node[a] for a in node[1:]))
        if group_id not in recipe[1:]:
            choices[group_id].add(recipe)
    cost = {}
    best = {}
    for iteration in range(75):
        changed = False
        for group_id, recipes in sorted(choices.items()):
            for recipe in sorted(recipes):
                args = () if recipe[0] in ("c", "x") else recipe[1:]
                if any(i not in cost for i in args):
                    continue
                # Path-weighted local cost keeps the long recurrent hash from dominating numerically.
                recipe_cost = (
                    (0 if recipe[0] in ("c", "x") else 8 if recipe[0] == "mem" else 1)
                    + max((cost[i] for i in args), default=0)
                    + sum(cost[i] for i in set(args)) * 0.001
                )
                if group_id not in cost or (recipe_cost, recipe) < (
                    cost[group_id],
                    best[group_id],
                ):
                    cost[group_id] = recipe_cost
                    best[group_id] = recipe
                    changed = True
        if not changed:
            break
    return groups.group_of_node[output_node], best
