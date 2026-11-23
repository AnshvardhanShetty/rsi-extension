"""Follow one input through the program and record each calculation."""

import operator

UNKNOWN = -1  # The expression depends on another input lane or an untracked address.
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
        # Store a + b and b + a as the same calculation.
        if operation in ("+", "*", "&", "|", "^", "==") and args[0] > args[1]:
            args = (args[1], args[0])
        if operation == "fma" and args[0] > args[1]:
            args = (args[1], args[0], args[2])
        if UNKNOWN in args:
            return UNKNOWN
        key = (operation, *args)
        node_id = self.index.get(key)
        if node_id is None:
            if operation == "mem":
                addresses = self.values[args[0]]
                if any(a < self.tree_start or a >= self.index_start for a in addresses):
                    return UNKNOWN
                values = tuple(m[a] for m, a in zip(self.sample_memories, addresses))
            else:
                if operation not in OPERATIONS:
                    return UNKNOWN
                try:
                    values = tuple(
                        int(OPERATIONS[operation](*v)) & WORD_MASK
                        for v in zip(*(self.values[operand_id] for operand_id in args))
                    )
                except (ArithmeticError, ValueError):
                    return UNKNOWN
                if all(self.nodes[operand_id][0] == "c" for operand_id in args):
                    return self.constant(values[0])
            node_id = self.record_expression(key, values)
        self.program_nodes.add(node_id)
        return node_id

    def read_program(self, bundles):
        """Return the calculation for the first output and the steps found in the program."""
        self.program_nodes = set()
        zero = self.constant(0)
        scratch = [zero] * 1536
        stored_values = {}

        def read_memory(address_node):
            if address_node == UNKNOWN:
                return UNKNOWN
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
            return UNKNOWN

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
                for name, *registers in instructions:
                    if engine == "alu":
                        dest, left, right = registers
                        value = self.operation(name, scratch[left], scratch[right])
                        updates.append((dest, value))
                    elif engine == "valu":
                        dest, *sources = registers
                        for lane in range(8):
                            if name == "vbroadcast":
                                value = scratch[sources[0]]
                            else:
                                operation = "fma" if name == "multiply_add" else name
                                values = [scratch[source + lane] for source in sources]
                                value = self.operation(operation, *values)
                            updates.append((dest + lane, value))
                    elif engine == "load":
                        dest, source, *offset = registers
                        if name == "const":
                            updates.append((dest, self.constant(source)))
                        elif name == "load":
                            updates.append((dest, read_memory(scratch[source])))
                        elif name == "load_offset":
                            lane = offset[0]
                            value = read_memory(scratch[source + lane])
                            updates.append((dest + lane, value))
                        elif name == "vload":
                            for lane in range(8):
                                address = self.operation(
                                    "+", scratch[source], self.constant(lane)
                                )
                                updates.append((dest + lane, read_memory(address)))
                        else:
                            raise ValueError(name)
                    elif engine == "store":
                        address_reg, source = registers
                        if name == "store":
                            stores.append((scratch[address_reg], scratch[source]))
                        elif name == "vstore":
                            for lane in range(8):
                                address = self.operation(
                                    "+", scratch[address_reg], self.constant(lane)
                                )
                                stores.append((address, scratch[source + lane]))
                        else:
                            raise ValueError(name)
                    elif engine == "flow":
                        if name == "pause":
                            continue
                        if name == "add_imm":
                            dest, source, number = registers
                            value = self.operation(
                                "+", scratch[source], self.constant(number)
                            )
                            updates.append((dest, value))
                        elif name in ("select", "vselect"):
                            dest, condition, yes, no = registers
                            width = 8 if name == "vselect" else 1
                            for lane in range(width):
                                value = self.operation(
                                    "sel",
                                    scratch[condition + lane],
                                    scratch[yes + lane],
                                    scratch[no + lane],
                                )
                                updates.append((dest + lane, value))
                        else:
                            raise ValueError(name)

            # All instructions in a cycle read the old registers and memory.
            for register, value in updates:
                scratch[register] = value
            for address, value in stores:
                write_memory(address, value)

        output = stored_values.get(self.value_start, self.input_value)
        return output, sorted(self.program_nodes)
