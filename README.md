# Vaga Viva

MVP de demonstração para reaproveitamento transparente de vagas de consultas
canceladas. O cenário usa dados inteiramente sintéticos: nenhuma pessoa ou
informação real de paciente é representada.

## Escopo desta etapa

- Sugere pessoas compatíveis por serviço, data e período.
- Mantém a ordem de fila fornecida pelo serviço; não estima prioridade clínica.
- Exibe os motivos de compatibilidade e oferece somente à próxima pessoa elegível.
- Registra ofertas pendentes, aceitas ou recusadas e mantém o histórico no cenário.
- Uma oferta pendente reserva a pessoa; uma recusa permite avançar para a próxima
  pessoa compatível.
- Impede uma pessoa com oferta pendente ou aceita de receber outra oferta ao
  mesmo tempo no cenário.
- Exibe indicadores operacionais do cenário e a distribuição descritiva de ofertas
  entre territórios fictícios.
- Apresenta perfil agregado de disponibilidade por serviço/data/período/unidade
  sintética e contagem descritiva de oportunidades por grupo fictício.
- Gera cenários sintéticos reproduzíveis e compara alocação sequencial, máximo
  preenchimento em lote e uma regra experimental multicritério.
- Considera preferências declaradas de turno/unidade somente como desempate e
  trata recursos de acessibilidade necessários como requisitos obrigatórios.
- Permite repetir a comparação em vários cenários sintéticos para observar a
  variação dos resultados simulados.

## Executar localmente

Requer Python 3.10 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m streamlit run app.py
```

## Testes

```powershell
python -m pytest
```

## Limites conhecidos

Este MVP não envia mensagens, acessa agendas reais, determina prioridade
clínica nem demonstra redução real de espera. Ofertas e respostas são simuladas
e o histórico existe apenas durante a sessão do navegador. Um uso real exigiria
validação do fluxo por profissionais, persistência segura e governança adequada.

Os indicadores e grupos territoriais são apenas uma demonstração. A taxa de
ofertas por oportunidade conta pares sintéticos pessoa-vaga compatíveis; não é
uma medida de equidade, não controla diferenças de disponibilidade ou critérios
operacionais e não sustenta conclusões sobre populações reais. Amostras pequenas
devem ser interpretadas somente como teste visual do produto.

## Indicadores da demonstração

- **Preenchimento:** vagas aceitas divididas pelas vagas canceladas no cenário.
- **Aceite entre respostas:** ofertas aceitas divididas por ofertas aceitas ou
  recusadas; ofertas pendentes não entram no denominador.
- **Ofertas por vaga preenchida:** tentativas de oferta para vagas aceitas
  divididas por essas vagas.
- **Distribuição sintética:** ofertas emitidas divididas por pares
  pessoa-vaga compatíveis inicialmente observados em cada grupo fictício.

Os indicadores descrevem apenas as interações registradas na sessão atual.
Não comparam o produto a uma política real ou a um grupo de controle.
O perfil de disponibilidade conta, para cada combinação de serviço, data,
período e unidade sintética, quantas pessoas e pares pessoa-vaga são compatíveis
com as disponibilidades e requisitos de acessibilidade fornecidos.

O painel de grupos fictícios mostra pessoas no grupo, pessoas com ao menos uma
oportunidade, pares pessoa-vaga elegíveis e ofertas emitidas. A amplitude entre
as taxas é descritiva e não é uma métrica de equidade: não ajusta por necessidade,
preferências, transporte, contexto social ou regras de cada serviço. Em especial,
sem ofertas observadas a amplitude aparece como N/D.

## Simulador de políticas

Na seção **Simulador: comparar políticas de alocação**, escolha o número de vagas,
o tamanho da fila e a semente. O cenário inicial usa semente 7, 10 vagas e 10
pessoas para ilustrar uma diferença entre as estratégias. A mesma combinação
gera o mesmo cenário:

- **Fila sequencial:** percorre as vagas na ordem gerada e aloca a primeira pessoa
  compatível ainda não alocada.
- **Lote máximo:** procura um emparelhamento que maximize a quantidade de vagas
  preenchidas, respeitando serviço, data, período, acessibilidade e uso único de
  cada pessoa.
- **Multicritério experimental:** primeiro maximiza a quantidade preenchida; entre
  essas soluções, minimiza a soma das posições da fila; por fim, minimiza
  incompatibilidades com preferências declaradas de turno/unidade. A prioridade
  de fila é fornecida pelo serviço e não é inferida pelo sistema.
- A interface expõe a soma das posições e o número de conflitos de preferências
  da solução multicritério para deixar visíveis os objetivos secundários.

A interface também exibe dias potenciais entre a data de referência hipotética
de cada pessoa e a data da vaga alocada. Esse número é um contrafactual sintético,
não uma estimativa de espera real nem de dias efetivamente evitados.

Na seção **Simulação de impacto em múltiplos cenários**, é possível comparar as
três políticas em até 100 cenários gerados com sementes consecutivas. A tabela
resume média, mediana, mínimo/máximo, taxa média de preenchimento e frequência
com que cada política alcança o maior preenchimento observado (incluindo empates).
É uma análise de sensibilidade interna ao gerador sintético, não uma estimativa
de efeito no SUS, probabilidade de sucesso real ou avaliação causal.

A comparação não simula resposta a ofertas, necessidade clínica nem impacto
real. Nenhuma das estratégias otimiza equidade ou substitui uma regra assistencial
aprovada. A otimização multicritério é uma hipótese de produto para discussão;
uma implantação exigiria validação dos critérios e do fluxo por cada serviço,
além de avaliação das consequências para diferentes grupos.

## Por que não há modelo preditivo

O protótipo não treina nem apresenta um modelo de Machine Learning. Dados
fabricados para a demonstração não permitem avaliar validade externa, calibração,
viés ou utilidade operacional. Uma previsão só deve ser considerada após definir
um desfecho operacional não clínico, obter dados autorizados e representativos,
estabelecer governança e desenhar validação temporal e por grupos, com supervisão
dos serviços. Nenhuma previsão deve determinar prioridade clínica ou substituir
decisão profissional.
