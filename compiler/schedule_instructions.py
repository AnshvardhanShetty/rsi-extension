"""Work out which instructions can run together on eight inputs at a time."""

from collections import Counter, defaultdict
import heapq
from .pack_instructions import pack_instructions


def assign_scratch_registers(starts, ends, first_free_register):
    """Give each value eight registers. Reuse them once the value is no longer needed."""
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
    """Take the steps for one input and schedule them for the whole batch."""
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
    # Register 0 is temporary. Each broadcast leaves eight copies in scratch.
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
        blocks = range(start, min(start + blocks_per_tile, num_blocks))
        jobs, job_inputs = build_tile_jobs(
            blocks, changing_nodes, expressions, fixed, output_node
        )
        cycles, starts, ends = schedule_tile(
            jobs, job_inputs, start, load_weight, block_stagger, use_scalar_units
        )
        registers = assign_scratch_registers(starts, ends, next_register)
        output.extend(
            emit_bundles(cycles, jobs, job_inputs, registers, output_pointers)
        )
    return output


def build_tile_jobs(blocks, changing_nodes, expressions, fixed, output_node):
    """Each block computes the same expressions but has its own inputs and output."""
    jobs = []
    job_for_node = {}
    job_inputs = []

    def add_job(block, node_id, expression):
        job_for_node[block, node_id] = len(jobs)
        jobs.append((block, node_id, expression))
        inputs = []
        for source in expression[1:]:
            if source in fixed:
                inputs.append((fixed[source], True))
            else:
                inputs.append((job_for_node[block, source], False))
        job_inputs.append(inputs)

    for block in blocks:
        for node_id in changing_nodes:
            add_job(block, node_id, expressions[node_id])
        add_job(block, "output", ("store", output_node))
    return jobs, job_inputs


def schedule_tile(
    jobs, job_inputs, start, load_weight, block_stagger, use_scalar_units
):
    """Choose what runs each cycle and track how long each result is needed."""
    queues = defaultdict(list)
    dependents = [[] for _ in jobs]
    dependencies_left = []
    for job_id, inputs in enumerate(job_inputs):
        producers = {source for source, is_register in inputs if not is_register}
        dependencies_left.append(len(producers))
        for producer in producers:
            dependents[producer].append(job_id)
    # Give jobs on the longest dependency chain first choice of an engine.
    priority_height = [0] * len(jobs)
    for job_id in reversed(range(len(jobs))):
        instruction_cost = load_weight if jobs[job_id][2][0] == "mem" else 1
        priority_height[job_id] = instruction_cost + max(
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
                -priority_height[job_id] + block_stagger * (jobs[job_id][0] - start),
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
            for source, is_fixed in job_inputs[job_id]:
                if not is_fixed:
                    ends[source] = tick
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

        for engine, free_slots in (("load", 2), ("store", 2), ("flow", 1)):
            queue = queues[engine]
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
    return cycles, starts, ends


def emit_bundles(cycles, jobs, job_inputs, physical, output_pointers):
    """Turn scheduled jobs into instructions, one cycle at a time."""
    for emits in cycles:
        bundle = {}
        for engine, job_id, first_lane, count in emits:
            block, _, expression = jobs[job_id]
            op = expression[0]
            registers = [
                value if is_register else physical[value]
                for value, is_register in job_inputs[job_id]
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
                instruction = {"sel": "vselect", "fma": "multiply_add"}.get(op, op)
                emit((instruction, destination, *registers))
        yield bundle
