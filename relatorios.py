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
