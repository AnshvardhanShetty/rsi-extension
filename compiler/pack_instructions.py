def scratch_access(engine, op):
    """Return the scratch registers an instruction reads and writes, or None for an unknown instruction."""
    name, *operands = op

    def vector_registers(a):
        return set(range(a, a + 8))

    if engine == "alu" and len(operands) == 3:
        return {operands[1], operands[2]}, {operands[0]}
    if engine == "valu":
        if name == "vbroadcast":
            return {operands[1]}, vector_registers(operands[0])
        if len(operands) in (3, 4):
            return set.union(
                *(vector_registers(a) for a in operands[1:])
            ), vector_registers(operands[0])
    if engine == "load":
        if name == "const":
            return set(), {operands[0]}
        if name == "load_offset":
            return {operands[1] + operands[2]}, {operands[0] + operands[2]}
        if name == "load":
            return {operands[1]}, {operands[0]}
        if name == "vload":
            return {operands[1]}, vector_registers(operands[0])
    if engine == "store":
        if name == "store":
            return set(operands), set()
        if name == "vstore":
            return {operands[0]} | vector_registers(operands[1]), set()
    if engine == "flow":
        if name == "vselect":
            return set.union(
                *(vector_registers(a) for a in operands[1:])
            ), vector_registers(operands[0])
        if name == "select":
            return set(operands[1:]), {operands[0]}
        if name == "add_imm":
            return {operands[1]}, {operands[0]}
    return None


def pack_instructions(bundles):
    """Merge neighboring bundles if they fit and still read the same values."""
    limits = {"alu": 12, "valu": 6, "load": 2, "store": 2, "flow": 1}
    if any("jump" in op[0] for bundle in bundles for op in bundle.get("flow", [])):
        return bundles
    packed = []
    pending = {}
    writes = set()
    for bundle in bundles:
        instructions = [
            (engine, op) for engine, slots in bundle.items() for op in slots
        ]
        register_accesses = [scratch_access(engine, op) for engine, op in instructions]
        if not instructions or None in register_accesses:
            if pending:
                packed.append(pending)
            packed.append(bundle)
            pending = {}
            writes = set()
            continue
        new_reads = set()
        new_writes = set()
        for read_registers, written_registers in register_accesses:
            new_reads.update(read_registers)
            new_writes.update(written_registers)
        overflow = any(
            len(pending.get(engine, [])) + len(operands) > limits[engine]
            for engine, operands in bundle.items()
        )
        memory_conflict = pending.get("store") and any(
            engine == "store" or (engine == "load" and op[0] != "const")
            for engine, op in instructions
        )
        if pending and (
            overflow or memory_conflict or writes & (new_reads | new_writes)
        ):
            packed.append(pending)
            pending = {}
            writes = set()
        for engine, operands in bundle.items():
            pending.setdefault(engine, []).extend(operands)
        writes.update(new_writes)
    if pending:
        packed.append(pending)
    return packed
