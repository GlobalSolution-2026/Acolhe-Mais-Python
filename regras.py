"""Regras de negócio do sistema: agenda, confirmação, liberação e lista do dia.

Principais regras:
- Risco de falta: 1 ponto por falta anterior + 1 se for a primeira consulta
  na UBS. Com 2 pontos ou mais o risco é ALTO; senão, BAIXO.
- Confirmação: risco ALTO precisa confirmar 72h antes e risco BAIXO, 48h antes.
  Consulta marcada com menos de 24h de antecedência dispensa confirmação.
- Liberação: consulta não confirmada no prazo tem a vaga liberada, mas
  paciente sem contato fica protegido (não perde a vaga).
- Lista do dia: ordem de prioridade = quem veio do dia anterior primeiro,
  depois VERDE antes de AZUL, sempre por ordem de chegada.
- Encerramento: quem não foi encaixado ganha prioridade no dia seguinte.

O relógio do sistema pode ser simulado (agora_simulado no config) para
demonstrar as regras de prazo sempre do mesmo jeito.
Aqui não tem input nem print: só regras que alteram e consultam os dados.
"""

from datetime import datetime, timedelta

from dados import (PRAZO_CONFIRMACAO, LIMITE_DISPENSA_H, FORMATO_DATA_HORA, CORES,
                   HORAS_ATENDIMENTO, DIAS_AGENDA, TOLERANCIA_ENCAIXE_MIN,
                   PREENCHER_EXEMPLO, NOMES_EXEMPLO, SOBRENOMES_EXEMPLO)


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
    """Consulta que está ocupando o horário (ignora LIBERADA e FALTA). None se não há."""
    for consulta in dados["consultas"]:
        if (consulta["id_horario"] == id_horario and consulta["ds_status"] != "LIBERADA"
                and consulta["ds_status"] != "FALTA"):
            return consulta
    return None


def consulta_ja_passou(dados: dict, consulta: dict) -> bool:
    """True se o horário da consulta já passou (ou é agora) pelo relógio do sistema."""
    horario = buscar_horario(dados, consulta["id_horario"])
    return horas_ate_consulta(dados, horario) <= 0


def consulta_ativa_no_dia(dados: dict, cns: str, dia) -> dict:
    """Consulta AGENDADA ou CONFIRMADA desse cartão SUS no dia informado (date).

    Devolve a consulta ou None. Serve para barrar agendamento duplicado no mesmo dia
    e para impedir que quem já tem consulta marcada hoje entre na fila do dia.
    """
    for consulta in dados["consultas"]:
        if consulta["nr_cns"] != cns:
            continue
        if consulta["ds_status"] != "AGENDADA" and consulta["ds_status"] != "CONFIRMADA":
            continue
        horario = buscar_horario(dados, consulta["id_horario"])
        if momento_do_horario(horario).date() == dia:
            return consulta
    return None


def proximo_id(lista: list, campo: str) -> int:
    """Próximo id disponível: maior valor de 'campo' na lista + 1."""
    maior = 0
    for item in lista:
        if item[campo] > maior:
            maior = item[campo]
    return maior + 1

def nome_do_cartao(dados: dict, cns: str) -> str:
    """Nome já cadastrado com esse cartão SUS (nas consultas ou na lista do dia).

    Devolve "" se o cartão ainda não foi usado. Serve para impedir que o mesmo
    cartão SUS seja usado por pessoas diferentes.
    """
    for consulta in dados["consultas"]:
        if consulta["nr_cns"] == cns:
            return consulta["nm_paciente"]
    for pessoa in dados["lista_dia"]:
        if pessoa["nr_cns"] == cns:
            return pessoa["nm_cidadao"]
    return ""


def cartao_de_outra_pessoa(dados: dict, cns: str, nome: str) -> bool:
    """True se o cartão SUS já pertence a alguém com outro nome."""
    cadastrado = nome_do_cartao(dados, cns)
    return cadastrado != "" and cadastrado.lower() != nome.strip().lower()

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
def inserir_em_ordem(horarios: list, novo: dict) -> None:
    """Insere o horário na posição certa para a lista continuar em ordem de data/hora.

    O texto 'AAAA-MM-DD HH:MM' pode ser comparado direto com > (a ordem do texto
    é a mesma ordem do tempo).
    """
    posicao = len(horarios)
    for indice in range(len(horarios)):
        if horarios[indice]["dt_horario"] > novo["dt_horario"]:
            posicao = indice
            break
    horarios.insert(posicao, novo)

def gerar_agenda(dados: dict) -> int:
    """Abre a agenda de hoje e dos próximos dias úteis, sem duplicar horários.

    Para cada dia de hoje até DIAS_AGENDA - 1 dias à frente (pulando sábado e
    domingo), cria os horários de HORAS_ATENDIMENTO que ainda não existem no JSON.
    Com PREENCHER_EXEMPLO ligado, cerca de 3 em cada 4 horários novos já nascem
    ocupados por um paciente fictício (como numa agenda real de UBS); os demais
    ficam LIVRES. Devolve quantos horários foram criados.
    """
    existentes = set()
    for horario in dados["horarios"]:
        existentes.add(horario["dt_horario"])
    hoje = agora(dados).date()
    criados = 0
    for i in range(DIAS_AGENDA):
        dia = hoje + timedelta(days=i)
        if dia.weekday() >= 5:  # 5 = sábado, 6 = domingo
            continue
        for posicao in range(len(HORAS_ATENDIMENTO)):
            texto = dia.strftime("%Y-%m-%d") + " " + HORAS_ATENDIMENTO[posicao]
            if texto in existentes:
                continue
            novo = {
                "id_horario": proximo_id(dados["horarios"], "id_horario"),
                "dt_horario": texto,
                "ds_status": "LIVRE",
            }
            inserir_em_ordem(dados["horarios"], novo)
            existentes.add(texto)
            criados += 1
            # 1 em cada 4 fica livre; a soma com o dia muda quais ficam livres a cada dia
            if PREENCHER_EXEMPLO and (posicao + dia.day) % 4 != 0:
                ocupar_com_exemplo(dados, novo)
    return criados


def ocupar_com_exemplo(dados: dict, horario: dict) -> None:
    """Agenda um paciente fictício no horário, usando as mesmas regras do agendamento.

    O número da nova consulta (n) escolhe o nome e o sobrenome, então cada
    consulta gerada tem um paciente diferente (até 80 combinações).
    Faltas, primeira vez e contato também variam com n, para ter risco ALTO,
    risco BAIXO e paciente sem contato na demonstração.
    """
    n = proximo_id(dados["consultas"], "id_consulta")
    nome = NOMES_EXEMPLO[(n * 7) % len(NOMES_EXEMPLO)]
    sobrenome = SOBRENOMES_EXEMPLO[(n * 3 + n // len(NOMES_EXEMPLO)) % len(SOBRENOMES_EXEMPLO)]
    cns = str(700000000001000 + n)          # 15 dígitos, um por consulta
    faltas = (0, 0, 1, 0, 2, 0, 3, 1)[n % 8]
    primeira_vez = n % 5 == 0
    contato = n % 7 != 0
    agendar_consulta(dados, horario["id_horario"], nome + " " + sobrenome, cns,
                     faltas, primeira_vez, contato)

def horarios_disponiveis(dados: dict) -> list:
    """Horários em que dá para agendar: LIVRE e LIBERADO (vaga devolvida)."""
    disponiveis = []
    for horario in dados["horarios"]:
        livre = horario["ds_status"] == "LIVRE" or horario["ds_status"] == "LIBERADO"
        if livre and horas_ate_consulta(dados, horario) > 0:
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
    """Consultas pendentes de confirmação, risco ALTO primeiro e depois BAIXO.

    Só entram consultas que ainda não passaram: confirmar um horário que já
    passou não faz sentido (nesse caso o próximo passo é registrar presença/falta).
    """
    pendentes = []
    for consulta in dados["consultas"]:
        if (exige_confirmacao(consulta) and consulta["ds_risco"] == "ALTO"
                and not consulta_ja_passou(dados, consulta)):
            pendentes.append(consulta)
    for consulta in dados["consultas"]:
        if (exige_confirmacao(consulta) and consulta["ds_risco"] == "BAIXO"
                and not consulta_ja_passou(dados, consulta)):
            pendentes.append(consulta)
    return pendentes


def confirmar_consulta(dados: dict, id_consulta: int) -> bool:
    """Marca a consulta como CONFIRMADA.

    Devolve False se ela não aceita confirmação (não está pendente ou o horário já passou).
    """
    consulta = buscar_consulta(dados, id_consulta)
    if consulta is None or not exige_confirmacao(consulta):
        return False
    if consulta_ja_passou(dados, consulta):
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
    """Consultas de hoje que aguardam registro de presença ou falta.

    Só entram as que já chegaram no horário (ou passaram): não dá para registrar
    presença ou falta de uma consulta que ainda não aconteceu.
    """
    hoje = agora(dados).date()
    lista = []
    for consulta in dados["consultas"]:
        aguardando = consulta["ds_status"] == "AGENDADA" or consulta["ds_status"] == "CONFIRMADA"
        horario = buscar_horario(dados, consulta["id_horario"])
        do_dia = momento_do_horario(horario).date() == hoje
        if aguardando and do_dia and consulta_ja_passou(dados, consulta):
            lista.append(consulta)
    return lista


def registrar_presenca(consulta: dict) -> None:
    """Consulta passa para REALIZADA."""
    consulta["ds_status"] = "REALIZADA"


def registrar_falta(dados: dict, consulta: dict) -> None:
    """Consulta passa para FALTA e o horário volta a ficar LIBERADO para encaixe."""
    consulta["ds_status"] = "FALTA"
    horario = buscar_horario(dados, consulta["id_horario"])
    horario["ds_status"] = "LIBERADO"


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
    """Vagas de HOJE que podem ser ofertadas para a lista do dia.

    - LIVRE: horário que ninguém agendou, só se ainda não passou.
    - LIBERADO: vaga devolvida por falta de confirmação ou porque o paciente
      faltou. Pode ser ofertada até TOLERANCIA_ENCAIXE_MIN minutos depois do
      horário, porque a falta só é registrada depois que o horário começa.
    """
    hoje = agora(dados).date()
    tolerancia_h = TOLERANCIA_ENCAIXE_MIN / 60
    vagas = []
    for horario in dados["horarios"]:
        if momento_do_horario(horario).date() != hoje:
            continue
        horas = horas_ate_consulta(dados, horario)
        if horario["ds_status"] == "LIVRE" and horas > 0:
            vagas.append(horario)
        elif horario["ds_status"] == "LIBERADO" and horas > -tolerancia_h:
            vagas.append(horario)
    return vagas

def encaixar(dados: dict, pessoa: dict, horario: dict) -> None:
    """Cidadão aceitou a vaga: fica ENCAIXADO e ganha uma consulta no horário.

    A consulta é criada com agendar_consulta (como é para hoje, já nasce
    CONFIRMADA), então o nome aparece na agenda e ela entra no comparecimento.
    Vaga LIBERADA (devolvida ou falta) vira REAPROVEITADO, que conta no indicador
    de reaproveitamento. Vaga LIVRE fica AGENDADO, porque só estava sobrando.
    """
    estava_liberado = horario["ds_status"] == "LIBERADO"
    consulta = agendar_consulta(dados, horario["id_horario"], pessoa["nm_cidadao"],
                                pessoa["nr_cns"], 0, False, True)
    consulta["fl_encaixe"] = True
    pessoa["ds_status"] = "ENCAIXADO"
    pessoa["fl_prioridade_amanha"] = False
    if estava_liberado:
        horario["ds_status"] = "REAPROVEITADO"


def fechar_dia(dados: dict) -> list:
    """Fecha o dia: quem não foi encaixado vira NAO_ENCAIXADO com prioridade.

    Devolve a lista de cópias dessas pessoas (já prontas para o dia seguinte).
    O chamador grava essa lista em lista_proximo_dia.json.
    """
    para_amanha = []
    for pessoa in dados["lista_dia"]:
        if pessoa["ds_status"] == "AGUARDANDO":
            pessoa["ds_status"] = "NAO_ENCAIXADO"
            pessoa["fl_prioridade_amanha"] = True
            copia = dict(pessoa)
            copia["ds_status"] = "AGUARDANDO"
            copia["hr_chegada"] = "dia ant."   # a hora de chegada era do dia anterior
            para_amanha.append(copia)
    dados["config"]["dia_fechado"] = True
    return para_amanha


def iniciar_novo_dia(dados: dict, pessoas_proximo_dia: list) -> int:
    """Prepara a lista do dia ao abrir o sistema.

    - Se o dia anterior foi fechado, a lista começa vazia.
    - Pessoas vindas de lista_proximo_dia.json entram na lista
      (sem duplicar o cartão SUS).
    Devolve quantas pessoas entraram com prioridade.
    """
    if dados["config"].get("dia_fechado", False):
        dados["lista_dia"] = []
        dados["config"]["dia_fechado"] = False
    cartoes = cartoes_cadastrados(dados["lista_dia"])
    entraram = 0
    for pessoa in pessoas_proximo_dia:
        if pessoa["nr_cns"] not in cartoes:
            dados["lista_dia"].append(pessoa)
            cartoes.add(pessoa["nr_cns"])
            entraram += 1
    return entraram
