"""Suggest simpler calculations for Z3 to check."""


def arithmetic_rewrites(graph, available):
    """Try cheaper ways to do the same arithmetic in one lane."""
    nodes = set(available)
    candidates = set()

    constant = graph.constant

    def operation(name, *args):
        node_id = graph.operation(name, *args)
        if node_id >= 0:
            candidates.add(node_id)
        return node_id

    for node_id in sorted(nodes):
        node = graph.nodes[node_id]
        name = node[0]
        if name in ("x", "c", "mem"):
            continue
        left = node[1]
        right = node[2]
        left_constant = graph.constant_value(left)
        right_constant = graph.constant_value(right)
        if (
            name in ("%", "//")
            and right_constant is not None
            and right_constant > 0
            and right_constant & (right_constant - 1) == 0
        ):
            if name == "%":
                operation("&", left, constant(right_constant - 1))
            else:
                shift = right_constant.bit_length() - 1
                operation(">>", left, constant(shift))
        if name == "sel":
            condition, when_true, when_false = node[1:]
            if graph.nodes[condition][0] not in ("<", "=="):
                continue
            # A comparison produces 0 or 1, so it can act as a multiplier.
            true_value = graph.constant_value(when_true)
            false_value = graph.constant_value(when_false)
            if true_value is not None and false_value is not None:
                operation(
                    "fma",
                    condition,
                    constant(true_value - false_value),
                    constant(false_value),
                )
            if false_value == 0:
                operation("*", condition, when_true)
            if true_value == 0:
                operation("*", operation("^", condition, constant(1)), when_false)
        if name == "==":
            for x, compared_value in ((left, right_constant), (right, left_constant)):
                if compared_value != 0:
                    continue
                test = graph.nodes[x]
                if test[0] == "%" and graph.constant_value(test[2]) == 2:
                    operation("^", x, constant(1))
                elif test[0] == "&" and any(
                    graph.constant_value(arg) == 1 for arg in test[1:]
                ):
                    operation("^", x, constant(1))
        if name == "+":
            for mul, other in ((left, right), (right, left)):
                product = graph.nodes[mul]
                if product[0] == "*":
                    operation("fma", product[1], product[2], other)
                if (
                    product[0] == "<<"
                    and graph.constant_value(product[2]) is not None
                    and graph.constant_value(product[2]) < 32
                ):
                    factor = 1 << graph.constant_value(product[2])
                    operation("fma", product[1], constant(factor), other)
                    other_term = graph.nodes[other]
                    if other_term[0] == "+" and product[1] in other_term[1:]:
                        addend = (
                            other_term[2]
                            if product[1] == other_term[1]
                            else other_term[1]
                        )
                        operation("fma", product[1], constant(factor + 1), addend)
    return candidates


def remove_zero_test(graph, starter_nodes):
    """select(x == 0, a, b) and select(x, b, a) choose the same value."""
    candidates = set()
    for node_id in starter_nodes:
        node = graph.nodes[node_id]
        if node[0] != "sel":
            continue
        test = graph.nodes[node[1]]
        if test[0] != "==":
            continue
        for x, z in ((test[1], test[2]), (test[2], test[1])):
            if graph.constant_value(z) == 0:
                candidates.add(graph.operation("sel", x, node[3], node[2]))
    return candidates
