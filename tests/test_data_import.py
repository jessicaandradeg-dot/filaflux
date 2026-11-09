import pytest

from filaflux.data_import import ScenarioImportError, parse_scenario_csvs
from filaflux.optimization import allocate_multicriteria


def build_csvs(
    *,
    slot_rows: str = (
        "slot_id,service,appointment_date,period,cancellation_source,unit_id,"
        "accessibility_features\n"
        "CANCEL-001,Cardiologia,2026-11-12,Manhã,Paciente,UNIDADE-1,"
        "rota_acessivel\n"
    ),
    candidate_rows: str = (
        "candidate_id,service,queue_position,available_dates,available_periods,"
        "preferred_unit_ids,accessibility_needs\n"
        "PSEUDO-001,Cardiologia,1,2026-11-12|2026-11-13,Manhã|Tarde,"
        "UNIDADE-1,rota_acessivel\n"
    ),
) -> tuple[bytes, bytes]:
    return slot_rows.encode(), candidate_rows.encode()


def test_parse_scenario_csvs_builds_minimized_domain_objects() -> None:
    slots_csv, candidates_csv = build_csvs()

    slots, candidates = parse_scenario_csvs(slots_csv, candidates_csv)

    assert len(slots) == 1
    assert slots[0].slot_id == "CANCEL-001"
    assert slots[0].unit_id == "UNIDADE-1"
    assert slots[0].accessibility_features == frozenset({"rota_acessivel"})
    assert candidates[0].candidate_id == "PSEUDO-001"
    assert candidates[0].display_name == "PSEUDO-001"
    assert candidates[0].queue_position == 1
    assert candidates[0].synthetic_area == "Não informado"
    assert candidates[0].baseline_appointment_date is None
    result = allocate_multicriteria(slots, candidates)
    assert result.assignments == {"CANCEL-001": "PSEUDO-001"}


def test_rejects_direct_identifier_headers() -> None:
    slots_csv, candidates_csv = build_csvs(
        candidate_rows=(
            "candidate_id,name,service,queue_position,available_dates,"
            "available_periods\n"
            "PSEUDO-001,Nome,Cardiologia,1,2026-11-12,Manhã\n"
        ),
    )

    with pytest.raises(ScenarioImportError, match="coluna identificável"):
        parse_scenario_csvs(slots_csv, candidates_csv)


def test_rejects_unknown_columns_instead_of_importing_extra_data() -> None:
    slots_csv, candidates_csv = build_csvs(
        candidate_rows=(
            "candidate_id,service,queue_position,available_dates,"
            "available_periods,notes\n"
            "PSEUDO-001,Cardiologia,1,2026-11-12,Manhã,texto\n"
        ),
    )

    with pytest.raises(ScenarioImportError, match="Colunas não reconhecidas"):
        parse_scenario_csvs(slots_csv, candidates_csv)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("appointment_date", "12/11/2026", "AAAA-MM-DD"),
        ("period", "Noite", "Manhã ou Tarde"),
        ("cancellation_source", "Sistema", "Serviço ou Paciente"),
    ],
)
def test_rejects_invalid_slot_values(
    field: str,
    value: str,
    message: str,
) -> None:
    slot_rows = (
        "slot_id,service,appointment_date,period,cancellation_source,unit_id\n"
        f"CANCEL-001,Cardiologia,2026-11-12,Manhã,Paciente,UNIDADE-1\n"
    )
    slot_rows = slot_rows.replace(
        {
            "appointment_date": "2026-11-12",
            "period": "Manhã",
            "cancellation_source": "Paciente",
        }[field],
        value,
        1,
    )
    slots_csv, candidates_csv = build_csvs(slot_rows=slot_rows)

    with pytest.raises(ScenarioImportError, match=message):
        parse_scenario_csvs(slots_csv, candidates_csv)


def test_rejects_duplicate_candidate_ids() -> None:
    slots_csv, candidates_csv = build_csvs(
        candidate_rows=(
            "candidate_id,service,queue_position,available_dates,"
            "available_periods\n"
            "PSEUDO-001,Cardiologia,1,2026-11-12,Manhã\n"
            "PSEUDO-001,Cardiologia,2,2026-11-12,Tarde\n"
        ),
    )

    with pytest.raises(ScenarioImportError, match="duplicado"):
        parse_scenario_csvs(slots_csv, candidates_csv)


def test_rejects_upload_larger_than_one_megabyte() -> None:
    _, candidates_csv = build_csvs()

    with pytest.raises(ScenarioImportError, match="1 MB"):
        parse_scenario_csvs(b"x" * 1_000_001, candidates_csv)


def test_rejects_more_than_thirty_slots() -> None:
    slot_rows = (
        "slot_id,service,appointment_date,period,cancellation_source,unit_id\n"
        + "".join(
            f"CANCEL-{index},Cardiologia,2026-11-12,Manhã,Paciente,UNIDADE-1\n"
            for index in range(31)
        )
    )
    slots_csv, candidates_csv = build_csvs(slot_rows=slot_rows)

    with pytest.raises(ScenarioImportError, match="no máximo 30"):
        parse_scenario_csvs(slots_csv, candidates_csv)


def test_rejects_more_than_sixty_candidates() -> None:
    candidate_rows = (
        "candidate_id,service,queue_position,available_dates,"
        "available_periods\n"
        + "".join(
            f"PSEUDO-{index},Cardiologia,{index},2026-11-12,Manhã\n"
            for index in range(1, 62)
        )
    )
    slots_csv, candidates_csv = build_csvs(candidate_rows=candidate_rows)

    with pytest.raises(ScenarioImportError, match="no máximo 60"):
        parse_scenario_csvs(slots_csv, candidates_csv)
