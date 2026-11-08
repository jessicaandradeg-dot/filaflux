from dataclasses import dataclass
from statistics import mean, median

from vaga_viva.optimization import allocate_multicriteria
from vaga_viva.policy_simulation import (
    PolicyResult,
    allocate_in_batch,
    allocate_sequentially,
    generate_synthetic_scenario,
)


@dataclass(frozen=True)
class PolicyImpactSummary:
    policy_name: str
    mean_filled_slots: float
    median_filled_slots: float
    minimum_filled_slots: int
    maximum_filled_slots: int
    mean_fill_rate: float
    scenarios_with_maximum_fill_rate: float
    scenarios_with_more_fills_than_sequential: float | None


@dataclass(frozen=True)
class ImpactSimulationResult:
    seed: int
    replication_count: int
    slot_count: int
    candidate_count: int
    summaries: tuple[PolicyImpactSummary, ...]


def simulate_policy_impact(
    *,
    seed: int,
    replication_count: int,
    slot_count: int,
    candidate_count: int,
) -> ImpactSimulationResult:
    """Compare allocation policies over reproducible, synthetic scenarios."""
    if replication_count < 1:
        raise ValueError("replication_count must be at least 1.")

    policy_results: dict[str, list[PolicyResult]] = {
        "Fila sequencial": [],
        "Lote máximo": [],
        "Multicritério": [],
    }

    for replication in range(replication_count):
        scenario = generate_synthetic_scenario(
            seed=seed + replication,
            slot_count=slot_count,
            candidate_count=candidate_count,
        )
        policy_results["Fila sequencial"].append(
            allocate_sequentially(scenario.slots, scenario.candidates)
        )
        policy_results["Lote máximo"].append(
            allocate_in_batch(scenario.slots, scenario.candidates)
        )
        policy_results["Multicritério"].append(
            allocate_multicriteria(scenario.slots, scenario.candidates)
        )

    maximum_fills_by_replication = [
        max(results[replication].filled_slot_count for results in policy_results.values())
        for replication in range(replication_count)
    ]
    sequential_fills = [
        result.filled_slot_count
        for result in policy_results["Fila sequencial"]
    ]

    summaries = []
    for policy_name, results in policy_results.items():
        filled_counts = [result.filled_slot_count for result in results]
        summaries.append(
            PolicyImpactSummary(
                policy_name=policy_name,
                mean_filled_slots=mean(filled_counts),
                median_filled_slots=median(filled_counts),
                minimum_filled_slots=min(filled_counts),
                maximum_filled_slots=max(filled_counts),
                mean_fill_rate=mean(filled / slot_count for filled in filled_counts),
                scenarios_with_maximum_fill_rate=sum(
                    filled == maximum
                    for filled, maximum in zip(
                        filled_counts,
                        maximum_fills_by_replication,
                    )
                )
                / replication_count,
                scenarios_with_more_fills_than_sequential=(
                    None
                    if policy_name == "Fila sequencial"
                    else sum(
                        filled > sequential
                        for filled, sequential in zip(
                            filled_counts,
                            sequential_fills,
                        )
                    )
                    / replication_count
                ),
            )
        )

    return ImpactSimulationResult(
        seed=seed,
        replication_count=replication_count,
        slot_count=slot_count,
        candidate_count=candidate_count,
        summaries=tuple(summaries),
    )
