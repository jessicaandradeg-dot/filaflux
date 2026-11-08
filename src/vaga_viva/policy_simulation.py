import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from vaga_viva.allocation import suggest_candidates
from vaga_viva.models import Candidate, CancelledSlot


@dataclass(frozen=True)
class SyntheticScenario:
    seed: int
    slots: tuple[CancelledSlot, ...]
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class PolicyResult:
    assignments: Mapping[str, str]
    eligible_pair_counts_by_area: Mapping[str, int]
    slot_count: int
    total_queue_position: int = 0
    preference_mismatches: int = 0

    @property
    def filled_slot_count(self) -> int:
        return len(self.assignments)

    @property
    def unfilled_slot_count(self) -> int:
        return self.slot_count - self.filled_slot_count

    @property
    def offer_count(self) -> int:
        return len(self.assignments)


def generate_synthetic_scenario(
    seed: int,
    slot_count: int = 10,
    candidate_count: int = 18,
) -> SyntheticScenario:
    if slot_count < 1:
        raise ValueError("slot_count must be at least 1.")
    if candidate_count < 1:
        raise ValueError("candidate_count must be at least 1.")

    rng = random.Random(seed)
    services = ("Cardiologia", "Oftalmologia", "Clínica médica")
    periods = ("Manhã", "Tarde")
    units = ("UNIDADE-SIM-1", "UNIDADE-SIM-2", "UNIDADE-SIM-3")
    accessibility_features = ("rota_acessivel", "banheiro_acessivel")
    areas = (
        "Território sintético A",
        "Território sintético B",
        "Território sintético C",
    )
    start_date = date(2026, 11, 12)

    slots = [
        CancelledSlot(
            slot_id=f"SIM-{index + 1:03d}",
            service=rng.choice(services),
            appointment_date=start_date + timedelta(days=rng.randrange(7)),
            period=rng.choice(periods),
            cancellation_source=rng.choice(("Serviço", "Paciente")),
            unit_id=rng.choice(units),
            accessibility_features=frozenset(
                rng.sample(
                    accessibility_features,
                    k=rng.randint(0, len(accessibility_features)),
                )
            ),
        )
        for index in range(slot_count)
    ]

    slots_by_service: dict[str, list[CancelledSlot]] = defaultdict(list)
    for slot in slots:
        slots_by_service[slot.service].append(slot)

    service_queue_positions: dict[str, int] = defaultdict(int)
    candidates: list[Candidate] = []
    available_services = tuple(slots_by_service)

    for index in range(candidate_count):
        service = rng.choice(available_services)
        service_slots = slots_by_service[service]
        available_dates = set(
            rng.sample(
                sorted({slot.appointment_date for slot in service_slots}),
                k=rng.randint(1, len({slot.appointment_date for slot in service_slots})),
            )
        )
        available_periods = set(
            rng.sample(
                sorted({slot.period for slot in service_slots}),
                k=rng.randint(1, len({slot.period for slot in service_slots})),
            )
        )
        service_queue_positions[service] += 1
        preferred_periods = frozenset(
            rng.sample(
                sorted(available_periods),
                k=rng.randint(0, len(available_periods)),
            )
        )
        preferred_unit_ids = frozenset(
            rng.sample(
                units,
                k=rng.randint(0, len(units)),
            )
        )
        accessibility_needs = frozenset(
            rng.sample(
                accessibility_features,
                k=rng.randint(0, len(accessibility_features)),
            )
        )
        candidates.append(
            Candidate(
                candidate_id=f"SINT-SIM-{index + 1:03d}",
                display_name=f"Pessoa sintética {index + 1:03d}",
                service=service,
                synthetic_area=rng.choice(areas),
                available_dates=frozenset(available_dates),
                available_periods=frozenset(available_periods),
                queue_position=service_queue_positions[service],
                preferred_periods=preferred_periods,
                preferred_unit_ids=preferred_unit_ids,
                accessibility_needs=accessibility_needs,
                baseline_appointment_date=max(
                    slot.appointment_date for slot in slots
                )
                + timedelta(days=rng.randint(14, 60)),
            )
        )

    return SyntheticScenario(
        seed=seed,
        slots=tuple(slots),
        candidates=tuple(candidates),
    )


def _eligible_pair_counts_by_area(
    slots: Sequence[CancelledSlot],
    candidates: Sequence[Candidate],
) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for slot in slots:
        for suggestion in suggest_candidates(slot, candidates):
            counts[suggestion.candidate.synthetic_area] += 1
    return dict(sorted(counts.items()))


def allocate_sequentially(
    slots: Sequence[CancelledSlot],
    candidates: Sequence[Candidate],
) -> PolicyResult:
    assignments: dict[str, str] = {}
    used_candidate_ids: set[str] = set()

    for slot in slots:
        suggestions = suggest_candidates(
            slot,
            candidates,
            unavailable_candidate_ids=used_candidate_ids,
        )
        if suggestions:
            candidate_id = suggestions[0].candidate.candidate_id
            assignments[slot.slot_id] = candidate_id
            used_candidate_ids.add(candidate_id)

    return PolicyResult(
        assignments=dict(assignments),
        eligible_pair_counts_by_area=_eligible_pair_counts_by_area(slots, candidates),
        slot_count=len(slots),
    )


def allocate_in_batch(
    slots: Sequence[CancelledSlot],
    candidates: Sequence[Candidate],
) -> PolicyResult:
    eligible_by_slot = {
        slot.slot_id: [
            suggestion.candidate.candidate_id
            for suggestion in suggest_candidates(slot, candidates)
        ]
        for slot in slots
    }
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    slot_by_id = {slot.slot_id: slot for slot in slots}
    candidate_to_slot: dict[str, str] = {}
    slot_to_candidate: dict[str, str] = {}

    ordered_slot_ids = sorted(
        eligible_by_slot,
        key=lambda slot_id: (
            len(eligible_by_slot[slot_id]),
            slot_by_id[slot_id].appointment_date,
            slot_by_id[slot_id].period,
            slot_id,
        ),
    )

    def assign(slot_id: str, visited_candidates: set[str]) -> bool:
        candidate_ids = sorted(
            eligible_by_slot[slot_id],
            key=lambda candidate_id: (
                candidate_by_id[candidate_id].queue_position,
                candidate_id,
            ),
        )
        for candidate_id in candidate_ids:
            if candidate_id in visited_candidates:
                continue
            visited_candidates.add(candidate_id)
            current_slot_id = candidate_to_slot.get(candidate_id)
            if current_slot_id is None or assign(current_slot_id, visited_candidates):
                candidate_to_slot[candidate_id] = slot_id
                slot_to_candidate[slot_id] = candidate_id
                return True
        return False

    for slot_id in ordered_slot_ids:
        assign(slot_id, set())

    return PolicyResult(
        assignments=dict(slot_to_candidate),
        eligible_pair_counts_by_area=_eligible_pair_counts_by_area(slots, candidates),
        slot_count=len(slots),
    )


def summarize_policy_results(
    result: PolicyResult,
    candidates: Sequence[Candidate],
) -> list[dict[str, int | str | None]]:
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    offers_by_area: dict[str, int] = defaultdict(int)
    for candidate_id in result.assignments.values():
        offers_by_area[candidate_by_id[candidate_id].synthetic_area] += 1

    all_areas = sorted(
        set(result.eligible_pair_counts_by_area) | set(offers_by_area)
    )
    return [
        {
            "Grupo fictício": area,
            "Pares elegíveis": result.eligible_pair_counts_by_area.get(area, 0),
            "Vagas alocadas": offers_by_area[area],
            "Alocadas / pares elegíveis": (
                offers_by_area[area] / result.eligible_pair_counts_by_area[area]
                if result.eligible_pair_counts_by_area.get(area, 0)
                else None
            ),
        }
        for area in all_areas
    ]
