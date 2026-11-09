from datetime import date

from filaflux.allocation import suggest_candidates
from filaflux.demo_data import load_demo_data
from filaflux.models import Candidate, CancelledSlot


def test_suggestions_require_matching_service_date_and_period() -> None:
    slots, candidates = load_demo_data()

    suggestions = suggest_candidates(slots[0], candidates)

    assert [item.candidate.candidate_id for item in suggestions] == [
        "SINT-001",
        "SINT-006",
    ]


def test_suggestions_follow_existing_queue_order() -> None:
    slots, candidates = load_demo_data()

    suggestions = suggest_candidates(slots[2], candidates)

    assert [item.candidate.queue_position for item in suggestions] == [2, 3, 4]


def test_candidate_with_existing_offer_is_not_suggested_again() -> None:
    slots, candidates = load_demo_data()

    suggestions = suggest_candidates(
        slots[0],
        candidates,
        unavailable_candidate_ids={"SINT-001"},
    )

    assert [item.candidate.candidate_id for item in suggestions] == ["SINT-006"]


def test_incompatible_candidate_is_not_suggested() -> None:
    slot = CancelledSlot(
        slot_id="VAGA-TESTE",
        service="Clínica médica",
        appointment_date=date(2026, 11, 12),
        period="Manhã",
        cancellation_source="Serviço",
    )
    candidate = Candidate(
        candidate_id="SINT-TESTE",
        display_name="Pessoa sintética de teste",
        service="Clínica médica",
        synthetic_area="Território sintético de teste",
        available_dates=frozenset({date(2026, 11, 12)}),
        available_periods=frozenset({"Tarde"}),
        queue_position=1,
    )

    assert suggest_candidates(slot, [candidate]) == []
