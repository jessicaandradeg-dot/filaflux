from collections.abc import Sequence
from dataclasses import dataclass
from math import inf

from filaflux.models import Candidate, CancelledSlot
from filaflux.policy_simulation import PolicyResult, _eligible_pair_counts_by_area


@dataclass
class _Edge:
    target: int
    reverse_index: int
    capacity: int
    cost: int


def _preference_mismatch_count(candidate: Candidate, slot: CancelledSlot) -> int:
    mismatches = 0
    if candidate.preferred_periods and slot.period not in candidate.preferred_periods:
        mismatches += 1
    if candidate.preferred_unit_ids and slot.unit_id not in candidate.preferred_unit_ids:
        mismatches += 1
    return mismatches


def allocate_multicriteria(
    slots: Sequence[CancelledSlot],
    candidates: Sequence[Candidate],
) -> PolicyResult:
    """Maximize compatible allocations, then queue position, then preferences.

    Accessibility requirements are hard compatibility constraints. The queue
    and preference criteria are experimental tie-breaks for synthetic scenarios,
    not clinical priority rules.
    """
    ordered_slots = sorted(
        slots,
        key=lambda slot: (
            slot.appointment_date,
            slot.period,
            slot.unit_id,
            slot.slot_id,
        ),
    )
    ordered_candidates = sorted(
        candidates,
        key=lambda candidate: (
            candidate.service,
            candidate.queue_position,
            candidate.candidate_id,
        ),
    )
    slot_count = len(ordered_slots)
    candidate_count = len(ordered_candidates)
    source = 0
    first_slot_node = 1
    first_candidate_node = first_slot_node + slot_count
    sink = first_candidate_node + candidate_count
    graph: list[list[_Edge]] = [[] for _ in range(sink + 1)]
    assignment_edges: dict[tuple[str, str], _Edge] = {}

    def add_edge(start: int, target: int, capacity: int, cost: int) -> _Edge:
        forward = _Edge(target, len(graph[target]), capacity, cost)
        reverse = _Edge(start, len(graph[start]), 0, -cost)
        graph[start].append(forward)
        graph[target].append(reverse)
        return forward

    candidate_nodes = {
        candidate.candidate_id: first_candidate_node + index
        for index, candidate in enumerate(ordered_candidates)
    }
    max_assignments = min(slot_count, candidate_count)
    max_preference_cost = 2 * max_assignments
    queue_cost_scale = max_preference_cost + 1

    for slot_index, slot in enumerate(ordered_slots):
        slot_node = first_slot_node + slot_index
        add_edge(source, slot_node, 1, 0)
        for candidate in ordered_candidates:
            if candidate.service != slot.service:
                continue
            if slot.appointment_date not in candidate.available_dates:
                continue
            if slot.period not in candidate.available_periods:
                continue
            if not candidate.accessibility_needs.issubset(slot.accessibility_features):
                continue
            cost = (
                candidate.queue_position * queue_cost_scale
                + _preference_mismatch_count(candidate, slot)
            )
            assignment_edges[(slot.slot_id, candidate.candidate_id)] = add_edge(
                slot_node,
                candidate_nodes[candidate.candidate_id],
                1,
                cost,
            )

    for candidate in ordered_candidates:
        add_edge(candidate_nodes[candidate.candidate_id], sink, 1, 0)

    while True:
        distances = [inf] * len(graph)
        previous_node = [-1] * len(graph)
        previous_edge = [-1] * len(graph)
        distances[source] = 0

        for _ in range(len(graph) - 1):
            changed = False
            for node, edges in enumerate(graph):
                if distances[node] == inf:
                    continue
                for edge_index, edge in enumerate(edges):
                    if edge.capacity == 0:
                        continue
                    candidate_distance = distances[node] + edge.cost
                    if candidate_distance < distances[edge.target]:
                        distances[edge.target] = candidate_distance
                        previous_node[edge.target] = node
                        previous_edge[edge.target] = edge_index
                        changed = True
            if not changed:
                break

        if previous_node[sink] == -1:
            break

        node = sink
        while node != source:
            parent = previous_node[node]
            edge = graph[parent][previous_edge[node]]
            edge.capacity -= 1
            graph[node][edge.reverse_index].capacity += 1
            node = parent

    assignments = {
        slot_id: candidate_id
        for (slot_id, candidate_id), edge in assignment_edges.items()
        if edge.capacity == 0
    }
    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in ordered_candidates
    }
    slot_by_id = {slot.slot_id: slot for slot in ordered_slots}

    return PolicyResult(
        assignments=assignments,
        eligible_pair_counts_by_area=_eligible_pair_counts_by_area(
            ordered_slots,
            ordered_candidates,
        ),
        slot_count=slot_count,
        total_queue_position=sum(
            candidate_by_id[candidate_id].queue_position
            for candidate_id in assignments.values()
        ),
        preference_mismatches=sum(
            _preference_mismatch_count(
                candidate_by_id[candidate_id],
                slot_by_id[slot_id],
            )
            for slot_id, candidate_id in assignments.items()
        ),
    )


def potential_wait_days_avoided(
    result: PolicyResult,
    slots: Sequence[CancelledSlot],
    candidates: Sequence[Candidate],
) -> int | None:
    """Sum hypothetical days versus each synthetic candidate's baseline date."""
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    slot_by_id = {slot.slot_id: slot for slot in slots}
    saved_days: list[int] = []

    for slot_id, candidate_id in result.assignments.items():
        baseline_date = candidate_by_id[candidate_id].baseline_appointment_date
        if baseline_date is None:
            return None
        saved_days.append(
            max(0, (baseline_date - slot_by_id[slot_id].appointment_date).days)
        )

    return sum(saved_days)
