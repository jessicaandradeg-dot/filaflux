# FilaFlux

**Simulador de alocação operacional para o reaproveitamento de vagas de consultas canceladas.**

O FilaFlux demonstra como regras transparentes de compatibilidade e otimização podem apoiar a análise do reaproveitamento de vagas. Por padrão, utiliza exclusivamente dados sintéticos e não se conecta a agendas, filas ou sistemas de saúde reais.

Uma instalação local/privada pode, por configuração explícita, analisar arquivos CSV operacionais autorizados e minimizados. Essa análise é isolada: não sincroniza alterações nem grava alocações na plataforma de origem.

O aplicativo também apresenta, em seção independente e opcional, indicadores municipais agregados de capacidade hospitalar e produção ambulatorial do SUS. Esses indicadores não interferem na simulação.

**[Acessar o FilaFlux](https://filaflux-saude.streamlit.app/)** · **[Código-fonte no GitHub](https://github.com/jessicaandradeg-dot/filaflux)**

## Objetivo

Cancelamentos de consultas podem deixar horários disponíveis enquanto outras pessoas aguardam atendimento. O FilaFlux explora como identificar encaixes compatíveis e comparar diferentes regras de alocação.

O protótipo ajuda a discutir como critérios explícitos afetam o preenchimento, a posição na fila e as preferências. Em um serviço real, a equipe responsável continuaria no controle das decisões, das regras autorizadas e do contato com as pessoas.

## Funcionalidades

1. **Fluxo demonstrativo:** selecionar uma vaga fictícia, ver a próxima pessoa compatível e simular aceite ou recusa.
2. **Compatibilidade explicável:** comparar serviço, data, período e requisitos de acessibilidade.
3. **Comparação de estratégias:** avaliar fila sequencial, lote máximo e otimização multicritério.
4. **Parâmetros sintéticos:** definir quantidade de vagas, pessoas, serviços e unidades participantes.
5. **Análise CSV privada:** comparar dados operacionais pseudonimizados por upload, sem sincronização ou escrita no sistema de origem.
6. **Contexto público:** consultar indicadores municipais agregados do CNES e SIA/SUS, independentes da simulação.
7. **Múltiplos cenários sintéticos:** observar a variação dos resultados em cenários reprodutíveis.

## Estratégias de alocação

- **Fila sequencial:** percorre as vagas e atribui a cada uma a primeira pessoa compatível ainda não utilizada.
- **Lote máximo:** considera as vagas em conjunto e busca maximizar o total de encaixes, usando cada pessoa no máximo uma vez.
- **Multicritério experimental:** maximiza preenchimento, depois considera posição na fila e conflitos com preferências de unidade e período. Necessidades de acessibilidade são requisitos obrigatórios.

A posição na fila é fornecida pelo cenário; o sistema não calcula prioridade clínica. O critério multicritério é uma hipótese para discussão, não uma regra assistencial aprovada.

## Interpretar os resultados

- **Vagas alocadas** são pares compatíveis encontrados pela política no cenário.
- **Dias potenciais** são uma diferença hipotética para uma data-base sintética; não representam espera real nem dias efetivamente evitados.
- **Amplitude entre grupos** é descritiva, não uma medida validada de equidade.
- **Múltiplos cenários** avaliam sensibilidade às distribuições artificiais programadas; não estimam impacto no SUS, causalidade ou probabilidade de sucesso no mundo real.

Os resultados demonstram o funcionamento do software e ajudam a discutir trade-offs. Não são evidência clínica ou operacional.

## Dados públicos do SUS

As fontes públicas são processadas separadamente e não alimentam as regras de alocação.

### Capacidade hospitalar — CNES

A seção utiliza a base oficial [Hospitais e Leitos — Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos), derivada do CNES, no arquivo anual de 2025. O processamento agrega em memória as 12 competências para o município do Rio de Janeiro (`330455`). Em dezembro, a extração registra 9.764 leitos SUS, 1.287 leitos de UTI SUS e 192 estabelecimentos. O aplicativo não persiste o arquivo bruto nem registros individualizados.

### Produção ambulatorial — SIA/SUS

A consulta utiliza a [tabulação municipal oficial do SIA/SUS no DATASUS](https://datasus.saude.gov.br/acesso-a-informacao/producao-ambulatorial-sia-sus/): município do estabelecimento Rio de Janeiro (`330455`), ano 2025, linha Município, coluna Ano/mês de processamento, medida Quantidade aprovada (`Qtd.aprovada`) e todas as categorias para os demais filtros.

A resposta CSV é validada quanto a cabeçalho, presença dos 12 meses, linha municipal única, valores inteiros e consistência do total anual. Apenas os totais mensais e metadados da consulta permanecem na sessão; o CSV não é salvo.

Quantidade aprovada não é número de pessoas ou usuários únicos, demanda não atendida, fila, espera ou prova de acesso efetivo. O mês de processamento não corresponde necessariamente ao mês do atendimento. Leitos cadastrados não representam disponibilidade em tempo real. A comparação é descritiva e não demonstra causalidade ou impacto do FilaFlux. O TabNet pode atualizar os meses recentes; a data e hora da consulta devem acompanhar capturas usadas em apresentações.

## Importação CSV em instalação privada

O modo CSV só aparece quando `FILAFUX_ENABLE_REAL_DATA_UPLOAD=1` está configurado. A instância pública no Streamlit Community Cloud deve permanecer com esse modo desabilitado. O aplicativo não detecta nem garante que um ambiente seja privado.

Use somente dados autorizados, minimizados e pseudonimizados. Não inclua nomes, documentos, contato, diagnóstico, texto livre ou colunas adicionais. Necessidades de acessibilidade podem ser dados sensíveis; inclua-as apenas se forem necessárias e autorizadas. Pseudonimização não equivale a anonimização.

Os arquivos são processados em memória e não gravados pelo app. Limpe a sessão ao terminar. Isso não substitui controles de acesso, avaliação de risco ou política institucional de retenção.

Limites: dois arquivos CSV UTF-8, até 1 MB cada, no máximo 30 vagas e 60 pessoas. Separe listas com `|`.

**Arquivo de vagas:**

Campos obrigatórios: `slot_id, service, appointment_date, period, cancellation_source, unit_id`. `accessibility_features` é opcional.

**Arquivo da fila:**

Campos obrigatórios: `candidate_id, service, queue_position, available_dates, available_periods`. `preferred_unit_ids` e `accessibility_needs` são opcionais.

Datas usam `AAAA-MM-DD`; períodos aceitos: `Manhã` e `Tarde`; origem do cancelamento: `Serviço` ou `Paciente`. `candidate_id` deve ser pseudônimo e é exibido nas sugestões. O app oferece modelos CSV para download.

A análise gera sugestões para revisão humana. Não contata pessoas, não altera filas reais, não tem integração com agendas e não determina prioridade clínica. Sincronizar ou gravar no sistema de origem exigiria integração separada, autorizada, auditável e validada pelo serviço.

## Referência de produto

A [lista de espera da NexHealth](https://www.nexhealth.com/features/waitlist) anuncia seleção de pessoas por disponibilidade e tipo de consulta, aceite online e sincronização automática com calendários clínicos. São funcionalidades divulgadas pelo fornecedor, não evidência independente de impacto. O insight para o FilaFlux é deixar explícita a diferença entre análise offline e operação real: confirmação e sincronização dependem de integração própria e governada. Esta comparação inicial não é uma revisão exaustiva do mercado.

## Limitações e segurança

O FilaFlux é um protótipo, não um sistema de operação assistencial. Não estima urgência, não calcula prioridade clínica, não faz contato, não substitui profissionais e não comprova redução de filas ou tempo de espera.

O projeto usa regras explícitas de compatibilidade e otimização combinatória; não treina nem utiliza modelo preditivo de IA/ML. Não insira dados reais de pacientes na aplicação pública.

## Executar localmente

Requer Python 3.10 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m streamlit run app.py
```

Para habilitar a importação CSV numa instalação local/privada, configure a variável de ambiente antes de iniciar:

```powershell
$env:FILAFUX_ENABLE_REAL_DATA_UPLOAD = "1"
python -m streamlit run app.py
```

Não configure essa variável na publicação pública.

## Publicar no Streamlit Community Cloud

A aplicação publicada é pública. Mantenha a importação CSV desabilitada; ela usa cenários sintéticos e, mediante ação do visitante, consulta fontes públicas do SUS. Não recebe dados de pacientes.

## Testes

```powershell
python -m pytest
```

Os testes cobrem compatibilidade, fluxo de ofertas, validação CSV, indicadores, reprodutibilidade dos cenários, otimização multicritério e agregação segura de dados públicos, sem chamadas de rede nos testes.

## Próximos passos antes de um piloto real

Validar o processo com profissionais e gestores; definir regras autorizadas; avaliar impactos entre grupos; estabelecer proteção de dados, segurança e persistência; e integrar sistemas somente com autorização e governança. O protótipo atual não está pronto para uso assistencial.
