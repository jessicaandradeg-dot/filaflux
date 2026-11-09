import pytest

from filaflux.impact_simulation import simulate_policy_impact


def test_impact_simulation_is_reproducible() -> None:
    first = simulate_policy_impact(
        seed=15,
        replication_count=5,
        slot_count=6,
        candidate_count=8,
    )
    second = simulate_policy_impact(
        seed=15,
        replication_count=5,
        slot_count=6,
        candidate_count=8,
    )

    assert first == second
    assert first.replication_count == 5
    assert [summary.policy_name for summary in first.summaries] == [
        "Fila sequencial",
        "Lote máximo",
        "Multicritério",
    ]


def test_impact_simulation_compares_policy_fill_rates() -> None:
    result = simulate_policy_impact(
        seed=7,
        replication_count=8,
        slot_count=6,
        candidate_count=8,
    )
    summaries = {item.policy_name: item for item in result.summaries}

    assert (
        summaries["Lote máximo"].mean_filled_slots
        >= summaries["Fila sequencial"].mean_filled_slots
    )
    assert (
        summaries["Multicritério"].mean_filled_slots
        >= summaries["Fila sequencial"].mean_filled_slots
    )
    assert summaries["Fila sequencial"].scenarios_with_maximum_fill_rate <= 1
    assert (
        summaries["Lote máximo"].scenarios_with_more_fills_than_sequential
        is not None
    )


def test_impact_simulation_rejects_zero_replications() -> None:
    with pytest.raises(ValueError, match="replication_count"):
        simulate_policy_impact(
            seed=1,
            replication_count=0,
            slot_count=2,
            candidate_count=2,
        )
