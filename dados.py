"""Leitura e gravação dos arquivos JSON + constantes fixas do sistema.

Arquivos (sempre na mesma pasta dos .py, não importa de onde o programa roda):
- dados.json: configuração, horários, consultas e lista do dia (estado atual).
- lista_proximo_dia.json: pessoas não encaixadas que entram com prioridade
  na lista do dia seguinte.

Ao encerrar a agenda do dia também é gerado um relatório em JSON
(relatorio_AAAA-MM-DD.json), na mesma pasta.
"""
import json
import os

ARQUIVO = "dados.json"
ARQUIVO_PROXIMO_DIA = "lista_proximo_dia.json"

# Tuplas: valores fixos (nunca mudam durante a execução)
CORES = ("VERDE", "AZUL")
STATUS_CONSULTA = ("AGENDADA", "CONFIRMADA", "LIBERADA", "REALIZADA", "FALTA")
STATUS_HORARIO = ("LIVRE", "AGENDADO", "LIBERADO", "REAPROVEITADO")
STATUS_LISTA = ("AGUARDANDO", "ENCAIXADO", "NAO_ENCAIXADO")

# Formato de data/hora guardado no JSON (ex.: "2026-11-10 08:00")
FORMATO_DATA_HORA = "%Y-%m-%d %H:%M"

# Regra de negócio: antecedência (em horas) para pedir confirmação por risco
PRAZO_CONFIRMACAO = {"ALTO": 72, "BAIXO": 48}
# Regra de negócio: consulta marcada com menos de 24h dispensa confirmação
LIMITE_DISPENSA_H = 24


def dados_vazios() -> dict:
    """Devolve a estrutura inicial usada quando o dados.json não existe."""
    return {
        "config": {"ubs": "UBS", "prazo_oferta_min": 30, "antecedencia_min": 60,
                   "agora_simulado": "", "dia_fechado": False},
        "horarios": [],
        "consultas": [],
        "lista_dia": [],
    }


def ler_arquivo(caminho: str, padrao):
    """Lê um JSON. Se não existir ou estiver quebrado, devolve o valor padrão."""
    if not os.path.exists(caminho):
        return padrao
    try:
        with open(caminho, "r", encoding="utf-8") as arq:
            return json.load(arq)
    except (json.JSONDecodeError, OSError):
        print(f"Aviso: não foi possível ler {os.path.basename(caminho)}. Usando dados vazios.")
        return padrao


def gravar_arquivo(caminho: str, conteudo) -> None:
    """Grava o conteúdo (dict ou list) em JSON com acentos legíveis."""
    with open(caminho, "w", encoding="utf-8") as arq:
        json.dump(conteudo, arq, ensure_ascii=False, indent=2)


def carregar_json() -> dict:
    """Lê o dados.json ao abrir o sistema."""
    return ler_arquivo(ARQUIVO, dados_vazios())


def salvar_json(dados: dict) -> None:
    """Grava o dados.json. Chamado após cada operação que altera algo."""
    gravar_arquivo(ARQUIVO, dados)


def carregar_proximo_dia() -> list:
    """Lê a lista de pessoas que ficaram com prioridade para hoje."""
    return ler_arquivo(ARQUIVO_PROXIMO_DIA, [])


def salvar_proximo_dia(pessoas: list) -> None:
    """Grava as pessoas não encaixadas, que entram com prioridade no próximo dia."""
    gravar_arquivo(ARQUIVO_PROXIMO_DIA, pessoas)


def salvar_relatorio_dia(relatorio: dict) -> str:
    """Grava o relatório de encerramento em relatorio_AAAA-MM-DD.json.

    Devolve o nome do arquivo criado (usa a data que está dentro do relatório).
    """
    nome_arquivo = f"relatorio_{relatorio['data']}.json"
    gravar_arquivo(nome_arquivo, relatorio)
    return nome_arquivo
