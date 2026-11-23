"""Follow one input value through the instructions and record the expressions used to compute it."""

import operator

WORD_MASK = (1 << 32) - 1
OPERATIONS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "&": operator.and_,
    "|": operator.or_,
    "^": operator.xor,
    "<<": lambda a, b: 0 if b >= 32 else a << b,
    ">>": operator.rshift,
    "<": operator.lt,
    "==": operator.eq,
    "%": operator.mod,
    "//": operator.floordiv,
    "fma": lambda a, b, c: a * b + c,
    "sel": lambda input_value, a, b: a if input_value else b,
}


class ExpressionGraph:
    """Each node stores an operation, its inputs, and its results on 12 sample trees."""

    def __init__(self, sample_memory):
        self.nodes = []
        self.values = []
        self.index = {}
        self.program_nodes = set()
        self.sample_memories = [sample_memory(seed) for seed in range(82111, 82123)]
        self.tree_start = self.sample_memories[0][4]
        self.index_start = self.sample_memories[0][5]
        self.value_start = self.sample_memories[0][6]
        self.input_value = self.record_expression(
            ("x",), tuple(m[self.value_start] for m in self.sample_memories)
        )

    def record_expression(self, key, sample_values):
        node_id = len(self.nodes)
        self.index[key] = node_id
        self.nodes.append(key)
        self.values.append(sample_values)
        return node_id

    def constant(self, number):
        number = int(number) & WORD_MASK
        key = ("c", number)
        node_id = self.index.get(key)
        if node_id is None:
            node_id = self.record_expression(key, (number,) * len(self.sample_memories))
        return node_id

    def constant_value(self, node_id):
        return (
            self.nodes[node_id][1]
            if node_id >= 0 and self.nodes[node_id][0] == "c"
            else None
        )

    def operation(self, operation, *args):
        if operation in ("+", "*", "&", "|", "^", "==") and args[0] > args[1]:
            args = (args[1], args[0])
        if operation == "fma" and args[0] > args[1]:
            args = (args[1], args[0], args[2])
        if -1 in args:
            return -1
        key = (operation, *args)
        node_id = self.index.get(key)
        if node_id is None:
            if operation == "mem":
                addresses = self.values[args[0]]
                if any(a < self.tree_start or a >= self.index_start for a in addresses):
                    return -1
                values = tuple(m[a] for m, a in zip(self.sample_memories, addresses))
            else:
                if operation not in OPERATIONS:
                    return -1
                try:
                    values = tuple(
                        int(OPERATIONS[operation](*v)) & WORD_MASK
                        for v in zip(*(self.values[operand_id] for operand_id in args))
                    )
                except (ArithmeticError, ValueError):
                    return -1
                if all(self.nodes[operand_id][0] == "c" for operand_id in args):
                    return self.constant(values[0])
            node_id = self.record_expression(key, values)
        self.program_nodes.add(node_id)
        return node_id

    def read_program(self, bundles):
        """Track which expression each scratch register holds. Writes take effect after a bundle."""
        self.program_nodes = set()
        zero = self.constant(0)
        scratch = [zero] * 1536
        stored_values = {}

        def read_memory(address_node):
            if address_node == -1:
                return -1
            address = self.constant_value(address_node)
            if address is None:
                return self.operation("mem", address_node)
            if address in stored_values:
                return stored_values[address]
            if address < self.tree_start:
                return self.constant(self.sample_memories[0][address])
            if address < self.index_start:
                return self.operation("mem", address_node)
            if address < self.value_start:
                return zero
            if address == self.value_start:
                return self.input_value
            return -1

        def write_memory(address_node, value):
            address = self.constant_value(address_node)
            if address is None or address < self.index_start:
                raise ValueError("unresolved store address")
            stored_values[address] = value

        for bundle in bundles:
            updates = []
            stores = []
            for engine, instructions in bundle.items():
                if engine == "debug":
                    continue
                for name, *operands in instructions:
                    if engine == "alu":
                        updates.append(
                            (
                                operands[0],
                                self.operation(
                                    name, scratch[operands[1]], scratch[operands[2]]
                                ),
                            )
                        )
                    elif engine == "valu":
                        for lane in range(8):
                            result = (
                                scratch[operands[1]]
                                if name == "vbroadcast"
                                else self.operation(
                                    "fma" if name == "multiply_add" else name,
                                    *(scratch[k + lane] for k in operands[1:]),
                                )
                            )
                            updates.append((operands[0] + lane, result))
                    elif engine == "load":
                        if name == "const":
                            updates.append((operands[0], self.constant(operands[1])))
                        elif name == "load":
                            updates.append(
                                (operands[0], read_memory(scratch[operands[1]]))
                            )
                        elif name == "load_offset":
                            updates.append(
                                (
                                    operands[0] + operands[2],
                                    read_memory(scratch[operands[1] + operands[2]]),
                                )
                            )
                        elif name == "vload":
                            for lane in range(8):
                                updates.append(
                                    (
                                        operands[0] + lane,
                                        read_memory(
                                            self.operation(
                                                "+",
                                                scratch[operands[1]],
                                                self.constant(lane),
                                            )
                                        ),
                                    )
                                )
                        else:
                            raise ValueError(name)
                    elif engine == "store":
                        if name == "store":
                            stores.append((scratch[operands[0]], scratch[operands[1]]))
                        elif name == "vstore":
                            for lane in range(8):
                                stores.append(
                                    (
                                        self.operation(
                                            "+",
                                            scratch[operands[0]],
                                            self.constant(lane),
                                        ),
                                        scratch[operands[1] + lane],
                                    )
                                )
                        else:
                            raise ValueError(name)
                    elif engine == "flow":
                        if name == "pause":
                            continue
                        if name == "add_imm":
                            updates.append(
                                (
                                    operands[0],
                                    self.operation(
                                        "+",
                                        scratch[operands[1]],
                                        self.constant(operands[2]),
                                    ),
                                )
                            )
                        elif name in ("select", "vselect"):
                            for lane in range(8 if name == "vselect" else 1):
                                updates.append(
                                    (
                                        operands[0] + lane,
                                        self.operation(
                                            "sel",
                                            *(scratch[k + lane] for k in operands[1:]),
                                        ),
                                    )
                                )
                        else:
                            raise ValueError(name)
            for register, value in updates:
                scratch[register] = value
            for address, value in stores:
                write_memory(address, value)
        return stored_values.get(self.value_start, self.input_value), sorted(
            self.program_nodes
        )
