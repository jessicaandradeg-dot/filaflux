from datetime import date

from vaga_viva.models import Candidate, CancelledSlot


def load_demo_data() -> tuple[list[CancelledSlot], list[Candidate]]:
    """Build deterministic, fictional data for the public demo."""
    appointment_dates = {
        date(2026, 11, 12),
        date(2026, 11, 13),
    }

    slots = [
        CancelledSlot(
            slot_id="VAGA-001",
            service="Cardiologia",
            appointment_date=date(2026, 11, 12),
            period="Manhã",
            cancellation_source="Serviço",
        ),
        CancelledSlot(
            slot_id="VAGA-002",
            service="Oftalmologia",
            appointment_date=date(2026, 11, 12),
            period="Tarde",
            cancellation_source="Paciente",
        ),
        CancelledSlot(
            slot_id="VAGA-003",
            service="Cardiologia",
            appointment_date=date(2026, 11, 13),
            period="Tarde",
            cancellation_source="Serviço",
        ),
    ]

    candidates = [
        Candidate(
            candidate_id="SINT-001",
            display_name="Pessoa sintética 001",
            service="Cardiologia",
            synthetic_area="Território sintético A",
            available_dates=frozenset({date(2026, 11, 12)}),
            available_periods=frozenset({"Manhã", "Tarde"}),
            queue_position=1,
        ),
        Candidate(
            candidate_id="SINT-002",
            display_name="Pessoa sintética 002",
            service="Cardiologia",
            synthetic_area="Território sintético B",
            available_dates=frozenset(appointment_dates),
            available_periods=frozenset({"Tarde"}),
            queue_position=2,
        ),
        Candidate(
            candidate_id="SINT-003",
            display_name="Pessoa sintética 003",
            service="Oftalmologia",
            synthetic_area="Território sintético A",
            available_dates=frozenset(appointment_dates),
            available_periods=frozenset({"Tarde"}),
            queue_position=1,
        ),
        Candidate(
            candidate_id="SINT-004",
            display_name="Pessoa sintética 004",
            service="Cardiologia",
            synthetic_area="Território sintético B",
            available_dates=frozenset({date(2026, 11, 13)}),
            available_periods=frozenset({"Tarde"}),
            queue_position=3,
        ),
        Candidate(
            candidate_id="SINT-005",
            display_name="Pessoa sintética 005",
            service="Oftalmologia",
            synthetic_area="Território sintético C",
            available_dates=frozenset({date(2026, 11, 12)}),
            available_periods=frozenset({"Manhã"}),
            queue_position=2,
        ),
        Candidate(
            candidate_id="SINT-006",
            display_name="Pessoa sintética 006",
            service="Cardiologia",
            synthetic_area="Território sintético C",
            available_dates=frozenset(appointment_dates),
            available_periods=frozenset({"Manhã", "Tarde"}),
            queue_position=4,
        ),
    ]

    return slots, candidates
