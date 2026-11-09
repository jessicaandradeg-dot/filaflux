from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal


OfferStatus = Literal["pending", "accepted", "declined"]
FinalOfferStatus = Literal["accepted", "declined"]


@dataclass(frozen=True)
class OfferAttempt:
    slot_id: str
    candidate_id: str
    status: OfferStatus = "pending"


def transition_offer(
    attempt: OfferAttempt,
    status: FinalOfferStatus,
) -> OfferAttempt:
    if attempt.status != "pending":
        raise ValueError("Only a pending offer can be accepted or declined.")
    if status not in {"accepted", "declined"}:
        raise ValueError(f"Unsupported final offer status: {status}")

    return OfferAttempt(
        slot_id=attempt.slot_id,
        candidate_id=attempt.candidate_id,
        status=status,
    )


def pending_offer(
    attempts: Sequence[OfferAttempt],
    slot_id: str,
) -> OfferAttempt | None:
    return next(
        (
            attempt
            for attempt in reversed(attempts)
            if attempt.slot_id == slot_id and attempt.status == "pending"
        ),
        None,
    )


def reserved_candidate_ids(
    history: Mapping[str, Sequence[OfferAttempt]],
) -> set[str]:
    return {
        attempt.candidate_id
        for attempts in history.values()
        for attempt in attempts
        if attempt.status in {"pending", "accepted"}
    }


def declined_candidate_ids(
    history: Mapping[str, Sequence[OfferAttempt]],
    slot_id: str,
) -> set[str]:
    return {
        attempt.candidate_id
        for attempt in history.get(slot_id, ())
        if attempt.status == "declined"
    }


def accepted_slot_ids(
    history: Mapping[str, Sequence[OfferAttempt]],
) -> set[str]:
    return {
        slot_id
        for slot_id, attempts in history.items()
        if any(attempt.status == "accepted" for attempt in attempts)
    }
