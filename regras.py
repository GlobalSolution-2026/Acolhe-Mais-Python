"""Regras de negócio: agenda, confirmação, liberação e lista do dia."""
from datetime import datetime

from dados import PRAZO_CONFIRMACAO, LIMITE_DISPENSA_H, FORMATO_DATA_HORA, CORES


# ---------- relógio do sistema ----------
def agora(dados: dict) -> datetime:
    """Data/hora atual do sistema.

    Se existir 'agora_simulado' no config, usa ele (serve para demonstrar as regras
    de prazo sempre do mesmo jeito). Se estiver vazio, usa o relógio real.
    """
    simulado = dados["config"].get("agora_simulado", "")
    if simulado != "":
        return datetime.strptime(simulado, FORMATO_DATA_HORA)
    return datetime.now()


def definir_relogio(dados: dict, texto_digitado: str) -> None:
    """Define o relógio simulado a partir de 'DD/MM/AAAA HH:MM' (vazio = relógio real)."""
    if texto_digitado == "":
        dados["config"]["agora_simulado"] = ""
    else:
        momento = datetime.strptime(texto_digitado, "%d/%m/%Y %H:%M")
        dados["config"]["agora_simulado"] = momento.strftime(FORMATO_DATA_HORA)


def momento_do_horario(horario: dict) -> datetime:
    """Converte o 'dt_horario' (texto do JSON) em datetime."""
    return datetime.strptime(horario["dt_horario"], FORMATO_DATA_HORA)


def horas_ate_consulta(dados: dict, horario: dict) -> float:
    """Quantas horas faltam do 'agora' até o horário da consulta (negativo = já passou)."""
    diferenca = momento_do_horario(horario) - agora(dados)
    return diferenca.total_seconds() / 3600


# ---------- buscas ----------
def buscar_horario(dados: dict, id_horario: int) -> dict:
    """Devolve o horário com esse id, ou None se não existir."""
    for horario in dados["horarios"]:
        if horario["id_horario"] == id_horario:
            return horario
    return None


def buscar_consulta(dados: dict, id_consulta: int) -> dict:
    """Devolve a consulta com esse id, ou None se não existir."""
    for consulta in dados["consultas"]:
        if consulta["id_consulta"] == id_consulta:
            return consulta
    return None


def consulta_ativa_do_horario(dados: dict, id_horario: int) -> dict:
    """Consulta que está ocupando o horário (ignora as já LIBERADAS). None se não há."""
    for consulta in dados["consultas"]:
        if consulta["id_horario"] == id_horario and consulta["ds_status"] != "LIBERADA":
            return consulta
    return None


def proximo_id(lista: list, campo: str) -> int:
    """Próximo id disponível: maior valor de 'campo' na lista + 1."""
    maior = 0
    for item in lista:
        if item[campo] > maior:
            maior = item[campo]
    return maior + 1


def cartoes_cadastrados(lista_dia: list) -> set:
    """Set de cartões SUS já na lista do dia (barra duplicidade)."""
    cartoes = set()
    for pessoa in lista_dia:
        cartoes.add(pessoa["nr_cns"])
    return cartoes


# ---------- risco ----------
def calcular_risco(faltas_anteriores: int, primeira_vez: bool) -> str:
    """Classifica o risco de FALTA do paciente em ALTO ou BAIXO.

    Pontos: 1 por falta anterior + 1 se for a primeira consulta do paciente na UBS
    (ainda sem vínculo). 2 pontos ou mais = ALTO; senão BAIXO.
    """
    pontos = faltas_anteriores
    if primeira_vez:
        pontos += 1
    if pontos >= 2:
        return "ALTO"
    return "BAIXO"


# ---------- agenda ----------
def horarios_disponiveis(dados: dict) -> list:
    """Horários em que dá para agendar: LIVRE e LIBERADO (vaga devolvida)."""
    disponiveis = []
    for horario in dados["horarios"]:
        if horario["ds_status"] == "LIVRE" or horario["ds_status"] == "LIBERADO":
            disponiveis.append(horario)
    return disponiveis


def agendar_consulta(dados: dict, id_horario: int, nome: str, cns: str,
                     faltas: int, primeira_vez: bool, contato: bool) -> dict:
    """Cria a consulta no horário escolhido e devolve o dicionário criado.

    Regra: consulta marcada com menos de 24h de antecedência dispensa confirmação
    (já nasce CONFIRMADA). Caso contrário nasce AGENDADA, aguardando confirmação.
    """
    horario = buscar_horario(dados, id_horario)
    horas = horas_ate_consulta(dados, horario)
    if horas < LIMITE_DISPENSA_H:
        status = "CONFIRMADA"
        dispensada = True
    else:
        status = "AGENDADA"
        dispensada = False
    consulta = {
        "id_consulta": proximo_id(dados["consultas"], "id_consulta"),
        "id_horario": id_horario,
        "nm_paciente": nome,
        "nr_cns": cns,
        "nr_faltas_anteriores": faltas,
        "fl_primeira_vez": primeira_vez,
        "ds_risco": calcular_risco(faltas, primeira_vez),
        "tem_contato": contato,
        "ds_status": status,
        "fl_confirmacao_dispensada": dispensada,
    }
    dados["consultas"].append(consulta)
    horario["ds_status"] = "AGENDADO"
    return consulta


# ---------- confirmações ----------
def exige_confirmacao(consulta: dict) -> bool:
    """True se a consulta ainda precisa de confirmação (AGENDADA e não dispensada)."""
    if consulta["ds_status"] != "AGENDADA":
        return False
    if consulta["fl_confirmacao_dispensada"]:
        return False
    return True


def consultas_pendentes(dados: dict) -> list:
    """Consultas pendentes de confirmação, risco ALTO primeiro e depois BAIXO."""
    pendentes = []
    for consulta in dados["consultas"]:
        if exige_confirmacao(consulta) and consulta["ds_risco"] == "ALTO":
            pendentes.append(consulta)
    for consulta in dados["consultas"]:
        if exige_confirmacao(consulta) and consulta["ds_risco"] == "BAIXO":
            pendentes.append(consulta)
    return pendentes


def confirmar_consulta(dados: dict, id_consulta: int) -> bool:
    """Marca a consulta como CONFIRMADA. Devolve False se ela não aceita confirmação."""
    consulta = buscar_consulta(dados, id_consulta)
    if consulta is None or not exige_confirmacao(consulta):
        return False
    consulta["ds_status"] = "CONFIRMADA"
    return True


def prazo_vencido(dados: dict, consulta: dict) -> bool:
    """True se a consulta já entrou na janela de confirmação e ainda não confirmou.

    Risco ALTO pede confirmação 72h antes; BAIXO, 48h antes. Se faltam menos horas
    que o prazo (e a consulta ainda não passou), o prazo venceu.
    """
    horario = buscar_horario(dados, consulta["id_horario"])
    horas = horas_ate_consulta(dados, horario)
    return 0 < horas <= PRAZO_CONFIRMACAO[consulta["ds_risco"]]


def consultas_para_liberar(dados: dict) -> tuple:
    """Separa as consultas com prazo vencido em (liberáveis, protegidas).

    Regra: paciente sem contato não tem a vaga liberada (vai para 'protegidas').
    """
    liberaveis = []
    protegidas = []
    for consulta in dados["consultas"]:
        if exige_confirmacao(consulta) and prazo_vencido(dados, consulta):
            if consulta["tem_contato"]:
                liberaveis.append(consulta)
            else:
                protegidas.append(consulta)
    return liberaveis, protegidas


def liberar_consulta(dados: dict, consulta: dict) -> None:
    """Marca a consulta como LIBERADA e o horário dela como LIBERADO."""
    consulta["ds_status"] = "LIBERADA"
    horario = buscar_horario(dados, consulta["id_horario"])
    horario["ds_status"] = "LIBERADO"


# ---------- comparecimento ----------
def consultas_do_comparecimento(dados: dict) -> list:
    """Consultas que ainda aguardam registro de presença ou falta."""
    lista = []
    for consulta in dados["consultas"]:
        if consulta["ds_status"] == "AGENDADA" or consulta["ds_status"] == "CONFIRMADA":
            lista.append(consulta)
    return lista


def registrar_presenca(consulta: dict) -> None:
    """Consulta passa para REALIZADA."""
    consulta["ds_status"] = "REALIZADA"


def registrar_falta(consulta: dict) -> None:
    """Consulta passa para FALTA."""
    consulta["ds_status"] = "FALTA"


# ---------- lista do dia ----------
def incluir_na_lista(dados: dict, nome: str, cns: str, cor: str) -> dict:
    """Inclui o cidadão no fim da lista (a ordem da lista é a ordem de chegada)."""
    pessoa = {
        "nm_cidadao": nome,
        "nr_cns": cns,
        "ds_cor": cor,
        "hr_chegada": agora(dados).strftime("%H:%M"),
        "ds_status": "AGUARDANDO",
        "fl_prioridade_amanha": False,
    }
    dados["lista_dia"].append(pessoa)
    return pessoa


def ordenar_lista(lista: list) -> list:
    """Devolve a lista na ordem de prioridade, sem sort/lambda.

    Ordem: 1) quem ficou com prioridade do dia anterior, 2) os demais.
    Dentro de cada grupo: VERDE primeiro e depois AZUL, sempre por ordem de chegada
    (que é a ordem em que a lista foi preenchida).
    """
    ordenada = []
    for prioridade in (True, False):
        for cor in CORES:
            for pessoa in lista:
                if pessoa["fl_prioridade_amanha"] == prioridade and pessoa["ds_cor"] == cor:
                    ordenada.append(pessoa)
    return ordenada


def proximo_da_lista(lista: list, ignorados: set) -> dict:
    """Primeiro AGUARDANDO na ordem de prioridade que ainda não recebeu a oferta.

    'ignorados' é um set com os cartões SUS de quem já recusou/não respondeu.
    Devolve None quando não sobra ninguém.
    """
    for pessoa in ordenar_lista(lista):
        if pessoa["ds_status"] == "AGUARDANDO" and pessoa["nr_cns"] not in ignorados:
            return pessoa
    return None


def horarios_liberados(dados: dict) -> list:
    """Horários com status LIBERADO (vagas que podem ser ofertadas)."""
    liberados = []
    for horario in dados["horarios"]:
        if horario["ds_status"] == "LIBERADO":
            liberados.append(horario)
    return liberados


def encaixar(pessoa: dict, horario: dict) -> None:
    """Cidadão aceitou a vaga: ele fica ENCAIXADO e o horário REAPROVEITADO."""
    pessoa["ds_status"] = "ENCAIXADO"
    pessoa["fl_prioridade_amanha"] = False
    horario["ds_status"] = "REAPROVEITADO"


def fechar_dia(dados: dict) -> list:
    """Fecha o dia: quem não foi encaixado vira NAO_ENCAIXADO com prioridade.

    Devolve a lista de cópias dessas pessoas (já prontas para o dia seguinte).
    A lista também é guardada em dados["lista_proximo_dia"] (salva no dados.json).
    """
    para_amanha = []
    for pessoa in dados["lista_dia"]:
        if pessoa["ds_status"] == "AGUARDANDO":
            pessoa["ds_status"] = "NAO_ENCAIXADO"
            pessoa["fl_prioridade_amanha"] = True
            copia = dict(pessoa)
            copia["ds_status"] = "AGUARDANDO"
            para_amanha.append(copia)
    dados["config"]["dia_fechado"] = True
    dados["lista_proximo_dia"] = para_amanha
    return para_amanha


def iniciar_novo_dia(dados: dict) -> int:
    """Prepara a lista do dia ao abrir o sistema.

    - Se o dia anterior foi fechado, a lista começa vazia.
    - Pessoas guardadas em dados["lista_proximo_dia"] entram na lista
      (sem duplicar o cartão SUS) e a lista do próximo dia é esvaziada.
    Devolve quantas pessoas entraram com prioridade.
    """
    if dados["config"].get("dia_fechado", False):
        dados["lista_dia"] = []
        dados["config"]["dia_fechado"] = False
    cartoes = cartoes_cadastrados(dados["lista_dia"])
    entraram = 0
    for pessoa in dados.get("lista_proximo_dia", []):
        if pessoa["nr_cns"] not in cartoes:
            dados["lista_dia"].append(pessoa)
            cartoes.add(pessoa["nr_cns"])
            entraram += 1
    dados["lista_proximo_dia"] = []
    return entraram
