from dataclasses import dataclass
from datetime import date
from typing import Literal


TimePeriod = Literal["Manhã", "Tarde"]


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    display_name: str
    service: str
    synthetic_area: str
    available_dates: frozenset[date]
    available_periods: frozenset[TimePeriod]
    queue_position: int
    preferred_periods: frozenset[TimePeriod] = frozenset()
    preferred_unit_ids: frozenset[str] = frozenset()
    accessibility_needs: frozenset[str] = frozenset()
    baseline_appointment_date: date | None = None


@dataclass(frozen=True)
class CancelledSlot:
    slot_id: str
    service: str
    appointment_date: date
    period: TimePeriod
    cancellation_source: Literal["Serviço", "Paciente"]
    unit_id: str = "UNIDADE-SINTÉTICA"
    accessibility_features: frozenset[str] = frozenset()


@dataclass(frozen=True)
class OfferSuggestion:
    candidate: Candidate
    reasons: tuple[str, ...]
