# Acolhe+ · Recepção UBS (Python)

Aplicação de terminal que simula a rotina diária da recepção de uma Unidade Básica de Saúde (UBS) no **Acolhe+**, solução desenvolvida para a Global Solution 2026/2 da FIAP (tema CitizenTech), na disciplina **Computational Thinking Using Python**.

O Acolhe+ orienta o cidadão sobre onde buscar atendimento no SUS e, nos casos de baixa gravidade (verde e azul), oferece uma consulta na UBS aproveitando os horários perdidos por falta. Esta aplicação reúne as regras que fazem esse reaproveitamento funcionar no dia a dia da unidade.

## Funcionalidades

| Menu | O que faz |
| --- | --- |
| **1. Agenda do dia** | Ver os horários de hoje e agendar consultas em horários livres ou liberados, com cálculo do risco de falta |
| **2. Confirmações** | Ver as consultas pendentes (risco alto primeiro), registrar confirmações, liberar horários não confirmados no prazo e ajustar o relógio simulado |
| **3. Comparecimento** | Registrar presença ou falta. O horário de quem faltou volta para encaixe |
| **4. Lista do dia** | Incluir cidadãos (verde ou azul), ver a lista por prioridade e ofertar vagas liberadas |
| **5. Relatórios** | Taxa de absenteísmo, taxa de reaproveitamento, pessoas não encaixadas e encerramento do dia, com relatório em JSON |

## Principais regras

- **Agenda:** dias úteis (seg a sex), 14 horários por dia, das 8h às 11h e das 13h às 16h, aberta para os próximos 7 dias.
- **Risco de falta:** 1 ponto por falta anterior + 1 ponto se for a primeira consulta na UBS. Com 2 pontos ou mais, o risco é **ALTO**; abaixo disso, **BAIXO**.
- **Confirmação (em dias úteis):**
  - pedido de confirmação 3 dias úteis antes (risco alto) ou 2 dias úteis antes (risco baixo);
  - prazo para confirmar até 1 dia útil antes da consulta;
  - consulta marcada para o mesmo dia dispensa confirmação.
- **Liberação:** consulta não confirmada no prazo tem o horário liberado, **exceto** a de paciente sem contato.
- **Lista do dia:** ordem de prioridade:
  1. quem não foi encaixado no dia anterior;
  2. verde antes de azul;
  3. ordem de chegada.
- **Oferta de vagas:** se a pessoa recusar ou não responder, a vaga passa ao próximo da lista. Quem aceita é encaixado, e o horário liberado passa a **REAPROVEITADO**.
- **Encerramento:** quem não foi encaixado ganha prioridade na lista do dia seguinte.

## Estrutura do projeto

```
├── main.py          # Ponto de entrada: prepara o dia e exibe o menu principal
├── menus.py         # Submenus e telas (entrada do usuário e exibição)
├── regras.py        # Regras de negócio (sem input/print)
├── relatorios.py    # Cálculo dos indicadores e relatório do dia
├── dados.py         # Leitura/gravação dos JSON e constantes do sistema
├── validacoes.py    # Validação e leitura segura das entradas
├── interface.py     # Limpar tela, pausar, títulos e tabelas
└── dados.json       # Estado atual: configuração, horários, consultas e lista do dia
```

Arquivos gerados durante o uso:
- `lista_proximo_dia.json`: pessoas não encaixadas, com prioridade no dia seguinte;
- `relatorio_AAAA-MM-DD.json`: relatório gerado ao encerrar o dia.

## Requisitos

- **Python 3.10 ou superior**, necessário para o `match-case`
- Sem bibliotecas externas: usa apenas `json`, `os` e `datetime`

## Como executar

Na pasta do projeto:

```bash
python main.py
```

Em alguns sistemas Linux e macOS, use `python3 main.py`.

Navegue digitando o número da opção e pressionando ENTER. A opção **0** volta ou sai. Os dados são salvos automaticamente após cada operação.

## Demonstração rápida

A UBS não atende no fim de semana, e os prazos dependem da data. Por isso, use o **relógio simulado** para ver todas as regras em qualquer dia:

1. *Confirmações → Ajustar data/hora*: `23/11/2026 08:00` (segunda-feira).
2. Ajuste de novo para `25/11/2026 08:00` (quarta-feira).
3. *Confirmações → Liberar consultas não confirmadas*: os horários são liberados.
4. *Lista do dia → Incluir cidadão* (cartão SUS com 15 dígitos) e *Ofertar vaga liberada*.
5. Ajuste para `25/11/2026 10:30` e registre presença e falta em *Comparecimento*.
6. *Relatórios*: veja os indicadores e encerre o dia.

Para voltar ao relógio real, ajuste a data/hora e pressione ENTER sem digitar nada.

## Limitações desta versão

- Atende a uma única UBS, com dados fictícios para demonstração.
- O risco de falta usa uma regra de pontos no lugar do modelo de aprendizado de máquina da solução.
- Não envia mensagens ou lembretes ao cidadão: a confirmação é registrada pela recepção.

## Outras partes do Acolhe+

Na solução completa, essas regras fazem parte da API Java e do painel da recepção, com banco de dados Oracle e modelos de IA servidos por uma API Flask. Esta aplicação permite testar as regras de forma independente da interface.