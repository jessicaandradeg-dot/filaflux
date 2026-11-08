import pytest

from vaga_viva.allocation import suggest_candidates
from vaga_viva.demo_data import load_demo_data
from vaga_viva.workflow import (
    OfferAttempt,
    accepted_slot_ids,
    declined_candidate_ids,
    pending_offer,
    reserved_candidate_ids,
    transition_offer,
)


def test_pending_offer_can_be_declined_and_keeps_history() -> None:
    pending = OfferAttempt(slot_id="VAGA-001", candidate_id="SINT-001")

    declined = transition_offer(pending, "declined")

    assert declined.status == "declined"
    assert pending.status == "pending"


def test_declined_candidate_is_skipped_for_that_slot() -> None:
    history = {
        "VAGA-001": [
            OfferAttempt(
                slot_id="VAGA-001",
                candidate_id="SINT-001",
                status="declined",
            )
        ]
    }

    assert declined_candidate_ids(history, "VAGA-001") == {"SINT-001"}
    assert declined_candidate_ids(history, "VAGA-002") == set()


def test_next_compatible_candidate_is_suggested_after_decline() -> None:
    slots, candidates = load_demo_data()
    history = {
        slots[0].slot_id: [
            OfferAttempt(
                slot_id=slots[0].slot_id,
                candidate_id="SINT-001",
                status="declined",
            )
        ]
    }

    suggestions = suggest_candidates(
        slots[0],
        candidates,
        unavailable_candidate_ids=declined_candidate_ids(
            history,
            slots[0].slot_id,
        ),
    )

    assert [item.candidate.candidate_id for item in suggestions] == ["SINT-006"]


def test_pending_and_accepted_offers_reserve_candidates() -> None:
    history = {
        "VAGA-001": [
            OfferAttempt(slot_id="VAGA-001", candidate_id="SINT-001"),
            OfferAttempt(
                slot_id="VAGA-001",
                candidate_id="SINT-002",
                status="accepted",
            ),
            OfferAttempt(
                slot_id="VAGA-001",
                candidate_id="SINT-003",
                status="declined",
            ),
        ]
    }

    assert reserved_candidate_ids(history) == {"SINT-001", "SINT-002"}


def test_pending_offer_lookup_returns_only_unresolved_offer() -> None:
    attempts = [
        OfferAttempt(
            slot_id="VAGA-001",
            candidate_id="SINT-001",
            status="declined",
        ),
        OfferAttempt(slot_id="VAGA-001", candidate_id="SINT-002"),
    ]

    assert pending_offer(attempts, "VAGA-001") == attempts[1]


def test_accepted_offer_closes_the_slot() -> None:
    history = {
        "VAGA-001": [
            OfferAttempt(
                slot_id="VAGA-001",
                candidate_id="SINT-001",
                status="accepted",
            )
        ]
    }

    assert accepted_slot_ids(history) == {"VAGA-001"}


def test_final_offer_cannot_be_changed_again() -> None:
    accepted = OfferAttempt(
        slot_id="VAGA-001",
        candidate_id="SINT-001",
        status="accepted",
    )

    with pytest.raises(ValueError, match="Only a pending offer"):
        transition_offer(accepted, "declined")
