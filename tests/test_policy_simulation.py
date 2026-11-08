from datetime import date

from vaga_viva.models import Candidate, CancelledSlot
from vaga_viva.policy_simulation import (
    allocate_in_batch,
    allocate_sequentially,
    generate_synthetic_scenario,
    summarize_policy_results,
)


def build_greedy_counterexample() -> tuple[list[CancelledSlot], list[Candidate]]:
    day_one = date(2026, 11, 12)
    day_two = date(2026, 11, 13)
    slots = [
        CancelledSlot(
            slot_id="FLEX",
            service="Cardiologia",
            appointment_date=day_one,
            period="Manhã",
            cancellation_source="Serviço",
        ),
        CancelledSlot(
            slot_id="ONLY-ONE",
            service="Cardiologia",
            appointment_date=day_two,
            period="Tarde",
            cancellation_source="Serviço",
        ),
    ]
    candidates = [
        Candidate(
            candidate_id="Q1",
            display_name="Pessoa sintética 1",
            service="Cardiologia",
            synthetic_area="Território sintético A",
            available_dates=frozenset({day_one, day_two}),
            available_periods=frozenset({"Manhã", "Tarde"}),
            queue_position=1,
        ),
        Candidate(
            candidate_id="Q2",
            display_name="Pessoa sintética 2",
            service="Cardiologia",
            synthetic_area="Território sintético B",
            available_dates=frozenset({day_one}),
            available_periods=frozenset({"Manhã"}),
            queue_position=2,
        ),
    ]
    return slots, candidates


def test_batch_fills_more_than_greedy_on_flexible_slot_example() -> None:
    slots, candidates = build_greedy_counterexample()

    sequential = allocate_sequentially(slots, candidates)
    batch = allocate_in_batch(slots, candidates)

    assert sequential.assignments == {"FLEX": "Q1"}
    assert batch.assignments == {"ONLY-ONE": "Q1", "FLEX": "Q2"}
    assert batch.filled_slot_count == 2
    assert batch.unfilled_slot_count == 0


def test_batch_assignment_is_compatible_and_candidates_are_unique() -> None:
    scenario = generate_synthetic_scenario(seed=16, slot_count=12, candidate_count=20)

    result = allocate_in_batch(scenario.slots, scenario.candidates)
    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in scenario.candidates
    }
    slot_by_id = {slot.slot_id: slot for slot in scenario.slots}

    assert len(set(result.assignments.values())) == len(result.assignments)
    for slot_id, candidate_id in result.assignments.items():
        slot = slot_by_id[slot_id]
        candidate = candidate_by_id[candidate_id]
        assert candidate.service == slot.service
        assert slot.appointment_date in candidate.available_dates
        assert slot.period in candidate.available_periods


def test_batch_cardinality_is_never_lower_than_sequential() -> None:
    for seed in range(50):
        scenario = generate_synthetic_scenario(
            seed=seed,
            slot_count=10,
            candidate_count=18,
        )

        sequential = allocate_sequentially(scenario.slots, scenario.candidates)
        batch = allocate_in_batch(scenario.slots, scenario.candidates)

        assert batch.filled_slot_count >= sequential.filled_slot_count


def test_scenario_generation_is_reproducible() -> None:
    first = generate_synthetic_scenario(seed=27, slot_count=8, candidate_count=12)
    second = generate_synthetic_scenario(seed=27, slot_count=8, candidate_count=12)

    assert first == second


def test_default_demonstration_seed_shows_batch_allocation_gain() -> None:
    scenario = generate_synthetic_scenario(seed=7, slot_count=10, candidate_count=10)

    sequential = allocate_sequentially(scenario.slots, scenario.candidates)
    batch = allocate_in_batch(scenario.slots, scenario.candidates)

    assert sequential.filled_slot_count == 5
    assert batch.filled_slot_count == 6


def test_policy_distribution_counts_group_opportunities_and_allocations() -> None:
    slots, candidates = build_greedy_counterexample()

    result = allocate_in_batch(slots, candidates)
    distribution = summarize_policy_results(result, candidates)

    assert distribution == [
        {
            "Grupo fictício": "Território sintético A",
            "Pares elegíveis": 2,
            "Vagas alocadas": 1,
            "Alocadas / pares elegíveis": 0.5,
        },
        {
            "Grupo fictício": "Território sintético B",
            "Pares elegíveis": 1,
            "Vagas alocadas": 1,
            "Alocadas / pares elegíveis": 1.0,
        },
    ]


def test_empty_inputs_produce_no_allocations() -> None:
    sequential = allocate_sequentially([], [])
    batch = allocate_in_batch([], [])

    assert sequential.assignments == {}
    assert batch.assignments == {}
    assert batch.unfilled_slot_count == 0
