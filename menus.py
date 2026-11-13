"""Submenus da recepção (telas do terminal).

Cada opção do menu principal tem um submenu aqui:
- Agenda do dia: ver horários e agendar consulta em horário livre ou liberado.
- Confirmações: ver pendentes (risco ALTO primeiro), registrar confirmação,
  liberar consultas não confirmadas no prazo e ajustar o relógio simulado.
- Comparecimento: registrar presença ou falta das consultas que já passaram.
- Lista do dia: incluir cidadão (VERDE ou AZUL), ver a lista na ordem de
  prioridade e ofertar vaga liberada ao primeiro da lista.
- Relatórios: absenteísmo, reaproveitamento, não encaixados e encerrar o dia.

Este arquivo só cuida da conversa com o usuário: lê as opções (validacoes.py),
mostra as telas (interface.py), chama as regras (regras.py e relatorios.py)
e salva os dados (dados.py) depois de cada alteração.
Cada tela limpa o terminal e pausa no final para o usuário conseguir ler.
"""

import dados as bd
import interface as ifc
import regras
import relatorios
import validacoes as val

# Colunas das tabelas: (nome, largura)
COLUNAS_CONSULTA = (("ID", 3), ("Data", 10), ("Hora", 5), ("Paciente", 22),
                    ("Risco", 5), ("Faltam", 7), ("Contato", 7), ("Status", 10))
COLUNAS_HORARIO = (("ID", 3), ("Data", 10), ("Hora", 5), ("Situação", 14), ("Paciente", 22))
COLUNAS_VAGA = (("ID", 3), ("Data", 10), ("Hora", 5), ("Situação", 14))
COLUNAS_PESSOA = (("#", 3), ("Nome", 24), ("Cor", 6), ("Chegada", 8),
                  ("Status", 14), ("Prioridade", 10))


# ---------- montagem de linhas ----------
def data_e_hora(horario: dict) -> tuple:
    """Devolve (data 'DD/MM/AAAA', hora 'HH:MM') de um horário."""
    momento = regras.momento_do_horario(horario)
    return momento.strftime("%d/%m/%Y"), momento.strftime("%H:%M")


def linha_consulta(consulta: dict, dados: dict) -> tuple:
    """Monta a linha de tabela de uma consulta."""
    horario = regras.buscar_horario(dados, consulta["id_horario"])
    data, hora = data_e_hora(horario)
    horas = regras.horas_ate_consulta(dados, horario)
    if horas < 0:
        faltam = "passou"
    else:
        faltam = f"{horas:.0f}h"
    contato = "Sim" if consulta["tem_contato"] else "Não"
    return (consulta["id_consulta"], data, hora, consulta["nm_paciente"],
            consulta["ds_risco"], faltam, contato, consulta["ds_status"])


def mostrar_consultas(consultas: list, dados: dict) -> list:
    """Mostra a tabela de consultas e devolve os IDs (texto) para validar a escolha."""
    linhas = []
    ids = []
    for consulta in consultas:
        linhas.append(linha_consulta(consulta, dados))
        ids.append(str(consulta["id_consulta"]))
    ifc.mostrar_tabela(COLUNAS_CONSULTA, linhas)
    return ids


def mostrar_vagas(horarios: list) -> list:
    """Mostra a tabela de horários/vagas e devolve os IDs (texto)."""
    linhas = []
    ids = []
    for horario in horarios:
        data, hora = data_e_hora(horario)
        linhas.append((horario["id_horario"], data, hora, horario["ds_status"]))
        ids.append(str(horario["id_horario"]))
    ifc.mostrar_tabela(COLUNAS_VAGA, linhas)
    return ids


def escolher_id(ids: list, texto: str) -> int:
    """Pede um ID da lista. Devolve 0 se o usuário cancelar (digitar 0)."""
    print(f"{texto} (0 para cancelar)")
    ids_validos = ids + ["0"]
    return int(val.ler_opcao(tuple(ids_validos)))


# ---------- 1. Agenda do dia ----------
def menu_agenda(dados: dict) -> None:
    """Submenu da agenda: ver horários e agendar consulta."""
    while True:
        ifc.limpar_tela()
        ifc.titulo("AGENDA DO DIA")
        print("1. Ver horários")
        print("2. Agendar consulta (horário livre ou liberado)")
        print("0. Voltar")
        opcao = val.ler_opcao(("1", "2", "0"))
        match opcao:
            case "1":
                ver_horarios(dados)
            case "2":
                agendar(dados)
            case "0":
                break
        ifc.pausar()


def ver_horarios(dados: dict) -> None:
    """Lista todos os horários (livres, agendados, liberados...) com o paciente."""
    ifc.limpar_tela()
    ifc.titulo("HORÁRIOS")
    linhas = []
    hoje = regras.agora(dados).date()
    for horario in dados["horarios"]:
        if regras.momento_do_horario(horario).date() != hoje:
            continue
        data, hora = data_e_hora(horario)
        consulta = regras.consulta_ativa_do_horario(dados, horario["id_horario"])
        paciente = ""
        if consulta is not None:
            paciente = consulta["nm_paciente"]
        linhas.append((horario["id_horario"], data, hora, horario["ds_status"], paciente))
    if len(linhas) == 0:
        print("Não há horários na agenda de hoje.")
        return
    ifc.mostrar_tabela(COLUNAS_HORARIO, linhas)


def agendar(dados: dict) -> None:
    """Agenda um paciente num horário LIVRE ou LIBERADO, calculando o risco de falta."""
    ifc.limpar_tela()
    ifc.titulo("AGENDAR CONSULTA")
    disponiveis = regras.horarios_disponiveis(dados)
    if len(disponiveis) == 0:
        print("Não há horários livres ou liberados.")
        return
    print("Horários disponíveis (LIBERADO = vaga devolvida por falta de confirmação):\n")
    ids = mostrar_vagas(disponiveis)
    id_escolhido = escolher_id(ids, "Escolha o ID do horário")
    if id_escolhido == 0:
        print("Operação cancelada.")
        return
    horario = regras.buscar_horario(dados, id_escolhido)
    nome = val.ler_texto("Nome do paciente")
    cns = val.ler_cns()
    if regras.cartao_de_outra_pessoa(dados, cns, nome):
        print(f"\nEste cartão SUS já está cadastrado para "
              f"{regras.nome_do_cartao(dados, cns)}. Confira os dados.")
        return
    dia = regras.momento_do_horario(horario).date()
    existente = regras.consulta_ativa_no_dia(dados, cns, dia)
    if existente is not None:
        data, hora = data_e_hora(regras.buscar_horario(dados, existente["id_horario"]))
        print(f"\nEste paciente já tem consulta marcada em {data} às {hora} "
              f"({existente['nm_paciente']}). Não é permitido duplicar no mesmo dia.")
        return
    print("\nRisco de FALTA (calculado pelo sistema):")
    print("  1 ponto por falta anterior + 1 ponto se for a primeira consulta na UBS.")
    print("  2 pontos ou mais = risco ALTO; menos que isso = risco BAIXO.")
    faltas = val.ler_inteiro("Faltas anteriores do paciente", 0, 20)
    primeira_vez = val.ler_sn("É a primeira consulta do paciente nesta UBS?")
    contato = val.ler_sn("Paciente tem contato (telefone/WhatsApp)?")
    consulta = regras.agendar_consulta(dados, id_escolhido, nome, cns,
                                       faltas, primeira_vez, contato)
    bd.salvar_json(dados)
    print(f"\nConsulta agendada. Risco de falta: {consulta['ds_risco']}.")
    if consulta["fl_confirmacao_dispensada"]:
        print("Marcada com menos de 24h de antecedência: confirmação dispensada.")
    else:
        print("Aguardando confirmação.")


# ---------- 2. Confirmações ----------
def menu_confirmacoes(dados: dict) -> None:
    """Submenu de confirmações: pendentes, confirmar, liberar e ajustar o relógio."""
    while True:
        ifc.limpar_tela()
        ifc.titulo("CONFIRMAÇÕES")
        print("1. Ver consultas pendentes de confirmação")
        print("2. Registrar confirmação")
        print("3. Liberar consultas não confirmadas no prazo")
        print("4. Ajustar data/hora do sistema (simulação)")
        print("0. Voltar")
        opcao = val.ler_opcao(("1", "2", "3", "4", "0"))
        match opcao:
            case "1":
                ver_pendentes(dados)
            case "2":
                registrar_confirmacao(dados)
            case "3":
                liberar_nao_confirmadas(dados)
            case "4":
                ajustar_relogio(dados)
            case "0":
                break
        ifc.pausar()


def ver_pendentes(dados: dict) -> None:
    """Lista as consultas pendentes de confirmação (risco alto primeiro)."""
    pendentes = regras.consultas_pendentes(dados)
    if len(pendentes) == 0:
        print("Nenhuma consulta pendente de confirmação.")
        return
    print("Pendentes de confirmação (risco alto primeiro):\n")
    mostrar_consultas(pendentes, dados)
    print("Prazo: risco ALTO confirma até 72h antes; risco BAIXO, até 48h antes.")


def registrar_confirmacao(dados: dict) -> None:
    """Escolhe uma consulta pendente e marca como confirmada."""
    pendentes = regras.consultas_pendentes(dados)
    if len(pendentes) == 0:
        print("Nenhuma consulta pendente de confirmação.")
        return
    ids = mostrar_consultas(pendentes, dados)
    id_consulta = escolher_id(ids, "ID da consulta confirmada")
    if id_consulta == 0:
        print("Operação cancelada.")
        return
    if regras.confirmar_consulta(dados, id_consulta):
        bd.salvar_json(dados)
        print("Confirmação registrada.")
    else:
        print("Não foi possível confirmar: o horário já passou ou a consulta não está pendente.")


def liberar_nao_confirmadas(dados: dict) -> None:
    """Libera os horários cujo prazo de confirmação venceu (pede confirmação antes)."""
    liberaveis, protegidas = regras.consultas_para_liberar(dados)
    if len(protegidas) > 0:
        print("Sem contato com o paciente: a vaga NÃO será liberada.\n")
        mostrar_consultas(protegidas, dados)
    if len(liberaveis) == 0:
        print("Nenhuma consulta para liberar.")
        return
    print("Não confirmadas dentro do prazo:\n")
    mostrar_consultas(liberaveis, dados)
    if not val.ler_sn(f"Liberar {len(liberaveis)} consulta(s)?"):
        print("Operação cancelada.")
        return
    for consulta in liberaveis:
        regras.liberar_consulta(dados, consulta)
    bd.salvar_json(dados)
    print(f"{len(liberaveis)} horário(s) liberado(s).")


def ajustar_relogio(dados: dict) -> None:
    """Permite simular a data/hora atual (para demonstrar os prazos de confirmação)."""
    atual = regras.agora(dados).strftime("%d/%m/%Y %H:%M")
    print(f"Data/hora do sistema agora: {atual}")
    texto = val.ler_data_hora("Nova data/hora")
    regras.definir_relogio(dados, texto)
    regras.gerar_agenda(dados)
    bd.salvar_json(dados)
    novo = regras.agora(dados).strftime("%d/%m/%Y %H:%M")
    print(f"Data/hora do sistema: {novo}")


# ---------- 3. Comparecimento ----------
def menu_comparecimento(dados: dict) -> None:
    """Submenu de comparecimento: registrar presença ou falta."""
    while True:
        ifc.limpar_tela()
        ifc.titulo("COMPARECIMENTO")
        print("1. Registrar presença")
        print("2. Registrar falta")
        print("0. Voltar")
        opcao = val.ler_opcao(("1", "2", "0"))
        match opcao:
            case "1" | "2":
                registrar_comparecimento(dados, opcao)
            case "0":
                break
        ifc.pausar()


def registrar_comparecimento(dados: dict, opcao: str) -> None:
    """Registra presença (opcao '1') ou falta (opcao '2') da consulta escolhida."""
    candidatas = regras.consultas_do_comparecimento(dados)
    if len(candidatas) == 0:
        print("Nenhuma consulta aguardando comparecimento.")
        return
    ids = mostrar_consultas(candidatas, dados)
    id_consulta = escolher_id(ids, "ID da consulta")
    if id_consulta == 0:
        print("Operação cancelada.")
        return
    consulta = regras.buscar_consulta(dados, id_consulta)
    if opcao == "1":
        regras.registrar_presenca(consulta)
        print("Presença registrada.")
    else:
        if not val.ler_sn(f"Confirmar FALTA de {consulta['nm_paciente']}?"):
            print("Operação cancelada.")
            return
        regras.registrar_falta(dados, consulta)
        print("Falta registrada.")
    bd.salvar_json(dados)


# ---------- 4. Lista do dia ----------
def menu_lista(dados: dict) -> None:
    """Submenu da lista do dia: incluir, ver e ofertar vaga."""
    while True:
        ifc.limpar_tela()
        ifc.titulo("LISTA DO DIA")
        print("1. Incluir cidadão (VERDE ou AZUL)")
        print("2. Ver lista na ordem de prioridade")
        print("3. Ofertar vaga liberada ao primeiro da lista")
        print("0. Voltar")
        opcao = val.ler_opcao(("1", "2", "3", "0"))
        match opcao:
            case "1":
                incluir_cidadao(dados)
            case "2":
                ver_lista(dados)
            case "3":
                ofertar_vaga(dados)
            case "0":
                break
        ifc.pausar()


def incluir_cidadao(dados: dict) -> None:
    """Inclui um cidadão na lista do dia, barrando cartão SUS repetido (set)."""
    nome = val.ler_texto("Nome do cidadão")
    cns = val.ler_cns()
    if regras.cartao_de_outra_pessoa(dados, cns, nome):
        print(f"Este cartão SUS já está cadastrado para "
              f"{regras.nome_do_cartao(dados, cns)}. Confira os dados.")
        return
    if cns in regras.cartoes_cadastrados(dados["lista_dia"]):
        print("Este cartão SUS já está na lista do dia.")
        return
    hoje = regras.agora(dados).date()
    existente = regras.consulta_ativa_no_dia(dados, cns, hoje)
    if existente is not None:
        data, hora = data_e_hora(regras.buscar_horario(dados, existente["id_horario"]))
        print(f"Quem tem consulta marcada hoje não entra na fila do dia "
              f"({existente['nm_paciente']}: {data} às {hora}).")
        return
    cor = ""
    while cor not in bd.CORES:
        cor = input(f"Cor ({'/'.join(bd.CORES)}): ").strip().upper()
        if cor not in bd.CORES:
            print("Cor inválida. Use VERDE ou AZUL.")
    regras.incluir_na_lista(dados, nome, cns, cor)
    bd.salvar_json(dados)
    print("Cidadão incluído na lista.")


def ver_lista(dados: dict) -> None:
    """Mostra a lista do dia na ordem de prioridade."""
    ifc.limpar_tela()
    ifc.titulo("LISTA DO DIA - ORDEM DE PRIORIDADE")
    if len(dados["lista_dia"]) == 0:
        print("A lista do dia está vazia.")
        return
    linhas = []
    posicao = 1
    for pessoa in regras.ordenar_lista(dados["lista_dia"]):
        prioridade = "Sim" if pessoa["fl_prioridade_amanha"] else ""
        linhas.append((posicao, pessoa["nm_cidadao"], pessoa["ds_cor"],
                       pessoa["hr_chegada"], pessoa["ds_status"], prioridade))
        posicao += 1
    ifc.mostrar_tabela(COLUNAS_PESSOA, linhas)
    print("Prioridade = veio da lista de não encaixados do dia anterior.")


def ofertar_vaga(dados: dict) -> None:
    """Oferece uma vaga liberada ao primeiro da lista; recusou/sem resposta = próximo.

    O prazo de 30 min é simulado: a recepção informa a resposta, sem relógio real.
    """
    liberados = regras.horarios_liberados(dados)
    if len(liberados) == 0:
        print("Não há vagas liberadas para ofertar.")
        return
    print("Vagas liberadas:\n")
    ids = mostrar_vagas(liberados)
    id_horario = escolher_id(ids, "ID da vaga a ofertar")
    if id_horario == 0:
        print("Operação cancelada.")
        return
    horario = regras.buscar_horario(dados, id_horario)
    data, hora = data_e_hora(horario)
    ignorados = set()
    prazo = dados["config"]["prazo_oferta_min"]
    while True:
        pessoa = regras.proximo_da_lista(dados["lista_dia"], ignorados)
        if pessoa is None:
            print("\nNinguém mais na lista. A vaga segue liberada.")
            break
        print(f"\nOfertar {data} às {hora} a {pessoa['nm_cidadao']} "
              f"({pessoa['ds_cor']}). Prazo: {prazo} min (simulado).")
        print("1. Aceitou   2. Recusou   3. Não respondeu")
        resposta = val.ler_opcao(("1", "2", "3"))
        if resposta == "1":
            regras.encaixar(dados, pessoa, horario)
            bd.salvar_json(dados)
            print(f"{pessoa['nm_cidadao']} encaixado(a) em {data} às {hora}.")
            break
        elif resposta == "2":
            print("Recusou. Passando ao próximo.")
        else:
            print("Sem resposta no prazo. Passando ao próximo.")
        ignorados.add(pessoa["nr_cns"])


def encerrar_dia(dados: dict) -> None:
    """Encerra a agenda do dia: fecha a lista e gera o relatório do dia em JSON.

    Quem não foi encaixado fica com prioridade para o dia seguinte (lista_proximo_dia.json)
    e o relatório completo vai para relatorio_AAAA-MM-DD.json.
    """
    if dados["config"].get("dia_fechado", False):
        print("A agenda do dia já foi encerrada.")
        return
    print("Ao encerrar: quem não foi encaixado terá prioridade amanhã e será gerado")
    print("o relatório do dia em JSON.\n")
    if not val.ler_sn("Encerrar a agenda do dia?"):
        print("Operação cancelada.")
        return
    para_amanha = regras.fechar_dia(dados)
    bd.salvar_proximo_dia(para_amanha)
    momento = regras.agora(dados)
    relatorio = relatorios.montar_relatorio_dia(
        dados, momento.strftime("%Y-%m-%d"), momento.strftime("%Y-%m-%d %H:%M"))
    arquivo = bd.salvar_relatorio_dia(relatorio)
    bd.salvar_json(dados)
    print(f"\nAgenda encerrada. {len(para_amanha)} pessoa(s) com prioridade para amanhã.")
    print(f"Relatório gerado em {arquivo}.")


# ---------- 5. Relatórios ----------
def menu_relatorios(dados: dict) -> None:
    """Submenu de relatórios: os 3 indicadores e o encerramento da agenda do dia."""
    while True:
        ifc.limpar_tela()
        ifc.titulo("RELATÓRIOS")
        print("1. Taxa de absenteísmo")
        print("2. Taxa de reaproveitamento de horários")
        print("3. Pessoas não encaixadas no dia")
        print("4. Encerrar a agenda do dia (gera relatório em JSON)")
        print("0. Voltar")
        opcao = val.ler_opcao(("1", "2", "3", "4", "0"))
        match opcao:
            case "1":
                mostrar_absenteismo(dados)
            case "2":
                mostrar_reaproveitamento(dados)
            case "3":
                mostrar_nao_encaixados(dados)
            case "4":
                encerrar_dia(dados)
            case "0":
                break
        ifc.pausar()


def mostrar_absenteismo(dados: dict) -> None:
    """Mostra a taxa de absenteísmo com os números usados no cálculo."""
    faltas = relatorios.contar_status(dados["consultas"], "FALTA")
    realizadas = relatorios.contar_status(dados["consultas"], "REALIZADA")
    taxa = relatorios.calcular_absenteismo(dados["consultas"])
    ifc.mostrar_tabela((("Indicador", 28), ("Valor", 10)), [
        ("Consultas realizadas", realizadas),
        ("Faltas", faltas),
        ("Taxa de absenteísmo", f"{taxa:.1f}%"),
    ])


def mostrar_reaproveitamento(dados: dict) -> None:
    """Mostra a taxa de reaproveitamento com os números usados no cálculo."""
    reaproveitados = 0
    liberados = 0
    for horario in dados["horarios"]:
        if horario["ds_status"] == "REAPROVEITADO":
            reaproveitados += 1
            liberados += 1
        elif horario["ds_status"] == "LIBERADO":
            liberados += 1
    taxa = relatorios.calcular_reaproveitamento(dados["horarios"])
    ifc.mostrar_tabela((("Indicador", 28), ("Valor", 10)), [
        ("Horários liberados (total)", liberados),
        ("Horários reaproveitados", reaproveitados),
        ("Taxa de reaproveitamento", f"{taxa:.1f}%"),
    ])


def mostrar_nao_encaixados(dados: dict) -> None:
    """Lista quem não conseguiu vaga no dia.

    Com o dia encerrado, mostra os NAO_ENCAIXADO. Com o dia ainda aberto,
    mostra quem continua AGUARDANDO (se o dia fosse encerrado agora,
    essas pessoas ficariam sem vaga).
    """
    if dados["config"].get("dia_fechado", False):
        pessoas = relatorios.listar_nao_encaixados(dados["lista_dia"])
    else:
        pessoas = relatorios.listar_aguardando(dados["lista_dia"])
        print("O dia ainda não foi encerrado. Quem continua aguardando vaga:\n")
    if len(pessoas) == 0:
        print("Nenhuma pessoa sem vaga.")
        return
    linhas = []
    posicao = 1
    for pessoa in pessoas:
        prioridade = "Sim" if pessoa["fl_prioridade_amanha"] else ""
        linhas.append((posicao, pessoa["nm_cidadao"], pessoa["ds_cor"],
                       pessoa["hr_chegada"], pessoa["ds_status"], prioridade))
        posicao += 1
    ifc.mostrar_tabela(COLUNAS_PESSOA, linhas)