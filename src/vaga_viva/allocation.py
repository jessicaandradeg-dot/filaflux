from collections.abc import Collection, Iterable

from vaga_viva.models import Candidate, CancelledSlot, OfferSuggestion


def suggest_candidates(
    slot: CancelledSlot,
    candidates: Iterable[Candidate],
    unavailable_candidate_ids: Collection[str] = (),
) -> list[OfferSuggestion]:
    """Return compatible candidates in their existing queue order.

    Queue order is provided by the service; this function does not infer or
    change clinical priority.
    """
    suggestions: list[OfferSuggestion] = []

    for candidate in candidates:
        if candidate.candidate_id in unavailable_candidate_ids:
            continue
        if candidate.service != slot.service:
            continue
        if slot.appointment_date not in candidate.available_dates:
            continue
        if slot.period not in candidate.available_periods:
            continue
        if not candidate.accessibility_needs.issubset(slot.accessibility_features):
            continue

        reasons = [
            f"Serviço compatível: {slot.service}",
            f"Disponibilidade confirmada: {slot.appointment_date:%d/%m/%Y}, "
            f"{slot.period.lower()}",
            f"Posição atual na fila: {candidate.queue_position}",
        ]
        if candidate.accessibility_needs:
            reasons.append(
                "Recursos de acessibilidade compatíveis: "
                + ", ".join(sorted(candidate.accessibility_needs))
            )
        suggestions.append(
            OfferSuggestion(
                candidate=candidate,
                reasons=tuple(reasons),
            )
        )

    return sorted(suggestions, key=lambda suggestion: suggestion.candidate.queue_position)
