"""Replace a load from a small range of tree addresses with a choice among preloaded values."""

from .read_instructions import WORD_MASK, OPERATIONS


class BoundedExpressions:
    def __init__(self, boolean_math=False):
        self.boolean_math = boolean_math
        self.nodes = []
        self.index = {}
        self.bounds = []

    def add_expression(self, operation, *args):
        key = (operation, *args)
        if key in self.index:
            return self.index[key]
        result = self.infer_bounds(operation, args)
        if isinstance(result, int):
            return result
        node_id = len(self.nodes)
        self.nodes.append(key)
        self.index[key] = node_id
        self.bounds.append(result)
        return node_id

    def constant(self, x):
        return self.add_expression("c", x & WORD_MASK)

    def infer_bounds(self, operation, operands):
        if operation == "c":
            return operands[0], operands[0]
        if operation in ("x", "mem"):
            return 0, WORD_MASK
        low, high = zip(*(self.bounds[node_id] for node_id in operands))
        if low == high:
            return self.constant(int(OPERATIONS[operation](*low)) & WORD_MASK)

        def unsigned_range(lowest, highest):
            return (
                (lowest, highest)
                if 0 <= lowest <= highest <= WORD_MASK
                else (0, WORD_MASK)
            )

        if operation == "sel":
            if high[0] == 0:
                return operands[2]
            if low[0] > 0:
                return operands[1]
            if operands[1] == operands[2]:
                return operands[1]
            if self.boolean_math and high[0] <= 1 and low[1:] == high[1:]:
                return self.add_expression(
                    "fma",
                    operands[0],
                    self.constant(low[1] - low[2]),
                    self.constant(low[2]),
                )
            return min(low[1:]), max(high[1:])
        if operation == "<":
            if high[0] < low[1]:
                return self.constant(1)
            if low[0] >= high[1]:
                return self.constant(0)
            return 0, 1
        if operation == "==":
            if operands[0] == operands[1]:
                return self.constant(1)
            if high[0] < low[1] or high[1] < low[0]:
                return self.constant(0)
            return 0, 1
        if operation == "+":
            for node_id in (0, 1):
                if high[node_id] == 0:
                    return operands[1 - node_id]
            return unsigned_range(sum(low), sum(high))
        if operation == "-":
            return unsigned_range(low[0] - high[1], high[0] - low[1])
        if operation == "*" or operation == "fma":
            for node_id in (0, 1):
                if high[node_id] == 0:
                    return self.constant(0) if operation == "*" else operands[2]
                if low[node_id] == high[node_id] == 1:
                    return (
                        operands[1 - node_id]
                        if operation == "*"
                        else self.add_expression(
                            "+", operands[1 - node_id], operands[2]
                        )
                    )
            return unsigned_range(
                low[0] * low[1] + (low[2] if operation == "fma" else 0),
                high[0] * high[1] + (high[2] if operation == "fma" else 0),
            )
        if operation == "&":
            return 0, min(high)
        if operation == "%":
            return 0, min(high[0], high[1] - 1) if low[1] >= 1 else WORD_MASK
        if operation == ">>":
            return low[0] >> min(high[1], 32), high[0] >> min(low[1], 32)
        if operation == "<<" and high[1] < 32:
            return unsigned_range(low[0] << low[1], high[0] << high[1])
        return 0, WORD_MASK

    def lookup_small_table(self, address, lowest, highest):
        size = highest - lowest + 1
        # Slot i holds the address whose low bits are i. For addresses 7..10
        # that gives [8, 9, 10, 7], so two bit tests select the right value.
        values = []
        for slot in range(size):
            table_address = lowest + (slot - lowest) % size
            values.append(self.add_expression("mem", self.constant(table_address)))
        bit = 1
        while len(values) > 1:
            condition = self.add_expression("&", address, self.constant(bit))
            values = [
                self.add_expression(
                    "sel", condition, values[node_id + 1], values[node_id]
                )
                for node_id in range(0, len(values), 2)
            ]
            bit *= 2
        return values[0]


def simplify_lookups(
    root, recipes, table_limit, tree_start, tree_end, boolean_math=False
):
    builder = BoundedExpressions(boolean_math)
    memo = {}

    def visit(result):
        if result in memo:
            return memo[result]
        recipe = recipes[result]
        operation = recipe[0]
        if operation == "x":
            node_id = builder.add_expression("x")
        elif operation == "c":
            node_id = builder.constant(recipe[1])
        else:
            args = [visit(x) for x in recipe[1:]]
            if operation == "mem":
                lowest, highest = builder.bounds[args[0]]
                table_size = highest - lowest + 1
                if (
                    tree_start <= lowest <= highest < tree_end
                    and table_size <= table_limit
                    and table_size & (table_size - 1) == 0
                ):
                    node_id = builder.lookup_small_table(args[0], lowest, highest)
                else:
                    node_id = builder.add_expression(operation, *args)
            else:
                node_id = builder.add_expression(operation, *args)
        memo[result] = node_id
        return node_id

    anchor = visit(root)
    return anchor, dict(enumerate(builder.nodes))
