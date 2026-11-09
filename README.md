# FilaFlux

**Simulador de alocação operacional para vagas de consultas canceladas.**
O FilaFlux demonstra como regras transparentes de compatibilidade e otimização
podem ajudar uma equipe a avaliar o reaproveitamento de vagas. A demonstração
usa exclusivamente dados sintéticos e não se conecta a agendas, filas ou
sistemas de saúde reais.

> **Em uma frase:** compare uma fila sequencial com estratégias de alocação em
> lote, observe quem poderia ser compatível com uma vaga fictícia e explore como
> os resultados mudam em diferentes cenários simulados.

## O que está sendo demonstrado

1. **Fluxo operacional de uma vaga cancelada:** a equipe seleciona a vaga
   fictícia, visualiza a próxima pessoa compatível e registra uma oferta simulada.
   Pode registrar aceite ou recusa; a pendência reserva a pessoa e a recusa
   permite avançar na fila.
2. **Compatibilidade explicável:** serviço, data e período precisam coincidir.
   Necessidades sintéticas de acessibilidade são requisitos obrigatórios.
3. **Comparação de políticas:** o mesmo conjunto de vagas e disponibilidades é
   avaliado pela alocação sequencial, pelo emparelhamento de máximo preenchimento
   e por uma otimização multicritério experimental.
4. **Perfil de disponibilidade:** contagem agregada de vagas, pessoas
   compatíveis e pares pessoa-vaga por serviço, data, período e unidade fictícia.
5. **Indicadores descritivos:** preenchimento, respostas a ofertas e distribuição
   de oportunidades entre grupos territoriais fictícios.
6. **Simulação em múltiplos cenários:** repetição reprodutível da comparação de
   políticas, com média, mediana, amplitude e frequência dos melhores
   preenchimentos no conjunto simulado.

## Para quem e para qual problema

Cancelamentos de consultas podem deixar horários vagos enquanto pessoas
aguardam atendimento. O conceito do FilaFlux é apoiar a análise operacional de
como identificar encaixes compatíveis e comparar regras de reaproveitamento.
Em um serviço real, a equipe responsável continuaria no controle das decisões,
das regras autorizadas e do contato com as pessoas.

O protótipo **não** demonstra que filas reais serão reduzidas. Não faz contato,
não consulta sistemas reais, não estima urgência, não define prioridade clínica
e não substitui profissionais. Seu propósito é tornar explícitas as regras,
trade-offs e perguntas que precisariam ser validadas antes de qualquer piloto.

## Como funcionam as políticas

- **Fila sequencial:** percorre as vagas na ordem gerada e atribui a cada uma a
  primeira pessoa compatível ainda não utilizada. É simples, mas uma escolha
  flexível para uma vaga pode impedir outro encaixe.
- **Lote máximo:** considera as vagas em conjunto e busca maximizar o total de
  encaixes compatíveis, usando cada pessoa no máximo uma vez.
- **Multicritério experimental:** primeiro maximiza o total preenchido; entre
  soluções com esse total, minimiza a soma das posições de fila fornecidas no
  cenário; depois minimiza conflitos com preferências fictícias de unidade e
  período. As necessidades de acessibilidade são restrições obrigatórias.

A ordem de fila é apenas um atributo fornecido pelo cenário — o sistema não
calcula prioridade clínica. O critério multicritério é uma hipótese para
discussão, não uma regra assistencial recomendada ou aprovada.

## O que os números significam (e não significam)

- **Vagas alocadas:** quantidade de pares compatíveis encontrados pela política
  no cenário.
- **Dias potenciais:** diferença hipotética entre uma data-base sintética e a
  data da vaga; não representa tempo de espera real nem dias efetivamente
  evitados.
- **Amplitude entre grupos:** diferença descritiva entre taxas de ofertas por
  oportunidades fictícias. Não é uma medida validada de equidade e não ajusta
  por necessidade, disponibilidade, barreiras de acesso ou contexto social.
- **Simulação em múltiplos cenários:** análise de sensibilidade condicionada às
  distribuições artificiais programadas. Não é estimativa de impacto no SUS,
  avaliação causal, probabilidade de sucesso no mundo real ou validação externa.

Os resultados servem para demonstrar o funcionamento do software e discutir
trade-offs. Não devem ser interpretados como evidência clínica ou operacional.

## Dados, IA e segurança

- Todos os nomes, filas, grupos, vagas, preferências e datas da demonstração são
  fictícios. Não insira dados pessoais ou dados reais de pacientes.
- O projeto usa regras explícitas de compatibilidade e otimização combinatória.
  **Não treina nem utiliza modelo preditivo de IA/ML.**
- Dados sintéticos não permitem avaliar validade, calibração, viés ou utilidade
  de um modelo clínico ou operacional. A inclusão futura de previsões exigiria
  uma pergunta bem definida, dados autorizados, governança e validação adequada.
- Nenhuma decisão automática de diagnóstico, prescrição ou prioridade clínica é
  produzida.

## Executar localmente

Requer Python 3.10 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m streamlit run app.py
```

Abra o endereço local mostrado pelo Streamlit (normalmente
`http://localhost:8501`).

## Testes

```powershell
python -m pytest
```

Os testes cobrem compatibilidade, fluxo de ofertas, indicadores, reprodutibilidade
dos cenários e objetivos da otimização multicritério, incluindo comparação com
enumeração exaustiva em cenários pequenos.

## Estrutura do projeto

```text
app.py                       Interface Streamlit
src/filaflux/                Regras, modelos, métricas e simuladores
tests/                       Testes automatizados
pyproject.toml               Dependências e metadados do pacote
```

## Próximos passos antes de um piloto real

Validar o processo com profissionais e gestores; definir regras autorizadas pelo
serviço; avaliar impactos sobre diferentes grupos; desenhar proteção de dados,
segurança e persistência; integrar sistemas somente com autorização e governança.
O protótipo atual não está pronto para uso assistencial.
