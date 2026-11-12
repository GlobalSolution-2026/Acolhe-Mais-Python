"""Indicadores e relatório de encerramento do dia.

Contém os cálculos dos indicadores pedidos (Tabela 5 do texto):
- taxa de absenteísmo (faltas sobre consultas com desfecho);
- taxa de reaproveitamento de horários (vagas liberadas que foram reocupadas);
- pessoas não encaixadas no dia.

Também monta o relatório final do dia (montar_relatorio_dia), que o dados.py
grava em um arquivo JSON quando a agenda é encerrada.

Aqui só existem cálculos: nada é impresso nem lido do teclado (isso fica
no menus.py), o que deixa as funções fáceis de testar.
"""


def contar_status(consultas: list, status: str) -> int:
    """Conta quantas consultas estão com o status informado."""
    total = 0
    for consulta in consultas:
        if consulta["ds_status"] == status:
            total += 1
    return total


def calcular_absenteismo(consultas: list) -> float:
    """Taxa de absenteísmo: faltas / (realizadas + faltas) * 100."""
    faltas = contar_status(consultas, "FALTA")
    realizadas = contar_status(consultas, "REALIZADA")
    total = faltas + realizadas
    if total == 0:
        return 0.0
    return faltas / total * 100


def calcular_reaproveitamento(horarios: list) -> float:
    """Taxa de reaproveitamento: reaproveitados / (liberados + reaproveitados) * 100."""
    reaproveitados = 0
    liberados = 0
    for horario in horarios:
        if horario["ds_status"] == "REAPROVEITADO":
            reaproveitados += 1
            liberados += 1
        elif horario["ds_status"] == "LIBERADO":
            liberados += 1
    if liberados == 0:
        return 0.0
    return reaproveitados / liberados * 100


def listar_nao_encaixados(lista_dia: list) -> list:
    """Pessoas da lista do dia que terminaram NAO_ENCAIXADO."""
    resultado = []
    for pessoa in lista_dia:
        if pessoa["ds_status"] == "NAO_ENCAIXADO":
            resultado.append(pessoa)
    return resultado


def montar_relatorio_dia(dados: dict, data_texto: str, gerado_em: str) -> dict:
    """Monta o relatório de encerramento do dia (dicionário pronto para virar JSON).

    data_texto: dia da agenda, formato AAAA-MM-DD. gerado_em: data/hora da geração.
    Deve ser chamada depois de fechar_dia, para a lista já trazer os NAO_ENCAIXADO.
    """
    faltas = contar_status(dados["consultas"], "FALTA")
    realizadas = contar_status(dados["consultas"], "REALIZADA")
    reaproveitados = 0
    liberados = 0
    for horario in dados["horarios"]:
        if horario["ds_status"] == "REAPROVEITADO":
            reaproveitados += 1
            liberados += 1
        elif horario["ds_status"] == "LIBERADO":
            liberados += 1
    nao_encaixados = []
    for pessoa in listar_nao_encaixados(dados["lista_dia"]):
        nao_encaixados.append({
            "nm_cidadao": pessoa["nm_cidadao"],
            "nr_cns": pessoa["nr_cns"],
            "ds_cor": pessoa["ds_cor"],
            "hr_chegada": pessoa["hr_chegada"],
        })
    return {
        "ubs": dados["config"]["ubs"],
        "data": data_texto,
        "gerado_em": gerado_em,
        "indicadores": {
            "consultas_realizadas": realizadas,
            "faltas": faltas,
            "taxa_absenteismo": round(calcular_absenteismo(dados["consultas"]), 1),
            "horarios_liberados": liberados,
            "horarios_reaproveitados": reaproveitados,
            "taxa_reaproveitamento": round(calcular_reaproveitamento(dados["horarios"]), 1),
        },
        "nao_encaixados": nao_encaixados,
        "lista_dia": dados["lista_dia"],
        "consultas": dados["consultas"],
        "horarios": dados["horarios"],
    }
