from datetime import date
from itertools import product

from vaga_viva.allocation import suggest_candidates
from vaga_viva.models import Candidate, CancelledSlot, TimePeriod
from vaga_viva.optimization import (
    allocate_multicriteria,
    potential_wait_days_avoided,
)
from vaga_viva.policy_simulation import generate_synthetic_scenario


def build_slot(
    slot_id: str,
    *,
    period: str = "Manhã",
    unit_id: str = "UNIDADE-1",
    accessibility_features: frozenset[str] = frozenset(),
) -> CancelledSlot:
    return CancelledSlot(
        slot_id=slot_id,
        service="Cardiologia",
        appointment_date=date(2026, 11, 12),
        period=period,
        cancellation_source="Serviço",
        unit_id=unit_id,
        accessibility_features=accessibility_features,
    )


def build_candidate(
    candidate_id: str,
    queue_position: int,
    *,
    available_dates: frozenset[date] = frozenset({date(2026, 11, 12)}),
    available_periods: frozenset[TimePeriod] = frozenset({"Manhã"}),
    preferred_periods: frozenset[TimePeriod] = frozenset(),
    preferred_unit_ids: frozenset[str] = frozenset(),
    accessibility_needs: frozenset[str] = frozenset(),
    baseline_appointment_date: date | None = None,
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id,
        display_name=f"Pessoa sintética {candidate_id}",
        service="Cardiologia",
        synthetic_area="Território sintético A",
        available_dates=available_dates,
        available_periods=available_periods,
        queue_position=queue_position,
        preferred_periods=preferred_periods,
        preferred_unit_ids=preferred_unit_ids,
        accessibility_needs=accessibility_needs,
        baseline_appointment_date=baseline_appointment_date,
    )


def _objective_score(
    assignments: dict[str, str],
    slots: list[CancelledSlot],
    candidates: list[Candidate],
) -> tuple[int, int, int]:
    slot_by_id = {slot.slot_id: slot for slot in slots}
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    queue_sum = sum(
        candidate_by_id[candidate_id].queue_position
        for candidate_id in assignments.values()
    )
    preference_mismatches = 0
    for slot_id, candidate_id in assignments.items():
        candidate = candidate_by_id[candidate_id]
        slot = slot_by_id[slot_id]
        if (
            candidate.preferred_periods
            and slot.period not in candidate.preferred_periods
        ):
            preference_mismatches += 1
        if (
            candidate.preferred_unit_ids
            and slot.unit_id not in candidate.preferred_unit_ids
        ):
            preference_mismatches += 1
    return len(assignments), -queue_sum, -preference_mismatches


def test_optimizer_maximizes_fills_before_queue_priority() -> None:
    day_one = date(2026, 11, 12)
    day_two = date(2026, 11, 13)
    slots = [
        build_slot("FLEX"),
        CancelledSlot(
            slot_id="ONLY-Q1",
            service="Cardiologia",
            appointment_date=day_two,
            period="Tarde",
            cancellation_source="Serviço",
        ),
    ]
    candidates = [
        build_candidate(
            "Q1",
            1,
            available_dates=frozenset({day_one, day_two}),
            available_periods=frozenset({"Manhã", "Tarde"}),
        ),
        build_candidate("Q2", 2),
    ]

    result = allocate_multicriteria(slots, candidates)

    assert result.assignments == {"FLEX": "Q2", "ONLY-Q1": "Q1"}
    assert result.filled_slot_count == 2
    assert result.total_queue_position == 3


def test_optimizer_prefers_earlier_queue_position_when_fill_is_equal() -> None:
    slot = build_slot("V1")
    candidates = [
        build_candidate("LATER", 2),
        build_candidate("EARLIER", 1),
    ]

    result = allocate_multicriteria([slot], candidates)

    assert result.assignments == {"V1": "EARLIER"}


def test_optimizer_uses_declared_preferences_only_after_queue_tie() -> None:
    slots = [
        build_slot("UNIT-1", unit_id="UNIT-1"),
        build_slot("UNIT-2", unit_id="UNIT-2"),
    ]
    candidates = [
        build_candidate(
            "PREF-1",
            1,
            preferred_unit_ids=frozenset({"UNIT-1"}),
        ),
        build_candidate(
            "PREF-2",
            1,
            preferred_unit_ids=frozenset({"UNIT-2"}),
        ),
    ]

    result = allocate_multicriteria(slots, candidates)

    assert result.assignments == {"UNIT-1": "PREF-1", "UNIT-2": "PREF-2"}
    assert result.preference_mismatches == 0


def test_accessibility_needs_are_hard_compatibility_constraints() -> None:
    slot = build_slot(
        "V1",
        accessibility_features=frozenset({"rota_acessivel"}),
    )
    candidates = [
        build_candidate(
            "NEEDS-LIFT",
            1,
            accessibility_needs=frozenset({"elevador"}),
        ),
        build_candidate(
            "NEEDS-RAMP",
            2,
            accessibility_needs=frozenset({"rota_acessivel"}),
        ),
    ]

    suggestions = suggest_candidates(slot, candidates)
    result = allocate_multicriteria([slot], candidates)

    assert [item.candidate.candidate_id for item in suggestions] == ["NEEDS-RAMP"]
    assert result.assignments == {"V1": "NEEDS-RAMP"}


def test_generator_creates_reproducible_access_preferences_and_wait_baselines() -> None:
    first = generate_synthetic_scenario(seed=13, slot_count=8, candidate_count=12)
    second = generate_synthetic_scenario(seed=13, slot_count=8, candidate_count=12)

    assert first == second
    assert all(slot.unit_id.startswith("UNIDADE-SIM-") for slot in first.slots)
    assert all(
        candidate.baseline_appointment_date is not None
        for candidate in first.candidates
    )


def test_potential_wait_days_are_synthetic_and_not_reported_without_baselines() -> None:
    slot = build_slot("V1")
    candidate_with_baseline = build_candidate(
        "C1",
        1,
        baseline_appointment_date=date(2026, 12, 12),
    )
    candidate_without_baseline = build_candidate("C2", 2)

    result_with_baseline = allocate_multicriteria(
        [slot],
        [candidate_with_baseline],
    )
    result_without_baseline = allocate_multicriteria(
        [slot],
        [candidate_without_baseline],
    )

    assert potential_wait_days_avoided(
        result_with_baseline,
        [slot],
        [candidate_with_baseline],
    ) == 30
    assert potential_wait_days_avoided(
        result_without_baseline,
        [slot],
        [candidate_without_baseline],
    ) is None


def test_optimizer_matches_exhaustive_lexicographic_objective_on_small_scenarios() -> None:
    for seed in range(12):
        scenario = generate_synthetic_scenario(
            seed=seed,
            slot_count=4,
            candidate_count=5,
        )
        slots = list(scenario.slots)
        candidates = list(scenario.candidates)
        options = [
            [
                None,
                *(
                    suggestion.candidate.candidate_id
                    for suggestion in suggest_candidates(slot, candidates)
                ),
            ]
            for slot in slots
        ]
        best_score = (-1, 0, 0)
        for choices in product(*options):
            assigned_ids = [candidate_id for candidate_id in choices if candidate_id]
            if len(assigned_ids) != len(set(assigned_ids)):
                continue
            assignments = {
                slot.slot_id: candidate_id
                for slot, candidate_id in zip(slots, choices)
                if candidate_id is not None
            }
            best_score = max(
                best_score,
                _objective_score(assignments, slots, candidates),
            )

        result = allocate_multicriteria(slots, candidates)

        assert _objective_score(dict(result.assignments), slots, candidates) == best_score


def test_optimizer_handles_empty_scenario() -> None:
    result = allocate_multicriteria([], [])

    assert result.assignments == {}
    assert result.filled_slot_count == 0
    assert result.unfilled_slot_count == 0
