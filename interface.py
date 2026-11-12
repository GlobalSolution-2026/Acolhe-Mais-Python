"""Interface com o usuário (terminal).

Reúne as funções que cuidam só da APARÊNCIA e do FLUXO da tela, sem nenhuma
regra de negócio e sem mexer nos dados:
- limpar_tela: apaga o terminal para cada menu começar "limpo".
- pausar: espera o ENTER para o usuário conseguir ler o resultado.
- titulo: imprime o título de cada tela entre linhas.
- mostrar_tabela: imprime listas como tabela, com cabeçalho e separador.

O menus.py usa essas funções para não repetir código de impressão.
"""
import os


def limpar_tela() -> None:
    """Limpa o terminal (cls no Windows, clear no Linux/Mac)."""
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def pausar() -> None:
    """Espera o usuário apertar ENTER para ele conseguir ler a tela."""
    input("\nPressione ENTER para continuar...")


def titulo(texto: str) -> None:
    """Imprime um título destacado entre linhas."""
    linha = "=" * 60
    print(linha)
    print(f"  {texto}")
    print(linha)


def mostrar_tabela(colunas: tuple, linhas: list) -> None:
    """Imprime uma tabela com cabeçalho e separador.

    colunas: tupla de pares (nome, largura). Ex.: (("ID", 4), ("Nome", 20))
    linhas: lista de tuplas, uma por linha, na mesma ordem das colunas.
    """
    cabecalho = ""
    for nome, largura in colunas:
        cabecalho += f"{nome:<{largura}} "
    print(cabecalho)
    print("-" * len(cabecalho))
    for linha in linhas:
        texto = ""
        posicao = 0
        for nome, largura in colunas:
            texto += f"{linha[posicao]!s:<{largura}} "
            posicao += 1
        print(texto)
    print()
