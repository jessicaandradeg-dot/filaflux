import csv
import io
import re
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import TextIO
from urllib.parse import urlencode, urljoin, urlsplit


SOURCE_PAGE_URL = "https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos"
SOURCE_FILE_URL = (
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/"
    "Leitos_SUS/Leitos_csv_2025.zip"
)
RIO_MUNICIPALITY_CODE = "330455"
PILOT_YEAR = 2025
TABNET_SIA_SOURCE_URL = (
    "https://datasus.saude.gov.br/acesso-a-informacao/"
    "producao-ambulatorial-sia-sus/"
)
TABNET_SIA_DEFINITION_URL = (
    "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qarj.def"
)
TABNET_SIA_ACTION_URL = (
    "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sia/cnv/qarj.def"
)
RIO_MUNICIPALITY_NAME = "RIO DE JANEIRO"
_TABNET_MONTHS = (
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
)

_METRIC_COLUMNS = {
    "LEITOS_EXISTENTES": "existing_beds",
    "LEITOS_SUS": "sus_beds",
    "UTI_TOTAL_EXIST": "existing_icu_beds",
    "UTI_TOTAL_SUS": "sus_icu_beds",
}
_REQUIRED_COLUMNS = {
    "COMP",
    "UF",
    "CO_IBGE",
    "CNES",
    *_METRIC_COLUMNS,
}


class PublicDataError(RuntimeError):
    """Raised when the public source cannot be fetched or validated."""


@dataclass(frozen=True)
class MonthlyBedCapacity:
    competence: str
    establishment_count: int
    existing_beds: int
    sus_beds: int
    existing_icu_beds: int
    sus_icu_beds: int


@dataclass(frozen=True)
class MonthlyAmbulatoryProduction:
    competence: str
    approved_procedures: int


@dataclass(frozen=True)
class TabNetQueryMetadata:
    source_page_url: str
    definition_url: str
    result_csv_url: str
    retrieved_at: str
    municipality_code: str
    municipality_name: str
    year: int
    row_dimension: str
    column_dimension: str
    measure: str
    filters: str


@dataclass(frozen=True)
class SiaTabulation:
    monthly: tuple[MonthlyAmbulatoryProduction, ...]
    metadata: TabNetQueryMetadata


@dataclass
class _MonthlyAccumulator:
    establishment_ids: set[str]
    metrics: dict[str, int]


class _CsvLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.csv_links: list[str] = []
        self._active_href: str | None = None
        self._active_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if href:
            self._active_href = href
            self._active_text = []

    def handle_data(self, data: str) -> None:
        if self._active_href is not None:
            self._active_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._active_href is None:
            return
        if "copia como .csv" in "".join(self._active_text).strip().lower():
            self.csv_links.append(self._active_href)
        self._active_href = None
        self._active_text = []


def _normalize_municipality_code(value: str) -> str:
    digits = "".join(
        character
        for character in value.strip()
        if character.isascii() and character.isdigit()
    )
    return digits.zfill(6)


def _parse_count(value: str | None, column: str, competence: str) -> int:
    normalized = (value or "").strip()
    if not normalized.isascii() or not normalized.isdigit():
        raise ValueError(
            f"Valor inválido em {column} para a competência {competence}."
        )
    return int(normalized)


def parse_tabnet_sia_csv(
    csv_bytes: bytes,
    municipality_code: str = RIO_MUNICIPALITY_CODE,
    year: int = PILOT_YEAR,
) -> list[MonthlyAmbulatoryProduction]:
    try:
        content = csv_bytes.decode("latin-1")
        rows = list(csv.reader(io.StringIO(content), delimiter=";"))
    except (UnicodeError, csv.Error) as error:
        raise PublicDataError(
            f"Não foi possível ler o CSV agregado do TabNet: {error}"
        ) from error

    expected_headers = ["Município"] + [
        f"{year}/{month}" for month in _TABNET_MONTHS
    ] + ["Total"]
    header_indexes = [
        index
        for index, row in enumerate(rows)
        if row and row[0].strip().casefold() == "município"
    ]
    if len(header_indexes) != 1:
        raise PublicDataError(
            "A resposta do TabNet não contém um cabeçalho municipal único."
        )

    header_index = header_indexes[0]
    header = [cell.strip() for cell in rows[header_index]]
    if header != expected_headers:
        raise PublicDataError(
            "O cabeçalho do TabNet não contém exatamente os 12 meses "
            f"esperados de {year}."
        )

    normalized_municipality_code = _normalize_municipality_code(municipality_code)
    municipality_rows = [
        row
        for row in rows[header_index + 1 :]
        if row
        and row[0].strip()
        and _normalize_municipality_code(
            row[0].strip().split(maxsplit=1)[0]
        )
        == normalized_municipality_code
    ]
    if len(municipality_rows) != 1:
        raise PublicDataError(
            "A resposta do TabNet não contém uma linha única para o município "
            f"{normalized_municipality_code}."
        )

    municipality_row = municipality_rows[0]
    if len(municipality_row) != len(expected_headers):
        raise PublicDataError(
            "A linha municipal do TabNet não contém os 12 meses esperados."
        )

    monthly: list[MonthlyAmbulatoryProduction] = []
    for month_number, (month_label, value) in enumerate(
        zip(_TABNET_MONTHS, municipality_row[1:-1], strict=True),
        start=1,
    ):
        normalized_value = value.strip()
        if not normalized_value.isascii() or not normalized_value.isdigit():
            raise PublicDataError(
                f"Quantidade aprovada inválida em {year}/{month_label}."
            )
        monthly.append(
            MonthlyAmbulatoryProduction(
                competence=f"{year}{month_number:02d}",
                approved_procedures=int(normalized_value),
            )
        )

    total_value = municipality_row[-1].strip()
    if not total_value.isascii() or not total_value.isdigit():
        raise PublicDataError("O total anual do TabNet não é um inteiro válido.")
    if sum(item.approved_procedures for item in monthly) != int(total_value):
        raise PublicDataError(
            "A soma mensal do TabNet não confere com o total anual informado."
        )
    return monthly


def aggregate_hospital_beds_csv(
    csv_file: TextIO,
    municipality_code: str = RIO_MUNICIPALITY_CODE,
    year: int = PILOT_YEAR,
) -> list[MonthlyBedCapacity]:
    reader = csv.DictReader(csv_file, delimiter=";")
    if reader.fieldnames is None:
        raise ValueError("O arquivo CSV não contém cabeçalho.")

    missing_columns = _REQUIRED_COLUMNS.difference(reader.fieldnames)
    if missing_columns:
        raise ValueError(
            "Colunas obrigatórias ausentes no CSV: "
            + ", ".join(sorted(missing_columns))
        )

    monthly: dict[str, _MonthlyAccumulator] = defaultdict(
        lambda: _MonthlyAccumulator(
            establishment_ids=set(),
            metrics={column: 0 for column in _METRIC_COLUMNS.values()},
        )
    )
    normalized_municipality_code = _normalize_municipality_code(municipality_code)

    for row in reader:
        if (
            row.get("UF", "").strip() != "RJ"
            or _normalize_municipality_code(row.get("CO_IBGE", ""))
            != normalized_municipality_code
        ):
            continue

        competence = row.get("COMP", "").strip()
        match = re.fullmatch(r"(\d{4})(0[1-9]|1[0-2])", competence)
        if match is None:
            raise ValueError(f"Competência inválida no CSV: {competence!r}.")
        if int(match.group(1)) != year:
            continue

        establishment_id = row.get("CNES", "").strip()
        if not establishment_id:
            raise ValueError(
                f"Código CNES ausente na competência {competence}."
            )

        accumulator = monthly[competence]
        if establishment_id in accumulator.establishment_ids:
            raise ValueError(
                f"Registro CNES duplicado na competência {competence}."
            )
        accumulator.establishment_ids.add(establishment_id)

        for source_column, metric_name in _METRIC_COLUMNS.items():
            accumulator.metrics[metric_name] += _parse_count(
                row.get(source_column),
                source_column,
                competence,
            )

    expected_competences = {f"{year}{month:02d}" for month in range(1, 13)}
    missing_competences = expected_competences.difference(monthly)
    if missing_competences:
        raise ValueError(
            "A série municipal não contém todas as competências do ano. "
            "Ausentes: "
            + ", ".join(sorted(missing_competences))
        )

    return [
        MonthlyBedCapacity(
            competence=competence,
            establishment_count=len(accumulator.establishment_ids),
            **accumulator.metrics,
        )
        for competence, accumulator in sorted(monthly.items())
    ]


def parse_hospital_beds_zip(
    archive_bytes: bytes,
    municipality_code: str = RIO_MUNICIPALITY_CODE,
    year: int = PILOT_YEAR,
) -> list[MonthlyBedCapacity]:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            csv_names = [
                name for name in archive.namelist() if name.lower().endswith(".csv")
            ]
            if len(csv_names) != 1:
                raise ValueError(
                    "O ZIP deveria conter exatamente um arquivo CSV."
                )
            with archive.open(csv_names[0]) as binary_file:
                with io.TextIOWrapper(
                    binary_file,
                    encoding="latin-1",
                    newline="",
                ) as csv_file:
                    return aggregate_hospital_beds_csv(
                        csv_file,
                        municipality_code=municipality_code,
                        year=year,
                    )
    except (
        OSError,
        UnicodeError,
        csv.Error,
        ValueError,
        zipfile.BadZipFile,
    ) as error:
        raise PublicDataError(
            f"Não foi possível validar o arquivo público de leitos: {error}"
        ) from error


def fetch_rio_2025_bed_capacity(
    timeout: float = 60,
) -> list[MonthlyBedCapacity]:
    request = urllib.request.Request(
        SOURCE_FILE_URL,
        headers={"User-Agent": "FilaFlux/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            archive_bytes = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise PublicDataError(
            f"Falha ao baixar a fonte oficial de leitos: {error}"
        ) from error

    return parse_hospital_beds_zip(archive_bytes)


def _build_tabnet_sia_request_body(year: int) -> bytes:
    if year != PILOT_YEAR:
        raise ValueError(f"O TabNet está configurado para o ano {PILOT_YEAR}.")

    placeholder = "Digite o texto e ache f\u00e1cil"
    parameters: list[tuple[str, str]] = [
        ("Linha", "Munic\u00edpio"),
        ("Coluna", "Ano/m\u00eas_processamento"),
        ("Incremento", "Qtd.aprovada"),
    ]
    parameters.extend(
        ("Arquivos", f"qarj25{month:02d}.dbf")
        for month in range(12, 0, -1)
    )
    parameters.extend(
        [
            ("pesqmes1", placeholder),
            ("SMunic\u00edpio", "69"),
            ("pesqmes2", placeholder),
        ]
    )
    filters = (
        ("SRegi\u00e3o_de_Sa\u00fade_(CIR)", None),
        ("SMacrorregi\u00e3o_de_Sa\u00fade", None),
        ("SDivis\u00e3o_administ_estadual", None),
        ("SMicrorregi\u00e3o_IBGE", "pesqmes5"),
        ("SRegi\u00e3o_Metropolitana_-_RIDE", None),
        ("SProcedimento", "pesqmes7"),
        ("SGrupo_procedimento", None),
        ("SSubgrupo_proced.", "pesqmes9"),
        ("SForma_organiza\u00e7\u00e3o", "pesqmes10"),
        ("SComplexidade", None),
        ("SFinanciamento", None),
        ("SRubrica_FAEC", "pesqmes13"),
        ("SFonte_Or\u00e7ament\u00e1ria", None),
        ("SRegra_contratual", "pesqmes15"),
        ("SCar\u00e1ter_Atendiment", None),
        ("SGest\u00e3o", None),
        ("SDocumento_registro", None),
        ("SEsfera_administrat", "pesqmes19"),
        ("STipo_de_prestador", None),
        ("SNatureza_Jur\u00eddica", "pesqmes21"),
        ("SEsfera_Jur\u00eddica", "pesqmes22"),
        ("SAprova\u00e7\u00e3o_produ\u00e7\u00e3o", None),
        ("SProfissional_-_CBO", "pesqmes24"),
    )
    for filter_name, search_field in filters:
        if search_field is not None:
            parameters.append((search_field, placeholder))
        parameters.append((filter_name, "TODAS_AS_CATEGORIAS__"))
    parameters.extend([("formato", "table"), ("mostre", "Mostra")])
    return urlencode(parameters, encoding="latin-1").encode("ascii")


def _get_tabnet_csv_url(response_html: bytes) -> str:
    parser = _CsvLinkParser()
    parser.feed(response_html.decode("latin-1"))
    if len(parser.csv_links) != 1:
        raise PublicDataError(
            "A resposta do TabNet não contém um link único para exportação CSV."
        )

    csv_url = urljoin(TABNET_SIA_ACTION_URL, parser.csv_links[0])
    parsed_url = urlsplit(csv_url)
    if (
        parsed_url.scheme != "http"
        or parsed_url.hostname != "tabnet.datasus.gov.br"
        or not parsed_url.path.startswith("/csv/")
    ):
        raise PublicDataError("O TabNet retornou um endereço CSV inesperado.")
    return csv_url


def fetch_rio_2025_sia_tabulation(timeout: float = 60) -> SiaTabulation:
    request = urllib.request.Request(
        TABNET_SIA_ACTION_URL,
        data=_build_tabnet_sia_request_body(PILOT_YEAR),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": TABNET_SIA_DEFINITION_URL,
            "User-Agent": "FilaFlux/0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_html = response.read()
        csv_url = _get_tabnet_csv_url(response_html)
        csv_request = urllib.request.Request(
            csv_url,
            headers={"User-Agent": "FilaFlux/0.1"},
        )
        with urllib.request.urlopen(csv_request, timeout=timeout) as response:
            csv_bytes = response.read()
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError) as error:
        raise PublicDataError(
            f"Falha ao consultar a tabulação agregada do SIA/SUS: {error}"
        ) from error

    monthly = parse_tabnet_sia_csv(csv_bytes)
    return SiaTabulation(
        monthly=tuple(monthly),
        metadata=TabNetQueryMetadata(
            source_page_url=TABNET_SIA_SOURCE_URL,
            definition_url=TABNET_SIA_DEFINITION_URL,
            result_csv_url=csv_url,
            retrieved_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            municipality_code=RIO_MUNICIPALITY_CODE,
            municipality_name=RIO_MUNICIPALITY_NAME,
            year=PILOT_YEAR,
            row_dimension="Município do estabelecimento",
            column_dimension="Ano/mês de processamento",
            measure="Quantidade aprovada (Qtd.aprovada)",
            filters="Todos os demais filtros permanecem em todas as categorias.",
        ),
    )
