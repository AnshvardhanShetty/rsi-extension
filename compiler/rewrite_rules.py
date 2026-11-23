"""Suggest cheaper expressions. The proof step checks each suggestion before use."""


def arithmetic_rewrites(graph, available):
    """Enumerate ordinary constant-strength reductions and fused arithmetic in the scalar IR."""
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
            operation(
                "&" if name == "%" else ">>",
                left,
                constant(
                    right_constant - 1
                    if name == "%"
                    else right_constant.bit_length() - 1
                ),
            )
        if name == "sel":
            condition, when_true, when_false = node[1:]
            y = graph.constant_value(when_true)
            z = graph.constant_value(when_false)
            if (
                y is not None
                and z is not None
                and graph.nodes[condition][0] in ("<", "==")
            ):
                operation("fma", condition, constant(y - z), constant(z))
            if z == 0 and graph.nodes[condition][0] in ("<", "=="):
                operation("*", condition, when_true)
            if y == 0 and graph.nodes[condition][0] in ("<", "=="):
                operation("*", operation("^", condition, constant(1)), when_false)
        if name == "==":
            for x, compared_value in ((left, right_constant), (right, left_constant)):
                test_operand = graph.nodes[x]
                if compared_value == 0 and (
                    test_operand[0] == "%"
                    and graph.constant_value(test_operand[2]) == 2
                    or test_operand[0] == "&"
                    and 1
                    in (
                        graph.constant_value(test_operand[1]),
                        graph.constant_value(test_operand[2]),
                    )
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
                    o = graph.nodes[other]
                    if o[0] == "+" and product[1] in o[1:]:
                        addend = o[2] if product[1] == o[1] else o[1]
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
