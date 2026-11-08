from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from vaga_viva.allocation import suggest_candidates
from vaga_viva.models import Candidate, CancelledSlot
from vaga_viva.workflow import OfferAttempt, accepted_slot_ids


@dataclass(frozen=True)
class OperationalMetrics:
    slot_count: int
    filled_slot_count: int
    offer_count: int
    pending_count: int
    accepted_count: int
    declined_count: int
    fill_rate: float | None
    resolution_acceptance_rate: float | None
    mean_offers_per_filled_slot: float | None
    filled_by_cancellation_source: dict[str, tuple[int, int]]


@dataclass(frozen=True)
class GroupDistribution:
    synthetic_area: str
    candidate_count: int
    candidates_with_opportunity: int
    eligible_opportunities: int
    offers: int
    accepted: int
    declined: int
    pending: int
    offer_per_eligible_opportunity_rate: float | None


@dataclass(frozen=True)
class AvailabilityProfile:
    service: str
    appointment_date: str
    period: str
    unit_id: str
    slot_count: int
    candidates_with_availability: int
    compatible_pairs: int


@dataclass
class _AvailabilityAccumulator:
    slot_count: int = 0
    candidate_ids: set[str] = field(default_factory=set)
    compatible_pairs: int = 0


def calculate_operational_metrics(
    slots: Sequence[CancelledSlot],
    history: Mapping[str, Sequence[OfferAttempt]],
) -> OperationalMetrics:
    attempts = [attempt for slot_attempts in history.values() for attempt in slot_attempts]
    accepted_slots = accepted_slot_ids(history)
    resolved_count = sum(
        attempt.status in {"accepted", "declined"} for attempt in attempts
    )
    accepted_count = sum(attempt.status == "accepted" for attempt in attempts)
    filled_slot_count = sum(slot.slot_id in accepted_slots for slot in slots)
    offers_for_filled_slots = sum(
        len(history.get(slot.slot_id, ()))
        for slot in slots
        if slot.slot_id in accepted_slots
    )

    source_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for slot in slots:
        counts = source_counts[slot.cancellation_source]
        counts[0] += 1
        if slot.slot_id in accepted_slots:
            counts[1] += 1

    return OperationalMetrics(
        slot_count=len(slots),
        filled_slot_count=filled_slot_count,
        offer_count=len(attempts),
        pending_count=sum(attempt.status == "pending" for attempt in attempts),
        accepted_count=accepted_count,
        declined_count=sum(attempt.status == "declined" for attempt in attempts),
        fill_rate=(
            filled_slot_count / len(slots)
            if slots
            else None
        ),
        resolution_acceptance_rate=(
            accepted_count / resolved_count
            if resolved_count
            else None
        ),
        mean_offers_per_filled_slot=(
            offers_for_filled_slots / filled_slot_count
            if filled_slot_count
            else None
        ),
        filled_by_cancellation_source={
            source: (counts[1], counts[0])
            for source, counts in sorted(source_counts.items())
        },
    )


def calculate_group_distribution(
    slots: Sequence[CancelledSlot],
    candidates: Sequence[Candidate],
    history: Mapping[str, Sequence[OfferAttempt]],
) -> list[GroupDistribution]:
    eligible_opportunities: dict[str, int] = defaultdict(int)
    eligible_candidate_ids: dict[str, set[str]] = defaultdict(set)
    outcomes: dict[str, dict[str, int]] = defaultdict(
        lambda: {"offers": 0, "accepted": 0, "declined": 0, "pending": 0}
    )
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    candidate_counts: dict[str, int] = defaultdict(int)

    for candidate in candidates:
        candidate_counts[candidate.synthetic_area] += 1

    for slot in slots:
        for suggestion in suggest_candidates(slot, candidates):
            eligible_opportunities[suggestion.candidate.synthetic_area] += 1
            eligible_candidate_ids[suggestion.candidate.synthetic_area].add(
                suggestion.candidate.candidate_id
            )

    for attempts in history.values():
        for attempt in attempts:
            candidate = candidate_by_id[attempt.candidate_id]
            group_outcomes = outcomes[candidate.synthetic_area]
            group_outcomes["offers"] += 1
            group_outcomes[attempt.status] += 1

    all_areas = sorted(
        set(candidate_counts) | set(eligible_opportunities) | set(outcomes)
    )
    return [
        GroupDistribution(
            synthetic_area=area,
            candidate_count=candidate_counts[area],
            candidates_with_opportunity=len(eligible_candidate_ids[area]),
            eligible_opportunities=eligible_opportunities[area],
            offers=outcomes[area]["offers"],
            accepted=outcomes[area]["accepted"],
            declined=outcomes[area]["declined"],
            pending=outcomes[area]["pending"],
            offer_per_eligible_opportunity_rate=(
                outcomes[area]["offers"] / eligible_opportunities[area]
                if eligible_opportunities[area]
                else None
            ),
        )
        for area in all_areas
    ]


def calculate_availability_profile(
    slots: Sequence[CancelledSlot],
    candidates: Sequence[Candidate],
) -> list[AvailabilityProfile]:
    grouped: dict[tuple[str, str, str, str], _AvailabilityAccumulator] = {}

    for slot in slots:
        key = (
            slot.service,
            slot.appointment_date.isoformat(),
            slot.period,
            slot.unit_id,
        )
        group = grouped.setdefault(key, _AvailabilityAccumulator())
        group.slot_count += 1
        compatible_candidates = [
            suggestion.candidate.candidate_id
            for suggestion in suggest_candidates(slot, candidates)
        ]
        group.candidate_ids.update(compatible_candidates)
        group.compatible_pairs += len(compatible_candidates)

    return [
        AvailabilityProfile(
            service=service,
            appointment_date=appointment_date,
            period=period,
            unit_id=unit_id,
            slot_count=group.slot_count,
            candidates_with_availability=len(group.candidate_ids),
            compatible_pairs=group.compatible_pairs,
        )
        for (service, appointment_date, period, unit_id), group in sorted(
            grouped.items()
        )
    ]
