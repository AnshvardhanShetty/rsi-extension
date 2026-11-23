"""Schedule instructions for 8 inputs at a time. Independent engines can work in the same cycle."""

from collections import Counter, defaultdict
import heapq
from .pack_instructions import pack_instructions


def assign_scratch_registers(starts, ends, first_free_register):
    # Reuse scratch registers after the last instruction that reads them.
    free_registers = []
    expiry = []
    physical = {}
    next_vector = first_free_register
    for job_id, begin in sorted(starts.items(), key=lambda item: (item[1], item[0])):
        while expiry and expiry[0][0] < begin:
            _, register = heapq.heappop(expiry)
            free_registers.append(register)
        if free_registers:
            register = free_registers.pop()
        else:
            register = next_vector
            next_vector += 8
        if next_vector > 1536:
            raise ValueError("scratch")
        physical[job_id] = register
        heapq.heappush(expiry, (ends[job_id], register))
    return physical


def schedule_instructions(
    output_node,
    expressions,
    output_address,
    blocks_per_tile,
    use_scalar_units=True,
    load_weight=4,
    block_stagger=0,
    num_blocks=32,
):
    order = []
    seen = set()

    def visit(node_id):
        if node_id in seen:
            return
        seen.add(node_id)
        expression = expressions[node_id]
        if expression[0] not in ("c", "x"):
            for a in expression[1:]:
                visit(a)
        order.append(node_id)

    visit(output_node)
    # Load constants once before scheduling the batch.
    fixed_nodes = {
        node_id
        for node_id in order
        if expressions[node_id][0] == "c"
        or (
            expressions[node_id][0] == "mem"
            and expressions[expressions[node_id][1]][0] == "c"
        )
    }
    changing_nodes = [node_id for node_id in order if node_id not in fixed_nodes]
    shared_inputs = {
        a
        for node_id in changing_nodes
        if expressions[node_id][0] != "x"
        for a in expressions[node_id][1:]
        if a in fixed_nodes
    }
    # Constant and pointer construction needs a single scalar temporary after each broadcast.
    output = []
    fixed = {}
    output_pointers = {}
    next_register = 1
    for node_id in sorted(shared_inputs):
        op, value_id = expressions[node_id]
        literal = value_id if op == "c" else expressions[value_id][1]
        output.append({"load": [("const", 0, literal)]})
        if op == "mem":
            output.append({"load": [("load", 0, 0)]})
        output.append({"valu": [("vbroadcast", next_register, 0)]})
        fixed[node_id] = next_register
        next_register += 8
    for block in range(num_blocks):
        output_pointers[block] = next_register
        next_register += 1
        output.append(
            {"load": [("const", output_pointers[block], output_address + 8 * block)]}
        )

    output = pack_instructions(output)
    for start in range(0, num_blocks, blocks_per_tile):
        jobs = []
        job_for_node = {}
        job_inputs = []
        dependents = []
        dependencies_left = []
        queues = defaultdict(list)

        def add_job(block, node_id, expression):
            job_id = len(jobs)
            job_for_node[block, node_id] = job_id
            jobs.append((block, node_id, expression))
            dependents.append([])
            a = (
                []
                if expression[0] == "x"
                else [
                    (fixed[x], True)
                    if x in fixed_nodes
                    else (job_for_node[block, x], False)
                    for x in expression[1:]
                ]
            )
            job_inputs.append(a)
            deps = {k for k, is_fixed in a if not is_fixed}
            dependencies_left.append(len(deps))
            for k in deps:
                dependents[k].append(job_id)

        for block in range(start, min(num_blocks, start + blocks_per_tile)):
            for node_id in changing_nodes:
                add_job(block, node_id, expressions[node_id])
            add_job(block, "output", ("store", output_node))
        # Give jobs on the longest dependency chain first choice of an engine.
        priority_height = [0] * len(jobs)
        for job_id in reversed(range(len(jobs))):
            h = load_weight if jobs[job_id][2][0] == "mem" else 1
            priority_height[job_id] = h + max(
                (priority_height[s] for s in dependents[job_id]), default=0
            )

        def engine_queue(op):
            if op in ("x", "mem"):
                return "load"
            if op == "store":
                return "store"
            if op == "sel":
                return "flow"
            if op == "fma":
                return "valu"
            return "binary"

        def queue_ready_job(job_id):
            heapq.heappush(
                queues[engine_queue(jobs[job_id][2][0])],
                (
                    -priority_height[job_id]
                    + block_stagger * (jobs[job_id][0] - start),
                    job_id,
                ),
            )

        for job_id, count in enumerate(dependencies_left):
            if count == 0:
                queue_ready_job(job_id)
        lane = Counter()
        cycles = []
        starts = {}
        ends = {}
        completed = 0
        while completed < len(jobs):
            tick = len(cycles)
            emits = []
            finished = []

            def issue_lanes(job_id, engine, count):
                expression = jobs[job_id][2]
                op = expression[0]
                if op != "store":
                    starts.setdefault(job_id, tick)
                    ends[job_id] = max(tick, ends.get(job_id, 0))
                for a, is_fixed in job_inputs[job_id]:
                    if not is_fixed:
                        ends[a] = tick
                first_lane = lane[job_id]
                width = 8 if op == "mem" or engine == "alu" else 1
                issued_width = min(count, width - first_lane)
                if issued_width <= 0:
                    raise AssertionError((job_id, op, first_lane, engine))
                emits.append((engine, job_id, first_lane, issued_width))
                lane[job_id] += issued_width
                if lane[job_id] == width:
                    finished.append(job_id)
                    return issued_width, True
                return issued_width, False

            for engine, queue_name, free_slots in [
                ("load", "load", 2),
                ("store", "store", 2),
                ("flow", "flow", 1),
            ]:
                queue = queues[queue_name]
                while queue and free_slots:
                    job_id = queue[0][1]
                    count, done = issue_lanes(job_id, engine, free_slots)
                    free_slots -= count
                    if done:
                        heapq.heappop(queue)
            for _ in range(6):
                choices = [
                    (queues[k][0], k)
                    for k in ("valu", "binary")
                    if queues[k] and (k != "binary" or lane[queues[k][0][1]] == 0)
                ]
                if not choices:
                    break
                (_, job_id), k = min(choices)
                heapq.heappop(queues[k])
                issue_lanes(job_id, "valu", 1)
            free_slots = 12 if use_scalar_units else 0
            while free_slots and (queues["partial"] or queues["binary"]):
                queue = queues["partial"] if queues["partial"] else queues["binary"]
                priority, job_id = heapq.heappop(queue)
                count, done = issue_lanes(job_id, "alu", free_slots)
                free_slots -= count
                if not done:
                    heapq.heappush(queues["partial"], (priority, job_id))
            assert emits
            cycles.append(emits)
            completed += len(finished)
            for job_id in finished:
                for s in dependents[job_id]:
                    dependencies_left[s] -= 1
                    if dependencies_left[s] == 0:
                        queue_ready_job(s)
        physical = assign_scratch_registers(starts, ends, next_register)
        for emits in cycles:
            bundle = {}
            for engine, job_id, first_lane, count in emits:
                block, node_id, expression = jobs[job_id]
                op = expression[0]
                registers = [
                    value if fixed else physical[value]
                    for value, fixed in job_inputs[job_id]
                ]
                emit = bundle.setdefault(engine, []).append
                if op == "store":
                    emit(("vstore", output_pointers[block], registers[0]))
                    continue
                destination = physical[job_id]
                if op == "x":
                    emit(("vload", destination, output_pointers[block]))
                elif op == "mem":
                    for lane_index in range(first_lane, first_lane + count):
                        emit(("load_offset", destination, registers[0], lane_index))
                elif engine == "alu":
                    for lane_index in range(first_lane, first_lane + count):
                        emit(
                            (
                                op,
                                destination + lane_index,
                                *(value_id + lane_index for value_id in registers),
                            )
                        )
                else:
                    emit(
                        (
                            "vselect"
                            if op == "sel"
                            else "multiply_add"
                            if op == "fma"
                            else op,
                            destination,
                            *registers,
                        )
                    )
            output.append(bundle)
    return output
