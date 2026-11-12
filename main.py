"""Recepção UBS - menu principal. Requer Python 3.10+ (match-case)."""
import dados as bd
import interface as ifc
import menus
import regras
import validacoes as val


def main() -> None:
    """Carrega os dados, prepara o dia e repete o menu principal até o usuário sair."""
    dados = bd.carregar_json()
    entraram = regras.iniciar_novo_dia(dados)
    bd.salvar_json(dados)
    if entraram > 0:
        print(f"{entraram} pessoa(s) do dia anterior entraram na lista com prioridade.")
        ifc.pausar()
    while True:
        ifc.limpar_tela()
        ifc.titulo(f"RECEPÇÃO {dados['config']['ubs'].upper()}")
        momento = regras.agora(dados).strftime("%d/%m/%Y %H:%M")
        print(f"Data/hora do sistema: {momento}\n")
        print("1. Agenda do dia")
        print("2. Confirmações")
        print("3. Comparecimento")
        print("4. Lista do dia")
        print("5. Relatórios")
        print("0. Sair")
        opcao = val.ler_opcao(("1", "2", "3", "4", "5", "0"))
        match opcao:
            case "1":
                menus.menu_agenda(dados)
            case "2":
                menus.menu_confirmacoes(dados)
            case "3":
                menus.menu_comparecimento(dados)
            case "4":
                menus.menu_lista(dados)
            case "5":
                menus.menu_relatorios(dados)
            case "0":
                print("Dados salvos. Até logo!")
                break


if __name__ == "__main__":
    main()
