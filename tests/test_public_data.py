import csv
import io
import zipfile

import pytest

from filaflux.public_data import (
    MonthlyBedCapacity,
    MonthlyAmbulatoryProduction,
    PublicDataError,
    aggregate_hospital_beds_csv,
    parse_hospital_beds_zip,
    parse_tabnet_sia_csv,
)


HEADERS = [
    "COMP",
    "UF",
    "CO_IBGE",
    "CNES",
    "LEITOS_EXISTENTES",
    "LEITOS_SUS",
    "UTI_TOTAL_EXIST",
    "UTI_TOTAL_SUS",
    "NOME_ESTABELECIMENTO",
    "NO_EMAIL",
]


def build_csv_rows(
    *,
    omit_december: bool = False,
    duplicate_first_establishment: bool = False,
) -> list[dict[str, str]]:
    rows = []
    for month in range(1, 13):
        if omit_december and month == 12:
            continue
        rows.append(
            {
                "COMP": f"2025{month:02d}",
                "UF": "RJ",
                "CO_IBGE": "330455",
                "CNES": f"RJ-{month:02d}",
                "LEITOS_EXISTENTES": str(100 + month),
                "LEITOS_SUS": str(80 + month),
                "UTI_TOTAL_EXIST": str(20 + month),
                "UTI_TOTAL_SUS": str(10 + month),
                "NOME_ESTABELECIMENTO": "Dado sintético ignorado",
                "NO_EMAIL": "nao-usado@example.invalid",
            }
        )
        rows.append(
            {
                "COMP": f"2025{month:02d}",
                "UF": "RJ",
                "CO_IBGE": "330330",
                "CNES": f"OUTRO-{month:02d}",
                "LEITOS_EXISTENTES": "999",
                "LEITOS_SUS": "999",
                "UTI_TOTAL_EXIST": "99",
                "UTI_TOTAL_SUS": "99",
                "NOME_ESTABELECIMENTO": "Outro município",
                "NO_EMAIL": "nao-usado@example.invalid",
            }
        )

    if duplicate_first_establishment:
        rows.append(rows[0].copy())
    return rows


def serialize_csv(rows: list[dict[str, str]], headers: list[str] = HEADERS) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def test_aggregation_returns_only_municipal_monthly_summaries() -> None:
    csv_content = serialize_csv(build_csv_rows())

    result = aggregate_hospital_beds_csv(io.StringIO(csv_content))

    assert len(result) == 12
    assert result[0] == MonthlyBedCapacity(
        competence="202501",
        establishment_count=1,
        existing_beds=101,
        sus_beds=81,
        existing_icu_beds=21,
        sus_icu_beds=11,
    )
    assert result[-1] == MonthlyBedCapacity(
        competence="202512",
        establishment_count=1,
        existing_beds=112,
        sus_beds=92,
        existing_icu_beds=32,
        sus_icu_beds=22,
    )
    assert not hasattr(result[0], "establishment_name")


def test_aggregation_rejects_an_incomplete_year() -> None:
    csv_content = serialize_csv(build_csv_rows(omit_december=True))

    with pytest.raises(ValueError, match="202512"):
        aggregate_hospital_beds_csv(io.StringIO(csv_content))


def test_aggregation_rejects_duplicate_establishment_competence() -> None:
    csv_content = serialize_csv(
        build_csv_rows(duplicate_first_establishment=True)
    )

    with pytest.raises(ValueError, match="duplicado"):
        aggregate_hospital_beds_csv(io.StringIO(csv_content))


def test_aggregation_rejects_missing_required_columns() -> None:
    headers = [header for header in HEADERS if header != "CNES"]
    csv_content = ";".join(headers) + "\n"

    with pytest.raises(ValueError, match="CNES"):
        aggregate_hospital_beds_csv(io.StringIO(csv_content))


def test_zip_parser_aggregates_without_writing_source_rows() -> None:
    csv_content = serialize_csv(build_csv_rows()).encode("latin-1")
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, mode="w") as archive:
        archive.writestr("Leitos_2025.csv", csv_content)

    result = parse_hospital_beds_zip(archive_buffer.getvalue())

    assert len(result) == 12
    assert result[-1].sus_beds == 92


def test_zip_parser_surfaces_invalid_archives() -> None:
    with pytest.raises(PublicDataError, match="validar"):
        parse_hospital_beds_zip(b"not a zip file")


def build_tabnet_csv(
    *,
    municipality_code: str = "330455",
    omit_december: bool = False,
    total_adjustment: int = 0,
    first_month_value: str = "10",
) -> bytes:
    headers = ["Município"] + [
        f"2025/{month}"
        for month in (
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez",
        )
    ] + ["Total"]
    values = ["10"] * (11 if omit_december else 12)
    total = sum(int(value) for value in values) + total_adjustment
    values[0] = first_month_value
    rows = [
        ["Quantidade aprovada"],
        [],
        headers,
        [f"{municipality_code} RIO DE JANEIRO", *values, str(total)],
        ["Total", *values, str(total)],
    ]
    output = io.StringIO(newline="")
    csv.writer(output, delimiter=";").writerows(rows)
    return output.getvalue().encode("latin-1")


def test_tabnet_parser_returns_twelve_monthly_approved_counts() -> None:
    result = parse_tabnet_sia_csv(build_tabnet_csv())

    assert len(result) == 12
    assert result[0] == MonthlyAmbulatoryProduction(
        competence="202501",
        approved_procedures=10,
    )
    assert result[-1] == MonthlyAmbulatoryProduction(
        competence="202512",
        approved_procedures=10,
    )


def test_tabnet_parser_rejects_missing_month() -> None:
    with pytest.raises(PublicDataError, match="12 meses"):
        parse_tabnet_sia_csv(build_tabnet_csv(omit_december=True))


def test_tabnet_parser_rejects_missing_or_duplicate_municipality() -> None:
    with pytest.raises(PublicDataError, match="linha única"):
        parse_tabnet_sia_csv(
            build_tabnet_csv(municipality_code="330330")
        )

    rows = list(
        csv.reader(
            io.StringIO(build_tabnet_csv().decode("latin-1")),
            delimiter=";",
        )
    )
    rows.insert(4, rows[3].copy())
    output = io.StringIO(newline="")
    csv.writer(output, delimiter=";").writerows(rows)
    with pytest.raises(PublicDataError, match="linha única"):
        parse_tabnet_sia_csv(output.getvalue().encode("latin-1"))


def test_tabnet_parser_rejects_invalid_monthly_count() -> None:
    with pytest.raises(PublicDataError, match="inválida"):
        parse_tabnet_sia_csv(
            build_tabnet_csv(first_month_value="dez")
        )


def test_tabnet_parser_rejects_annual_total_mismatch() -> None:
    with pytest.raises(PublicDataError, match="não confere"):
        parse_tabnet_sia_csv(build_tabnet_csv(total_adjustment=1))


def test_tabnet_parser_rejects_unexpected_header() -> None:
    csv_content = build_tabnet_csv().decode("latin-1").replace(
        "2025/Jan", "2024/Jan", 1
    )

    with pytest.raises(PublicDataError, match="cabeçalho"):
        parse_tabnet_sia_csv(csv_content.encode("latin-1"))
