# FilaFlux

**Simulador de alocação operacional para o reaproveitamento de vagas de consultas canceladas.**

O **FilaFlux** é um protótipo que demonstra como regras transparentes de compatibilidade e técnicas de otimização podem apoiar a análise do reaproveitamento de vagas de consultas canceladas.

A proposta é identificar pessoas compatíveis com vagas disponíveis e comparar diferentes estratégias de alocação, permitindo visualizar seus resultados e os critérios utilizados em cada decisão.

O projeto possui dois modos de análise:

- **Simulação sintética:** funcionamento padrão, com dados fictícios, sem conexão com agendas, filas ou sistemas de saúde reais.
- **Análise CSV:** funcionalidade opcional, disponível somente quando habilitada por configuração explícita em uma instalação local ou privada. Permite analisar arquivos operacionais autorizados e minimizados, sem sincronizar alterações ou gravar alocações no sistema de origem.

O aplicativo também apresenta uma seção independente com indicadores municipais agregados de capacidade hospitalar e produção ambulatorial do SUS. Esses dados são utilizados exclusivamente para contextualização e não interferem na simulação.

**[Acessar o FilaFlux](https://filaflux-saude.streamlit.app/)** · **[Código-fonte no GitHub](https://github.com/jessicaandradeg-dot/filaflux)**

---

## 1. Objetivo

Cancelamentos de consultas podem deixar horários disponíveis enquanto outras pessoas aguardam atendimento.

O FilaFlux explora uma possível solução para esse problema: identificar oportunidades de encaixe e avaliar como diferentes regras de alocação influenciam o preenchimento das vagas.

O protótipo permite discutir questões como:

- Como identificar pessoas compatíveis com uma vaga cancelada?
- Como diferentes estratégias influenciam o número de encaixes?
- A análise conjunta das vagas pode aumentar o aproveitamento das oportunidades?
- Como considerar a posição na fila e as preferências de atendimento?
- Quais são os trade-offs entre as estratégias avaliadas?

Em um serviço real, a equipe responsável continuaria no controle das decisões, das regras autorizadas e do contato com as pessoas.

## 2. Funcionalidades

O aplicativo reúne as seguintes funcionalidades:

1. **Simulação do fluxo operacional:** seleção de uma vaga cancelada fictícia, identificação da próxima pessoa compatível e simulação de uma oferta, com possibilidade de aceite ou recusa.
2. **Compatibilidade explicável:** verificação de serviço, data, período e requisitos de acessibilidade.
3. **Comparação de estratégias:** avaliação de três políticas de alocação: fila sequencial, lote máximo e otimização multicritério.
4. **Configuração de cenários:** definição da quantidade de vagas, pessoas, serviços e unidades participantes.
5. **Análise de arquivos CSV:** comparação de dados operacionais pseudonimizados em uma instalação com a funcionalidade habilitada.
6. **Indicadores públicos do SUS:** consulta independente de dados municipais agregados do CNES e SIA/SUS.
7. **Simulação de múltiplos cenários:** repetição reprodutível das comparações para observar a variação dos resultados.

## 3. Estratégias de alocação

O FilaFlux compara três abordagens utilizando o mesmo conjunto de vagas e disponibilidades.

### 3.1. Fila sequencial

Percorre as vagas na ordem gerada e atribui a cada uma a primeira pessoa compatível ainda não utilizada.

É uma abordagem simples, mas uma escolha para determinada vaga pode impedir outro encaixe que seria possível com uma distribuição diferente.

### 3.2. Lote máximo

Considera as vagas em conjunto e busca maximizar o número total de encaixes compatíveis, garantindo que cada pessoa seja utilizada no máximo uma vez.

Essa abordagem permite avaliar se a análise conjunta das oportunidades consegue alcançar um preenchimento superior ao da estratégia sequencial.

### 3.3. Otimização multicritério experimental

Utiliza uma sequência de objetivos:

1. Maximizar o número total de vagas preenchidas.
2. Entre as soluções com o mesmo preenchimento, minimizar a soma das posições de fila fornecidas no cenário.
3. Em seguida, minimizar conflitos com preferências fictícias de unidade e período.

As necessidades de acessibilidade são tratadas como requisitos obrigatórios de compatibilidade, e não como critérios opcionais de pontuação.

**Importante:** a posição na fila é um atributo fornecido pelo cenário. O sistema não calcula prioridade clínica. A estratégia multicritério é experimental e constitui uma hipótese para discussão metodológica, não uma regra assistencial recomendada ou aprovada.

## 4. Indicadores e interpretação dos resultados

O aplicativo apresenta indicadores para comparar o comportamento das estratégias.

| Indicador | Significado |
|---|---|
| Vagas alocadas | Quantidade de pares compatíveis encontrados pela política no cenário. |
| Dias potenciais | Diferença hipotética entre uma data-base sintética e a data da vaga. |
| Amplitude entre grupos | Diferença descritiva entre taxas de ofertas por oportunidades fictícias. |
| Resultados por cenário | Média, mediana, amplitude e frequência dos melhores preenchimentos nas simulações. |

Algumas ressalvas são importantes:

- Dias potenciais não representam tempo de espera real nem dias efetivamente evitados.
- A amplitude entre grupos não é uma medida validada de equidade e não considera diferenças de necessidade, disponibilidade, barreiras de acesso ou contexto social.
- As simulações de múltiplos cenários avaliam a sensibilidade às distribuições artificiais programadas.
- Os resultados não representam estimativas de impacto no SUS, avaliações causais, probabilidades de sucesso no mundo real ou validação externa.

Os indicadores demonstram o funcionamento do software e permitem discutir os trade-offs entre as políticas avaliadas. Não constituem evidência clínica ou operacional.

## 5. Indicadores públicos do SUS

O aplicativo possui uma seção opcional de contextualização com dados públicos agregados de duas fontes: CNES e SIA/SUS.

As consultas são processadas separadamente e **não alimentam as regras de alocação**.

### 5.1. Capacidade hospitalar — CNES

A seção utiliza a base oficial [Hospitais e Leitos — Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos), derivada do Cadastro Nacional de Estabelecimentos de Saúde (CNES), utilizando o arquivo anual de 2025.

O processamento contempla:

- Município do Rio de Janeiro (código `330455`).
- Agregação mensal por competência.
- Contagem de leitos SUS, leitos de UTI SUS e estabelecimentos.

A extração validada contém as 12 competências de 2025.

Em dezembro, foram registrados:

- **9.764 leitos SUS**;
- **1.287 leitos de UTI SUS**;
- **192 estabelecimentos**.

O arquivo é processado em memória. O aplicativo utiliza os campos necessários para a agregação, incluindo um código temporário de estabelecimento para contagem e verificação de duplicidades. Apenas os indicadores mensais agregados são mantidos na sessão. O arquivo bruto e os registros individualizados não são persistidos pelo aplicativo.

### 5.2. Produção ambulatorial — SIA/SUS

A produção ambulatorial é consultada por meio da [tabulação municipal oficial do SIA/SUS no DATASUS](https://datasus.saude.gov.br/acesso-a-informacao/producao-ambulatorial-sia-sus/).

A consulta utiliza os seguintes parâmetros:

| Parâmetro | Configuração |
|---|---|
| Município do estabelecimento | Rio de Janeiro (`330455`) |
| Ano | 2025 |
| Linha | Município |
| Coluna | Ano/mês de processamento |
| Medida | Quantidade aprovada (`Qtd.aprovada`) |
| Demais filtros | Todas as categorias |

A consulta utiliza a tabulação municipal agregada, não arquivos brutos estaduais ou registros individualizados.

A resposta CSV passa por validações para verificar:

- Presença do cabeçalho esperado.
- Existência exata dos 12 meses.
- Presença de uma única linha municipal.
- Valores inteiros.
- Consistência entre a soma mensal e o total anual.

A extração validada retornou **194.949.723 procedimentos ambulatoriais aprovados em 2025**.

O aplicativo mantém na sessão apenas os 12 totais mensais e os metadados da consulta, incluindo fonte, parâmetros, endereço do CSV e data/hora de execução. O arquivo CSV não é salvo pelo aplicativo.

### 5.3. Limitações dos indicadores públicos

Os indicadores possuem caráter exclusivamente descritivo:

- Quantidade aprovada no SIA/SUS não equivale ao número de pessoas ou usuários únicos.
- Produção aprovada não representa demanda não atendida, tamanho de fila, tempo de espera ou comprovação de acesso efetivo.
- O mês de processamento não corresponde necessariamente ao mês em que o atendimento ocorreu.
- Leitos cadastrados no CNES não representam disponibilidade em tempo real.
- Os dados não medem cancelamentos, filas ou disponibilidade de consultas.
- A comparação não demonstra causalidade, capacidade assistencial efetiva ou impacto do FilaFlux.

O TabNet pode atualizar os meses mais recentes. Por isso, a data e o horário da consulta devem acompanhar capturas utilizadas em apresentações.

## 6. Análise de arquivos CSV em instalação local ou privada

Além da simulação sintética, o FilaFlux possui um modo opcional de importação de arquivos CSV para análise de dados operacionais.

Essa funcionalidade permite avaliar as regras de compatibilidade e as estratégias de alocação utilizando arquivos autorizados, sem estabelecer integração direta com o sistema de origem.

### 6.1. Habilitação

O modo CSV somente fica disponível quando a seguinte variável de ambiente está configurada:

`FILAFUX_ENABLE_REAL_DATA_UPLOAD=1`

A instância pública publicada no Streamlit Community Cloud deve permanecer com essa funcionalidade desabilitada.

O aplicativo não detecta nem garante que uma instalação seja privada. A habilitação deve ocorrer somente em um ambiente com controles de acesso e segurança adequados.

### 6.2. Cuidados com os dados

Utilize somente dados autorizados, minimizados e pseudonimizados.

Não inclua:
- Nomes ou documentos de identificação.
- Telefones, e-mails ou outros dados de contato.
- Diagnósticos ou informações clínicas desnecessárias.
- Textos livres.
- Colunas adicionais que não sejam necessárias à análise.

Necessidades de acessibilidade podem constituir dados pessoais sensíveis e devem ser incluídas somente quando necessárias e devidamente autorizadas.

**Pseudonimização não equivale a anonimização.** Um identificador pseudonimizado ainda pode permitir a identificação de uma pessoa quando combinado com outras informações.

Os arquivos são processados em memória e não são gravados pelo aplicativo. Ao finalizar, limpe a sessão. Esse comportamento não substitui controles de acesso, avaliação de riscos ou políticas institucionais de segurança e retenção de dados.

### 6.3. Formato e limites dos arquivos

A importação aceita:

| Requisito | Limite |
|---|---|
| Formato | CSV UTF-8 |
| Quantidade | 2 arquivos |
| Tamanho | Até 1 MB por arquivo |
| Vagas | Até 30 |
| Pessoas | Até 60 |
| Separador de listas | `\|` |

São necessários dois arquivos: um com as vagas disponíveis e outro com as pessoas na fila.

**Arquivo de vagas**

Campos obrigatórios:

`slot_id, service, appointment_date, period, cancellation_source, unit_id`

Campo opcional:

`accessibility_features`

**Arquivo da fila**

Campos obrigatórios:

`candidate_id, service, queue_position, available_dates, available_periods`

Campos opcionais:

`preferred_unit_ids, accessibility_needs`

### 6.4. Regras de preenchimento

- Datas devem utilizar o formato `AAAA-MM-DD`.
- Períodos aceitos: `Manhã` e `Tarde`.
- Origem do cancelamento: `Serviço` ou `Paciente`.
- `candidate_id` deve ser um identificador pseudonimizado, pois será exibido nas sugestões.
- Listas de datas, períodos e preferências devem utilizar `|` como separador.

O aplicativo disponibiliza modelos CSV para download, facilitando a preparação dos arquivos.

### 6.5. Resultado da análise

A importação permite gerar sugestões de alocação para revisão humana.

O modo CSV é exclusivamente analítico:
- Não contata pessoas.
- Não altera filas reais.
- Não sincroniza agendas.
- Não grava alocações no sistema de origem.
- Não determina prioridade clínica.

Qualquer integração futura com sistemas de saúde exigiria desenvolvimento separado, autorização institucional, controles de acesso, auditoria e validação pelo serviço responsável.

## 7. Referência de produto

Como referência de mercado, a [NexHealth — Waitlist](https://www.nexhealth.com/features/waitlist) divulga funcionalidades de seleção de pessoas por disponibilidade e tipo de consulta, aceite online e sincronização automática com calendários clínicos.

Essas funcionalidades são informações divulgadas pelo próprio fornecedor, não evidências independentes de impacto.

A comparação ajuda a destacar uma diferença importante na proposta do FilaFlux: enquanto soluções integradas podem operar diretamente sobre agendas clínicas, o protótipo prioriza a análise offline e a comparação transparente de estratégias de alocação.

Esta referência é exploratória e não constitui uma revisão exaustiva do mercado.

## 8. Limitações e segurança

O FilaFlux é um protótipo experimental, não um sistema de operação assistencial.

O aplicativo utiliza regras explícitas de compatibilidade e técnicas de otimização combinatória. **Não treina nem utiliza modelos preditivos de inteligência artificial ou aprendizado de máquina (IA/ML).**

Seus resultados não comprovam redução de filas, diminuição do tempo de espera ou melhoria no acesso aos serviços de saúde.

A aplicação de estratégias semelhantes em serviços reais exigiria, entre outros aspectos:

- Validação com profissionais e gestores de saúde.
- Definição de critérios assistenciais autorizados.
- Avaliação de equidade e possíveis barreiras de acesso.
- Adequação às exigências de segurança e privacidade.
- Validação operacional e institucional.
- Integração governada com os sistemas de origem, caso necessária.

**Não insira dados reais de pacientes na aplicação pública.**

## 9. Executar localmente

Requisitos: Python 3.10 ou superior.

Clone o repositório e instale as dependências:

```powershell
git clone https://github.com/jessicaandradeg-dot/filaflux.git
cd filaflux

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
python -m streamlit run app.py
```

### Habilitar a importação CSV

Para habilitar a funcionalidade em uma instalação local ou privada, configure a variável de ambiente antes de iniciar o aplicativo:

```powershell
$env:FILAFUX_ENABLE_REAL_DATA_UPLOAD = "1"
python -m streamlit run app.py
```

Para manter o modo desabilitado, não configure essa variável.

**Não habilite a importação CSV na publicação pública.**

## 10. Publicação no Streamlit Community Cloud

A aplicação publicada está disponível publicamente:

[https://filaflux-saude.streamlit.app/](https://filaflux-saude.streamlit.app/)

A publicação utiliza cenários sintéticos e permite consultar fontes públicas agregadas do SUS mediante ação do visitante.

A importação de arquivos CSV deve permanecer desabilitada nessa instância.

## 11. Testes automatizados

Para executar os testes:

```powershell
python -m pytest
```

A suíte contempla testes de:

- Compatibilidade entre vagas e pessoas.
- Fluxo de ofertas e respostas.
- Validação dos arquivos CSV.
- Cálculo de indicadores.
- Reprodutibilidade dos cenários.
- Otimização multicritério.
- Agregação segura de dados públicos.

Os testes não dependem de chamadas de rede, permitindo verificar o comportamento dos componentes em ambiente controlado.

## 12. Próximos passos

Antes de considerar um piloto em ambiente real, são necessários:

1. Validar as regras de compatibilidade com profissionais e gestores de saúde.
2. Avaliar o comportamento das estratégias com dados operacionais autorizados.
3. Investigar critérios de equidade, segurança e adequação assistencial.
4. Definir requisitos institucionais para tratamento e proteção dos dados.
5. Avaliar a necessidade de integração com agendas e sistemas de regulação, incluindo mecanismos de auditoria e governança.

O FilaFlux é uma demonstração de conceito que busca tornar mais transparentes as decisões de alocação e oferecer uma base para discussão e avaliação de possíveis estratégias de reaproveitamento de vagas.
