import streamlit as st

from vaga_viva.allocation import suggest_candidates
from vaga_viva.analytics import (
    calculate_availability_profile,
    calculate_group_distribution,
    calculate_operational_metrics,
)
from vaga_viva.demo_data import load_demo_data
from vaga_viva.impact_simulation import simulate_policy_impact
from vaga_viva.optimization import (
    allocate_multicriteria,
    potential_wait_days_avoided,
)
from vaga_viva.policy_simulation import (
    allocate_in_batch,
    allocate_sequentially,
    generate_synthetic_scenario,
    summarize_policy_results,
)
from vaga_viva.workflow import (
    FinalOfferStatus,
    OfferAttempt,
    accepted_slot_ids,
    declined_candidate_ids,
    pending_offer,
    reserved_candidate_ids,
    transition_offer,
)


st.set_page_config(
    page_title="Vaga Viva | Saúde & Bem-estar",
    page_icon="🩺",
    layout="wide",
)

slots, candidates = load_demo_data()

if "offer_history" not in st.session_state:
    st.session_state.offer_history = {}


def reset_demo() -> None:
    st.session_state.offer_history = {}


def update_offer_status(
    slot_id: str,
    attempt: OfferAttempt,
    status: FinalOfferStatus,
) -> None:
    history = dict(st.session_state.offer_history)
    attempts = list(history.get(slot_id, ()))
    attempt_index = attempts.index(attempt)
    attempts[attempt_index] = transition_offer(attempt, status)
    history[slot_id] = attempts
    st.session_state.offer_history = history


st.title("Vaga Viva")
st.subheader("Reaproveitamento transparente de vagas canceladas")
st.caption(
    "Demonstração com dados inteiramente sintéticos. A ferramenta sugere; "
    "a equipe responsável decide."
)

history = st.session_state.offer_history
all_attempts = [
    attempt for attempts in history.values() for attempt in attempts
]
accepted_slots = accepted_slot_ids(history)
pending_count = sum(attempt.status == "pending" for attempt in all_attempts)
accepted_count = sum(attempt.status == "accepted" for attempt in all_attempts)
declined_count = sum(attempt.status == "declined" for attempt in all_attempts)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Vagas canceladas no cenário", len(slots))
col2.metric("Ofertas pendentes", pending_count)
col3.metric("Ofertas aceitas", accepted_count)
col4.metric("Recusas registradas", declined_count)
st.caption(f"{len(slots) - len(accepted_slots)} vaga(s) ainda sem aceite.")

st.divider()
left, right = st.columns([1, 1.5])

with left:
    st.markdown("### Vagas disponíveis")
    for slot in slots:
        attempts = history.get(slot.slot_id, [])
        current_offer = pending_offer(attempts, slot.slot_id)
        if slot.slot_id in accepted_slots:
            status = "Vaga preenchida"
        elif current_offer is not None:
            status = f"Oferta pendente para {current_offer.candidate_id}"
        elif attempts:
            status = "Aguardando próxima oferta"
        else:
            status = "Aguardando análise"

        st.markdown(
            f"**{slot.slot_id} — {slot.service}**  \n"
            f"{slot.appointment_date:%d/%m/%Y} · {slot.period} · "
            f"cancelamento pelo(a) {slot.cancellation_source.lower()}  \n"
            f"_{status}_"
        )
        if attempts:
            with st.expander(f"Histórico de ofertas — {slot.slot_id}"):
                for attempt in attempts:
                    candidate = next(
                        item
                        for item in candidates
                        if item.candidate_id == attempt.candidate_id
                    )
                    status_label = {
                        "pending": "Pendente",
                        "accepted": "Aceita",
                        "declined": "Recusada",
                    }[attempt.status]
                    st.write(f"{candidate.display_name} — {status_label}")

with right:
    st.markdown("### Analisar uma vaga")
    available_slots = [slot for slot in slots if slot.slot_id not in accepted_slots]

    if not available_slots:
        st.success("Todas as vagas deste cenário foram preenchidas.")
    else:
        selected_slot_id = st.selectbox(
            "Selecione a vaga cancelada",
            options=[slot.slot_id for slot in available_slots],
            format_func=lambda slot_id: next(
                f"{slot_id} · {slot.service} · {slot.appointment_date:%d/%m} · {slot.period}"
                for slot in available_slots
                if slot.slot_id == slot_id
            ),
        )
        selected_slot = next(
            slot for slot in available_slots if slot.slot_id == selected_slot_id
        )

        st.write(
            f"Compatibilidade: **{selected_slot.service}**, "
            f"**{selected_slot.appointment_date:%d/%m/%Y}**, "
            f"**{selected_slot.period.lower()}**."
        )

        selected_history = history.get(selected_slot.slot_id, [])
        current_offer = pending_offer(selected_history, selected_slot.slot_id)

        if current_offer is not None:
            candidate = next(
                item
                for item in candidates
                if item.candidate_id == current_offer.candidate_id
            )
            st.info(
                f"Oferta pendente para **{candidate.display_name}**. "
                "Aguarde a resposta antes de oferecer a vaga a outra pessoa."
            )
            accept_col, decline_col = st.columns(2)
            if accept_col.button(
                "Confirmar aceite",
                key=f"accept-{selected_slot.slot_id}",
                type="primary",
            ):
                update_offer_status(selected_slot.slot_id, current_offer, "accepted")
                st.rerun()
            if decline_col.button(
                "Registrar recusa e avançar",
                key=f"decline-{selected_slot.slot_id}",
            ):
                update_offer_status(selected_slot.slot_id, current_offer, "declined")
                st.rerun()
        else:
            unavailable_ids = reserved_candidate_ids(history)
            unavailable_ids.update(
                declined_candidate_ids(history, selected_slot.slot_id)
            )
            suggestions = suggest_candidates(
                selected_slot,
                candidates,
                unavailable_candidate_ids=unavailable_ids,
            )

            if not suggestions:
                st.info("Nenhuma pessoa sintética da fila atende aos critérios.")
            else:
                suggestion = suggestions[0]
                candidate = suggestion.candidate
                st.markdown("#### Próxima pessoa compatível")
                with st.container(border=True):
                    st.markdown(
                        f"**{candidate.display_name}** · "
                        f"posição {candidate.queue_position} na fila"
                    )
                    for reason in suggestion.reasons:
                        st.caption(f"✓ {reason}")
                    st.caption(
                        f"{len(suggestions)} pessoa(s) compatível(is) "
                        "disponível(is) nesta simulação."
                    )

                    if st.button(
                        "Registrar oferta pendente",
                        key=f"offer-{selected_slot.slot_id}-{candidate.candidate_id}",
                        type="primary",
                    ):
                        updated_history = dict(st.session_state.offer_history)
                        attempts = list(
                            updated_history.get(selected_slot.slot_id, ())
                        )
                        attempts.append(
                            OfferAttempt(
                                slot_id=selected_slot.slot_id,
                                candidate_id=candidate.candidate_id,
                            )
                        )
                        updated_history[selected_slot.slot_id] = attempts
                        st.session_state.offer_history = updated_history
                        st.rerun()

st.divider()
st.markdown("### Regras desta etapa")
st.markdown(
    "- Só entram na lista pessoas com serviço, data e período compatíveis.\n"
    "- As ofertas seguem a posição de fila fornecida; o sistema não define "
    "prioridade clínica.\n"
    "- Uma oferta pendente reserva a pessoa até a equipe registrar aceite ou recusa.\n"
    "- Recusas ficam no histórico da vaga; o sistema apresenta a próxima pessoa "
    "compatível.\n"
    "- Registrar, aceitar ou recusar uma oferta é uma simulação e não representa "
    "contato real."
)

st.button("Reiniciar cenário", on_click=reset_demo)

st.divider()
st.markdown("### Indicadores do cenário")
metrics = calculate_operational_metrics(slots, history)
fill_rate_label = (
    f"{metrics.fill_rate:.0%}" if metrics.fill_rate is not None else "N/D"
)
acceptance_rate_label = (
    f"{metrics.resolution_acceptance_rate:.0%}"
    if metrics.resolution_acceptance_rate is not None
    else "N/D"
)
offers_per_fill_label = (
    f"{metrics.mean_offers_per_filled_slot:.1f}"
    if metrics.mean_offers_per_filled_slot is not None
    else "N/D"
)

metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("Vagas preenchidas", f"{metrics.filled_slot_count}/{metrics.slot_count}")
metric_col2.metric("Taxa de preenchimento", fill_rate_label)
metric_col3.metric("Aceite entre respostas", acceptance_rate_label)
st.caption(
    f"Média de ofertas por vaga preenchida: {offers_per_fill_label}. "
    "Taxas sem observações suficientes são exibidas como N/D."
)

st.markdown("#### Preenchimento por origem do cancelamento")
st.dataframe(
    [
        {
            "Origem": source,
            "Vagas preenchidas": filled,
            "Vagas canceladas": total,
            "Preenchimento": f"{filled / total:.0%}" if total else "N/D",
        }
        for source, (filled, total) in metrics.filled_by_cancellation_source.items()
    ],
    hide_index=True,
    width="stretch",
)

st.markdown("#### Distribuição das ofertas por território sintético")
distribution = calculate_group_distribution(slots, candidates, history)
group_rates = [
    item.offer_per_eligible_opportunity_rate
    for item in distribution
    if item.offer_per_eligible_opportunity_rate is not None
]
group_rate_spread = (
    max(group_rates) - min(group_rates)
    if group_rates and any(item.offers for item in distribution)
    else None
)
spread_label = (
    f"{group_rate_spread:.0%}" if group_rate_spread is not None else "N/D"
)
st.metric("Amplitude descritiva entre grupos sintéticos", spread_label)
st.dataframe(
    [
        {
            "Grupo fictício": item.synthetic_area,
            "Pessoas no grupo": item.candidate_count,
            "Pessoas com oportunidade": item.candidates_with_opportunity,
            "Oportunidades elegíveis": item.eligible_opportunities,
            "Ofertas": item.offers,
            "Aceitas": item.accepted,
            "Recusadas": item.declined,
            "Pendentes": item.pending,
            "Ofertas / oportunidades": (
                f"{item.offer_per_eligible_opportunity_rate:.0%}"
                if item.offer_per_eligible_opportunity_rate is not None
                else "N/D"
            ),
        }
        for item in distribution
    ],
    hide_index=True,
    width="stretch",
)
st.caption(
    "Esses grupos e os dados são sintéticos. A taxa compara ofertas emitidas "
    "com pares pessoa-vaga compatíveis no cenário, não mede equidade nem "
    "desempenho real. A amplitude é apenas a diferença entre a maior e a menor "
    "taxa observada, sem ajuste por necessidade, disponibilidade ou outros fatores. "
    "Amostras pequenas limitam qualquer interpretação."
)

st.markdown("#### Perfil sintético de disponibilidade")
availability_profile = calculate_availability_profile(slots, candidates)
st.dataframe(
    [
        {
            "Serviço": item.service,
            "Data": item.appointment_date,
            "Período": item.period,
            "Unidade fictícia": item.unit_id,
            "Vagas": item.slot_count,
            "Pessoas compatíveis": item.candidates_with_availability,
            "Pares pessoa-vaga": item.compatible_pairs,
        }
        for item in availability_profile
    ],
    hide_index=True,
    width="stretch",
)
st.caption(
    "Perfil agregado derivado das disponibilidades declaradas no cenário "
    "sintético. Compatibilidade considera serviço, data, período e recursos de "
    "acessibilidade requeridos; não representa oferta ou demanda de uma rede real."
)

if "policy_scenario" not in st.session_state:
    st.session_state.policy_scenario = generate_synthetic_scenario(
        seed=7,
        slot_count=10,
        candidate_count=10,
    )

st.divider()
with st.expander("Simulador: comparar políticas de alocação", expanded=True):
    st.markdown(
        "Gere um cenário sintético reproduzível e compare três estratégias "
        "sobre as mesmas vagas e disponibilidades."
    )
    controls_col1, controls_col2, controls_col3 = st.columns(3)
    seed = controls_col1.number_input(
        "Semente do cenário",
        min_value=0,
        max_value=2**32 - 1,
        value=7,
        step=1,
        help="A mesma semente e os mesmos tamanhos geram o mesmo cenário.",
    )
    simulated_slot_count = controls_col2.number_input(
        "Vagas canceladas",
        min_value=1,
        max_value=30,
        value=10,
        step=1,
    )
    simulated_candidate_count = controls_col3.number_input(
        "Pessoas na fila",
        min_value=1,
        max_value=60,
        value=10,
        step=1,
    )

    if st.button("Gerar e comparar cenário", type="primary"):
        st.session_state.policy_scenario = generate_synthetic_scenario(
            seed=int(seed),
            slot_count=int(simulated_slot_count),
            candidate_count=int(simulated_candidate_count),
        )

    scenario = st.session_state.policy_scenario
    sequential_result = allocate_sequentially(scenario.slots, scenario.candidates)
    batch_result = allocate_in_batch(scenario.slots, scenario.candidates)
    multicriteria_result = allocate_multicriteria(
        scenario.slots,
        scenario.candidates,
    )
    batch_gain = batch_result.filled_slot_count - sequential_result.filled_slot_count
    multicriteria_gain = (
        multicriteria_result.filled_slot_count - sequential_result.filled_slot_count
    )

    st.caption(
        f"Cenário {len(scenario.slots)} vaga(s), "
        f"{len(scenario.candidates)} pessoa(s), semente {scenario.seed}."
    )
    sequential_col, batch_col, multicriteria_col = st.columns(3)
    sequential_col.metric(
        "Fila sequencial — vagas alocadas",
        f"{sequential_result.filled_slot_count}/{sequential_result.slot_count}",
    )
    batch_col.metric(
        "Lote máximo — vagas alocadas",
        f"{batch_result.filled_slot_count}/{batch_result.slot_count}",
        delta=f"{batch_gain:+d} vs. sequencial",
    )
    multicriteria_col.metric(
        "Multicritério — vagas alocadas",
        f"{multicriteria_result.filled_slot_count}/{multicriteria_result.slot_count}",
        delta=f"{multicriteria_gain:+d} vs. sequencial",
    )
    wait_col1, wait_col2 = st.columns(2)
    sequential_wait_days = potential_wait_days_avoided(
        sequential_result,
        scenario.slots,
        scenario.candidates,
    )
    multicriteria_wait_days = potential_wait_days_avoided(
        multicriteria_result,
        scenario.slots,
        scenario.candidates,
    )
    wait_col1.metric(
        "Dias potenciais vs. referência sintética — sequencial",
        str(sequential_wait_days)
        if sequential_wait_days is not None
        else "N/D",
    )
    wait_col2.metric(
        "Dias potenciais vs. referência sintética — multicritério",
        str(multicriteria_wait_days)
        if multicriteria_wait_days is not None
        else "N/D",
    )
    objective_col1, objective_col2 = st.columns(2)
    objective_col1.metric(
        "Soma das posições de fila — multicritério",
        multicriteria_result.total_queue_position,
    )
    objective_col2.metric(
        "Conflitos com preferências — multicritério",
        multicriteria_result.preference_mismatches,
    )

    st.markdown("#### Como as políticas funcionam")
    st.markdown(
        "- **Fila sequencial:** percorre as vagas na ordem gerada e aloca a "
        "primeira pessoa compatível disponível.\n"
        "- **Lote máximo:** procura o maior número de encaixes compatíveis.\n"
        "- **Multicritério experimental:** mantém o maior preenchimento; entre "
        "essas soluções, minimiza a soma das posições na fila; só então reduz "
        "conflitos com preferências declaradas de turno/unidade. Necessidades de "
        "acessibilidade são restrições obrigatórias, não preferências.\n"
        "- Cada pessoa pode receber no máximo uma alocação por política. São "
        "simulações, não ofertas reais, e a regra de fila é uma hipótese a "
        "validar com cada serviço."
    )
    st.caption(
        "Os dias potenciais são a diferença entre a data-base fictícia de "
        "atendimento e a data da vaga alocada. São um contrafactual sintético, "
        "não dias de espera realmente evitados."
    )

    st.markdown("#### Alocações lado a lado")
    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in scenario.candidates
    }
    comparison_rows = []
    for slot in scenario.slots:
        sequential_candidate_id = sequential_result.assignments.get(slot.slot_id)
        batch_candidate_id = batch_result.assignments.get(slot.slot_id)
        multicriteria_candidate_id = multicriteria_result.assignments.get(slot.slot_id)
        comparison_rows.append(
            {
                "Vaga": slot.slot_id,
                "Serviço": slot.service,
                "Data": slot.appointment_date.strftime("%d/%m/%Y"),
                "Período": slot.period,
                "Sequencial": (
                    candidate_by_id[sequential_candidate_id].display_name
                    if sequential_candidate_id
                    else "Sem alocação"
                ),
                "Lote": (
                    candidate_by_id[batch_candidate_id].display_name
                    if batch_candidate_id
                    else "Sem alocação"
                ),
                "Multicritério": (
                    candidate_by_id[multicriteria_candidate_id].display_name
                    if multicriteria_candidate_id
                    else "Sem alocação"
                ),
            }
        )
    st.dataframe(comparison_rows, hide_index=True, width="stretch")

    st.markdown("#### Distribuição por território sintético")
    sequential_distribution = {
        row["Grupo fictício"]: row
        for row in summarize_policy_results(
            sequential_result,
            scenario.candidates,
        )
    }
    batch_distribution = {
        row["Grupo fictício"]: row
        for row in summarize_policy_results(
            batch_result,
            scenario.candidates,
        )
    }
    multicriteria_distribution = {
        row["Grupo fictício"]: row
        for row in summarize_policy_results(
            multicriteria_result,
            scenario.candidates,
        )
    }
    distribution_rows = []
    all_areas = (
        set(sequential_distribution)
        | set(batch_distribution)
        | set(multicriteria_distribution)
    )
    for area in sorted(all_areas):
        sequential_row = sequential_distribution.get(area, {})
        batch_row = batch_distribution.get(area, {})
        multicriteria_row = multicriteria_distribution.get(area, {})
        eligible_pairs = max(
            sequential_row.get("Pares elegíveis", 0),
            batch_row.get("Pares elegíveis", 0),
            multicriteria_row.get("Pares elegíveis", 0),
        )
        distribution_rows.append(
            {
                "Grupo fictício": area,
                "Pares elegíveis": eligible_pairs,
                "Alocadas — sequencial": sequential_row.get("Vagas alocadas", 0),
                "Alocadas — lote": batch_row.get("Vagas alocadas", 0),
                "Alocadas — multicritério": multicriteria_row.get(
                    "Vagas alocadas",
                    0,
                ),
            }
        )
    st.dataframe(distribution_rows, hide_index=True, width="stretch")
    st.caption(
        "Nenhuma política otimiza equidade. A composição dos grupos é fictícia; "
        "as contagens não demonstram impacto, justiça ou desempenho clínico. Em "
        "serviço real, regras e critérios precisam ser validados com profissionais "
        "e autorizados pelo serviço."
    )

with st.expander("Simulação de impacto em múltiplos cenários"):
    st.markdown(
        "Repita a comparação em cenários sintéticos reproduzíveis para observar "
        "a variação dos resultados, em vez de concluir a partir de uma única "
        "semente."
    )
    impact_cols = st.columns(4)
    impact_seed = impact_cols[0].number_input(
        "Semente-base",
        min_value=0,
        max_value=2**32 - 1,
        value=7,
        step=1,
        key="impact_seed",
    )
    impact_repetitions = impact_cols[1].number_input(
        "Cenários",
        min_value=1,
        max_value=100,
        value=30,
        step=1,
        key="impact_repetitions",
    )
    impact_slot_count = impact_cols[2].number_input(
        "Vagas por cenário",
        min_value=1,
        max_value=30,
        value=10,
        step=1,
        key="impact_slots",
    )
    impact_candidate_count = impact_cols[3].number_input(
        "Pessoas por cenário",
        min_value=1,
        max_value=60,
        value=18,
        step=1,
        key="impact_candidates",
    )
    if st.button("Executar simulação comparativa", key="run-impact-simulation"):
        st.session_state.impact_simulation = simulate_policy_impact(
            seed=int(impact_seed),
            replication_count=int(impact_repetitions),
            slot_count=int(impact_slot_count),
            candidate_count=int(impact_candidate_count),
        )

    impact_result = st.session_state.get("impact_simulation")
    if impact_result is not None:
        st.caption(
            f"{impact_result.replication_count} cenários; semente-base "
            f"{impact_result.seed}; {impact_result.slot_count} vaga(s) e "
            f"{impact_result.candidate_count} pessoa(s) por cenário."
        )
        st.dataframe(
            [
                {
                    "Política": summary.policy_name,
                    "Média de vagas alocadas": (
                        f"{summary.mean_filled_slots:.2f}"
                    ),
                    "Mediana": f"{summary.median_filled_slots:.1f}",
                    "Mín.–máx.": (
                        f"{summary.minimum_filled_slots}–"
                        f"{summary.maximum_filled_slots}"
                    ),
                    "Taxa média de preenchimento": (
                        f"{summary.mean_fill_rate:.1%}"
                    ),
                    "Cenários no máximo observado": (
                        f"{summary.scenarios_with_maximum_fill_rate:.0%}"
                    ),
                    "Cenários com mais alocações que sequencial": (
                        f"{summary.scenarios_with_more_fills_than_sequential:.0%}"
                        if summary.scenarios_with_more_fills_than_sequential
                        is not None
                        else "Referência"
                    ),
                }
                for summary in impact_result.summaries
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Resultados de simulação sintética, condicionados às distribuições e "
            "regras programadas. A frequência de máximo admite empate; não é "
            "probabilidade de sucesso no mundo real nem evidência causal. Dados "
            "sintéticos não justificam treinar ou validar um modelo preditivo."
        )
