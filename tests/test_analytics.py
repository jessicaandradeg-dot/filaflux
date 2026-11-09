from filaflux.analytics import (
    calculate_availability_profile,
    calculate_group_distribution,
    calculate_operational_metrics,
)
from filaflux.demo_data import load_demo_data
from filaflux.models import Candidate
from filaflux.workflow import OfferAttempt


def test_operational_metrics_are_undefined_without_responses() -> None:
    slots, _ = load_demo_data()

    metrics = calculate_operational_metrics(slots, {})

    assert metrics.slot_count == 3
    assert metrics.filled_slot_count == 0
    assert metrics.fill_rate == 0
    assert metrics.resolution_acceptance_rate is None
    assert metrics.mean_offers_per_filled_slot is None
    assert metrics.filled_by_cancellation_source == {
        "Paciente": (0, 1),
        "Serviço": (0, 2),
    }


def test_operational_metrics_count_completed_offer_sequence() -> None:
    slots, _ = load_demo_data()
    history = {
        "VAGA-001": [
            OfferAttempt(
                slot_id="VAGA-001",
                candidate_id="SINT-001",
                status="declined",
            ),
            OfferAttempt(
                slot_id="VAGA-001",
                candidate_id="SINT-006",
                status="accepted",
            ),
        ],
        "VAGA-002": [
            OfferAttempt(slot_id="VAGA-002", candidate_id="SINT-003")
        ],
    }

    metrics = calculate_operational_metrics(slots, history)

    assert metrics.offer_count == 3
    assert metrics.filled_slot_count == 1
    assert metrics.accepted_count == 1
    assert metrics.declined_count == 1
    assert metrics.pending_count == 1
    assert metrics.fill_rate == 1 / 3
    assert metrics.resolution_acceptance_rate == 1 / 2
    assert metrics.mean_offers_per_filled_slot == 2
    assert metrics.filled_by_cancellation_source == {
        "Paciente": (0, 1),
        "Serviço": (1, 2),
    }


def test_group_distribution_uses_only_synthetic_eligible_opportunities() -> None:
    slots, candidates = load_demo_data()
    history = {
        "VAGA-001": [
            OfferAttempt(
                slot_id="VAGA-001",
                candidate_id="SINT-001",
                status="declined",
            ),
            OfferAttempt(slot_id="VAGA-001", candidate_id="SINT-006"),
        ]
    }

    distribution = calculate_group_distribution(slots, candidates, history)

    assert [
        (
            item.synthetic_area,
            item.eligible_opportunities,
            item.offers,
            item.declined,
            item.pending,
        )
        for item in distribution
    ] == [
        ("Território sintético A", 2, 1, 1, 0),
        ("Território sintético B", 2, 0, 0, 0),
        ("Território sintético C", 2, 1, 0, 1),
    ]
    assert [
        (item.candidate_count, item.candidates_with_opportunity)
        for item in distribution
    ] == [(2, 2), (2, 2), (2, 1)]


def test_availability_profile_summarizes_compatible_people_and_pairs() -> None:
    slots, candidates = load_demo_data()

    profile = calculate_availability_profile(slots, candidates)

    assert [
        (
            item.service,
            item.appointment_date,
            item.period,
            item.unit_id,
            item.slot_count,
            item.candidates_with_availability,
            item.compatible_pairs,
        )
        for item in profile
    ] == [
        ("Cardiologia", "2026-11-12", "Manhã", "UNIDADE-SINTÉTICA", 1, 2, 2),
        ("Cardiologia", "2026-11-13", "Tarde", "UNIDADE-SINTÉTICA", 1, 3, 3),
        ("Oftalmologia", "2026-11-12", "Tarde", "UNIDADE-SINTÉTICA", 1, 1, 1),
    ]


def test_group_distribution_keeps_groups_without_eligible_opportunities() -> None:
    slots, candidates = load_demo_data()
    incompatible_candidates = [
        Candidate(
            candidate_id=candidate.candidate_id,
            display_name=candidate.display_name,
            service="Serviço incompatível",
            synthetic_area=candidate.synthetic_area,
            available_dates=candidate.available_dates,
            available_periods=candidate.available_periods,
            queue_position=candidate.queue_position,
        )
        for candidate in candidates
    ]

    distribution = calculate_group_distribution(
        slots,
        incompatible_candidates,
        {},
    )

    assert [item.synthetic_area for item in distribution] == [
        "Território sintético A",
        "Território sintético B",
        "Território sintético C",
    ]
    assert all(item.candidate_count == 2 for item in distribution)
    assert all(item.eligible_opportunities == 0 for item in distribution)
    assert all(item.offer_per_eligible_opportunity_rate is None for item in distribution)
