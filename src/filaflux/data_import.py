import csv
import io
import re
from datetime import date
from typing import Literal

from filaflux.models import Candidate, CancelledSlot, TimePeriod


MAX_UPLOAD_BYTES = 1_000_000
MAX_SLOT_ROWS = 30
MAX_CANDIDATE_ROWS = 60

_SLOT_REQUIRED_FIELDS = {
    "slot_id",
    "service",
    "appointment_date",
    "period",
    "cancellation_source",
    "unit_id",
}
_SLOT_OPTIONAL_FIELDS = {"accessibility_features"}
_CANDIDATE_REQUIRED_FIELDS = {
    "candidate_id",
    "service",
    "queue_position",
    "available_dates",
    "available_periods",
}
_CANDIDATE_OPTIONAL_FIELDS = {
    "preferred_unit_ids",
    "accessibility_needs",
}
_FORBIDDEN_HEADERS = {
    "address",
    "birthdate",
    "cns",
    "cpf",
    "diagnosis",
    "diagnostico",
    "dob",
    "email",
    "name",
    "nome",
    "phone",
    "telefone",
}
_PERIODS: dict[str, TimePeriod] = {"Manhã": "Manhã", "Tarde": "Tarde"}
_CANCELLATION_SOURCES: dict[
    str,
    Literal["Serviço", "Paciente"],
] = {
    "Serviço": "Serviço",
    "Paciente": "Paciente",
}


class ScenarioImportError(ValueError):
    """Raised when an uploaded CSV does not match the safe scenario format."""


def _read_csv(
    content: bytes,
    *,
    label: str,
    required_fields: set[str],
    optional_fields: set[str],
    max_rows: int,
) -> list[dict[str, str]]:
    if not content:
        raise ScenarioImportError(f"O arquivo de {label} está vazio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ScenarioImportError(
            f"O arquivo de {label} excede o limite de 1 MB."
        )

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ScenarioImportError(
            f"O arquivo de {label} precisa estar codificado em UTF-8."
        ) from error

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ScenarioImportError(f"O arquivo de {label} não tem cabeçalho.")

    headers = [header.strip() for header in reader.fieldnames]
    normalized_headers = [header.lower() for header in headers]
    if len(normalized_headers) != len(set(normalized_headers)):
        raise ScenarioImportError(
            f"O arquivo de {label} contém nomes de coluna repetidos."
        )
    if any(
        re.search(r"[a-z]", header) and header in _FORBIDDEN_HEADERS
        for header in normalized_headers
    ):
        raise ScenarioImportError(
            f"O arquivo de {label} inclui uma coluna identificável. "
            "Remova nomes, documentos, contato e dados clínicos."
        )

    allowed_fields = required_fields | optional_fields
    unknown_headers = set(normalized_headers) - allowed_fields
    missing_headers = required_fields - set(normalized_headers)
    if unknown_headers:
        raise ScenarioImportError(
            f"Colunas não reconhecidas em {label}: "
            f"{', '.join(sorted(unknown_headers))}."
        )
    if missing_headers:
        raise ScenarioImportError(
            f"Colunas obrigatórias ausentes em {label}: "
            f"{', '.join(sorted(missing_headers))}."
        )

    rows: list[dict[str, str]] = []
    for row_number, raw_row in enumerate(reader, start=2):
        if None in raw_row:
            raise ScenarioImportError(
                f"A linha {row_number} de {label} tem campos extras."
            )
        row = {
            header.strip().lower(): (value or "").strip()
            for header, value in raw_row.items()
            if header is not None
        }
        if not any(row.values()):
            continue
        rows.append(row)
        if len(rows) > max_rows:
            raise ScenarioImportError(
                f"O arquivo de {label} pode conter no máximo {max_rows} linhas."
            )

    if not rows:
        raise ScenarioImportError(f"O arquivo de {label} não contém registros.")
    return rows


def _required_value(row: dict[str, str], field: str, row_number: int) -> str:
    value = row.get(field, "")
    if not value:
        raise ScenarioImportError(
            f"Preencha '{field}' na linha {row_number}."
        )
    return value


def _split_values(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split("|") if item.strip())


def _parse_periods(value: str, row_number: int) -> frozenset[TimePeriod]:
    periods = _split_values(value)
    if not periods or not periods.issubset(_PERIODS):
        raise ScenarioImportError(
            f"Use apenas Manhã e/ou Tarde em 'available_periods' "
            f"na linha {row_number}."
        )
    return frozenset(_PERIODS[period] for period in periods)


def _parse_dates(value: str, row_number: int) -> frozenset[date]:
    try:
        dates = frozenset(date.fromisoformat(item) for item in _split_values(value))
    except ValueError as error:
        raise ScenarioImportError(
            f"Use datas no formato AAAA-MM-DD em 'available_dates' "
            f"na linha {row_number}."
        ) from error
    if not dates:
        raise ScenarioImportError(
            f"Preencha 'available_dates' na linha {row_number}."
        )
    return dates


def parse_scenario_csvs(
    slots_csv: bytes,
    candidates_csv: bytes,
) -> tuple[tuple[CancelledSlot, ...], tuple[Candidate, ...]]:
    """Parse minimized, pseudonymized operational data without persisting it."""
    slot_rows = _read_csv(
        slots_csv,
        label="vagas",
        required_fields=_SLOT_REQUIRED_FIELDS,
        optional_fields=_SLOT_OPTIONAL_FIELDS,
        max_rows=MAX_SLOT_ROWS,
    )
    candidate_rows = _read_csv(
        candidates_csv,
        label="fila",
        required_fields=_CANDIDATE_REQUIRED_FIELDS,
        optional_fields=_CANDIDATE_OPTIONAL_FIELDS,
        max_rows=MAX_CANDIDATE_ROWS,
    )

    slots: list[CancelledSlot] = []
    seen_slot_ids: set[str] = set()
    for row_number, row in enumerate(slot_rows, start=2):
        slot_id = _required_value(row, "slot_id", row_number)
        if slot_id in seen_slot_ids:
            raise ScenarioImportError(f"Vaga duplicada na linha {row_number}.")
        seen_slot_ids.add(slot_id)

        try:
            appointment_date = date.fromisoformat(
                _required_value(row, "appointment_date", row_number)
            )
        except ValueError as error:
            raise ScenarioImportError(
                f"Use AAAA-MM-DD em 'appointment_date' na linha {row_number}."
            ) from error

        period_value = _required_value(row, "period", row_number)
        period = _PERIODS.get(period_value)
        if period is None:
            raise ScenarioImportError(
                f"Use Manhã ou Tarde em 'period' na linha {row_number}."
            )
        cancellation_source_value = _required_value(
            row,
            "cancellation_source",
            row_number,
        )
        cancellation_source = _CANCELLATION_SOURCES.get(
            cancellation_source_value
        )
        if cancellation_source is None:
            raise ScenarioImportError(
                f"Use Serviço ou Paciente em 'cancellation_source' "
                f"na linha {row_number}."
            )

        slots.append(
            CancelledSlot(
                slot_id=slot_id,
                service=_required_value(row, "service", row_number),
                appointment_date=appointment_date,
                period=period,
                cancellation_source=cancellation_source,
                unit_id=_required_value(row, "unit_id", row_number),
                accessibility_features=_split_values(
                    row.get("accessibility_features", "")
                ),
            )
        )

    candidates: list[Candidate] = []
    seen_candidate_ids: set[str] = set()
    for row_number, row in enumerate(candidate_rows, start=2):
        candidate_id = _required_value(row, "candidate_id", row_number)
        if candidate_id in seen_candidate_ids:
            raise ScenarioImportError(
                f"Identificador pseudônimo duplicado na linha {row_number}."
            )
        seen_candidate_ids.add(candidate_id)

        try:
            queue_position = int(
                _required_value(row, "queue_position", row_number)
            )
        except ValueError as error:
            raise ScenarioImportError(
                f"'queue_position' precisa ser um inteiro na linha {row_number}."
            ) from error
        if queue_position < 1:
            raise ScenarioImportError(
                f"'queue_position' precisa ser maior que zero na linha {row_number}."
            )

        candidates.append(
            Candidate(
                candidate_id=candidate_id,
                display_name=candidate_id,
                service=_required_value(row, "service", row_number),
                synthetic_area="Não informado",
                available_dates=_parse_dates(
                    _required_value(row, "available_dates", row_number),
                    row_number,
                ),
                available_periods=_parse_periods(
                    _required_value(row, "available_periods", row_number),
                    row_number,
                ),
                queue_position=queue_position,
                preferred_unit_ids=_split_values(
                    row.get("preferred_unit_ids", "")
                ),
                accessibility_needs=_split_values(
                    row.get("accessibility_needs", "")
                ),
            )
        )

    return tuple(slots), tuple(candidates)
