# FilaFlux

**Simulador de alocação operacional para o reaproveitamento de vagas de consultas canceladas.**

O **FilaFlux** é um protótipo que demonstra como regras transparentes de compatibilidade e técnicas de otimização podem apoiar a análise do reaproveitamento de vagas de consultas canceladas.

A proposta é permitir que uma equipe de saúde simule diferentes estratégias de alocação, visualize os possíveis encaixes e compare os resultados de cada abordagem.

A simulação utiliza exclusivamente dados sintéticos e não se conecta a agendas, filas ou sistemas de saúde reais.

O aplicativo também apresenta, em uma seção independente e opcional, indicadores municipais agregados de capacidade hospitalar e produção ambulatorial do SUS. Esses indicadores servem apenas para contextualizar o cenário de saúde e não interferem na simulação.

**[Acessar o FilaFlux](https://filaflux-saude.streamlit.app/)**

---

## 1. Objetivo do projeto

Cancelamentos de consultas podem deixar horários disponíveis enquanto outras pessoas aguardam atendimento. O FilaFlux explora uma possível estratégia para reaproveitar essas vagas: identificar pessoas compatíveis e comparar diferentes regras de alocação.

O protótipo busca responder a perguntas como:

- Como identificar pessoas compatíveis com uma vaga cancelada?
- Como diferentes estratégias de alocação influenciam o número de encaixes?
- Uma alocação que considera as vagas em conjunto consegue aproveitar melhor as oportunidades?
- Quais são os trade-offs entre preenchimento, posição na fila e preferências de atendimento?
- Como os resultados se comportam em diferentes cenários simulados?

Em um serviço real, a equipe responsável continuaria no controle das decisões, das regras autorizadas e do contato com as pessoas.

## 2. Funcionalidades

O aplicativo permite explorar seis componentes principais:

1. **Simulação de vagas canceladas:** seleção de uma vaga fictícia e identificação da próxima pessoa compatível, com registro de uma oferta simulada e possibilidade de aceite ou recusa.
2. **Compatibilidade explicável:** verificação de critérios como serviço, data, período e necessidades fictícias de acessibilidade, tratadas como requisitos obrigatórios.
3. **Comparação de estratégias de alocação:** avaliação de três políticas distintas utilizando o mesmo conjunto de vagas e disponibilidades.
4. **Perfil de disponibilidade:** apresentação de contagens agregadas de vagas, pessoas compatíveis e pares pessoa-vaga, considerando serviço, data, período e unidade fictícia.
5. **Indicadores de desempenho:** visualização de preenchimento, respostas às ofertas e distribuição de oportunidades entre grupos territoriais fictícios.
6. **Simulação de múltiplos cenários:** repetição reprodutível das comparações, com apresentação de média, mediana, amplitude e frequência dos melhores resultados de preenchimento.

## 3. Estratégias de alocação

O FilaFlux compara três políticas de alocação:

### 3.1. Fila sequencial

Percorre as vagas na ordem gerada e atribui a cada uma a primeira pessoa compatível ainda não utilizada.

É uma abordagem simples, mas uma escolha para determinada vaga pode impedir outro encaixe que seria possível com uma distribuição diferente.

### 3.2. Emparelhamento de máximo preenchimento

Considera as vagas em conjunto e busca maximizar o número total de encaixes compatíveis, garantindo que cada pessoa seja utilizada no máximo uma vez.

Essa abordagem permite avaliar se uma análise conjunta das oportunidades consegue alcançar um preenchimento superior ao da estratégia sequencial.

### 3.3. Otimização multicritério experimental

Adota uma sequência de objetivos:

1. Maximizar o número total de vagas preenchidas.
2. Entre as soluções com o mesmo preenchimento, minimizar a soma das posições de fila fornecidas no cenário.
3. Em seguida, minimizar conflitos com preferências fictícias de unidade e período.

As necessidades de acessibilidade são consideradas restrições obrigatórias, e não critérios opcionais de pontuação.

**Importante:** a posição na fila é um atributo fornecido pelo cenário sintético. O sistema não calcula prioridade clínica. A estratégia multicritério é experimental e serve para discussão metodológica, não constituindo uma regra assistencial recomendada ou aprovada.

## 4. Indicadores e interpretação dos resultados

O aplicativo apresenta indicadores para facilitar a comparação entre as estratégias.

| Indicador | Interpretação |
|---|---|
| Vagas alocadas | Quantidade de pares compatíveis encontrados pela política no cenário. |
| Dias potenciais | Diferença hipotética entre uma data-base sintética e a data da vaga. |
| Respostas às ofertas | Distribuição dos resultados das ofertas simuladas. |
| Amplitude entre grupos | Diferença descritiva entre taxas de ofertas por oportunidades fictícias. |
| Resultados por cenário | Média, mediana, amplitude e frequência dos melhores preenchimentos nas simulações. |

A interpretação desses indicadores exige algumas ressalvas:

- Dias potenciais não representam tempo de espera real nem dias efetivamente evitados.
- A amplitude entre grupos não é uma medida validada de equidade. Não considera diferenças de necessidade, disponibilidade, barreiras de acesso ou contexto social.
- As simulações de múltiplos cenários dependem das distribuições artificiais programadas.
- Os resultados não representam estimativas de impacto no SUS, avaliações causais, probabilidades de sucesso no mundo real ou validações externas.

Os indicadores servem para demonstrar o funcionamento do software e discutir os trade-offs entre as políticas avaliadas.

## 5. Integração de dados públicos do SUS

Além da simulação, o FilaFlux apresenta uma seção opcional com indicadores municipais agregados provenientes de duas fontes públicas: CNES e SIA/SUS.

Essas fontes são processadas separadamente e não alimentam as regras de alocação.

### 5.1. Capacidade hospitalar — CNES

A seção de capacidade hospitalar utiliza a base oficial [Hospitais e Leitos — Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos), derivada do Cadastro Nacional de Estabelecimentos de Saúde (CNES), utilizando o arquivo anual de 2025.

O processamento contempla:

- Município do Rio de Janeiro (código `330455`).
- Agregação mensal por competência.
- Contagem de leitos SUS, leitos de UTI SUS e estabelecimentos.
- Comparação da evolução mensal dos indicadores, utilizando janeiro de 2025 como referência.

A extração validada contém as 12 competências de 2025.

Em dezembro, foram registrados:

- **9.764 leitos SUS**;
- **1.287 leitos de UTI SUS**;
- **192 estabelecimentos**.

O arquivo é processado em memória. O aplicativo seleciona os campos necessários para a agregação, utilizando um código temporário de estabelecimento para contagem e verificação de duplicidades. Apenas os indicadores mensais agregados são mantidos na sessão. O arquivo bruto e os registros individualizados por estabelecimento não são persistidos pelo aplicativo.

### 5.2. Produção ambulatorial — SIA/SUS

A produção ambulatorial é consultada separadamente por meio da [tabulação municipal oficial do SIA/SUS no DATASUS](https://datasus.saude.gov.br/acesso-a-informacao/producao-ambulatorial-sia-sus/).

A consulta utiliza os seguintes parâmetros:

| Parâmetro | Configuração |
|---|---|
| Município do estabelecimento | Rio de Janeiro (`330455`) |
| Ano | 2025 |
| Linha | Município |
| Coluna | Ano/mês de processamento |
| Medida | Quantidade aprovada (`Qtd.aprovada`) |
| Demais filtros | Todas as categorias |

A consulta utiliza a tabulação municipal agregada, não arquivos brutos estaduais nem registros individualizados.

A resposta CSV passa por validações para verificar:

- Presença do cabeçalho esperado.
- Existência exata dos 12 meses.
- Presença de uma única linha municipal.
- Valores inteiros.
- Consistência entre a soma dos valores mensais e o total anual.

A extração validada retornou **194.949.723 procedimentos ambulatoriais aprovados** em 2025.

O aplicativo mantém na sessão apenas os 12 totais mensais e os metadados da consulta, incluindo fonte, parâmetros, endereço do CSV e data/hora de execução. O arquivo CSV não é salvo pelo aplicativo.

### 5.3. Apresentação e limites dos indicadores públicos

Os indicadores do CNES e do SIA/SUS são apresentados separadamente:

- A produção ambulatorial possui gráfico próprio.
- Quando as duas séries estão carregadas, os indicadores são apresentados lado a lado em uma tabela mensal.
- Não há combinação dos indicadores em um índice único nem compartilhamento de escala gráfica.

É importante considerar que:

- Quantidade aprovada no SIA/SUS não equivale ao número de pessoas ou usuários únicos.
- Produção aprovada não representa demanda não atendida, tamanho de fila, tempo de espera ou comprovação de acesso efetivo.
- O mês de processamento não corresponde necessariamente ao mês em que o atendimento ocorreu.
- Leitos cadastrados no CNES não significam leitos disponíveis em tempo real.
- Os indicadores não medem cancelamentos, filas ou disponibilidade de consultas.
- A comparação é descritiva e não demonstra associação causal, capacidade assistencial efetiva ou impacto do FilaFlux.

O TabNet pode atualizar os meses mais recentes. Por isso, a data e o horário da consulta registrados pelo aplicativo devem acompanhar qualquer captura utilizada em apresentações.

**Os dados públicos têm finalidade exclusivamente contextual e não interferem na simulação de alocação.**

## 6. Limitações e escopo de aplicação

O FilaFlux é um protótipo experimental de demonstração, não um sistema operacional de gestão de filas de saúde.

Atualmente, o aplicativo:

- Não utiliza dados reais de pacientes ou consultas canceladas.
- Não se conecta a agendas, filas ou sistemas de regulação.
- Não realiza contato ou envio de notificações às pessoas.
- Não estima urgência ou prioridade clínica.
- Não substitui a avaliação dos profissionais de saúde.
- Não comprova redução de filas, tempo de espera ou melhoria no acesso aos serviços.

A aplicação de estratégias semelhantes em serviços reais exigiria validação com dados operacionais, definição de critérios assistenciais autorizados, avaliação de equidade, requisitos de segurança e privacidade e participação das equipes responsáveis.

O propósito do FilaFlux é demonstrar uma proposta de solução, tornar explícitas as regras de compatibilidade e permitir a comparação de estratégias de alocação em cenários controlados.

---

## 7. Aplicativo

**Acesse o protótipo:** [https://filaflux-saude.streamlit.app/](https://filaflux-saude.streamlit.app/)

**Código-fonte:** [https://github.com/jessicaandradeg-dot/filaflux](https://github.com/jessicaandradeg-dot/filaflux)
